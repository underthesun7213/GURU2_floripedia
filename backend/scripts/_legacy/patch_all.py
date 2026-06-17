"""
Floripedia 후처리 통합 스크립트
================================
etl_add_plants.py가 생성한 v2_data.json을 읽어
모든 후처리를 한 번에 적용 → v2_data_patched.json 출력.

실행 순서:
  Phase 1: flowerGroup + scentInfo — Gemini 배치 패치
  Phase 2: 잔존 '기타' 강제분류 + '향 없음'→'무향' 치환
  Phase 3: colorLabels 16종 정규화 + colorGroup 재매핑
  Phase 4: hex↔label 1:1 맞춤, 빈 scentTags→["무향"], habitat 누락 채움

Usage:
  python patch_all.py                  # 전체 실행
  python patch_all.py --skip-gemini    # Phase 1 스킵 (이미 패치된 파일에 2~4만 재적용)
"""

import json
import os
import sys
import time
import logging
import argparse
from collections import Counter

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ============================================================
# CONFIG
# ============================================================

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
INPUT_PATH = os.path.join(DATA_DIR, "v2_data.json")
OUTPUT_PATH = os.path.join(DATA_DIR, "v2_data_patched.json")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.5-flash-lite")
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# ============================================================
# SPEC CONSTANTS
# ============================================================

FLOWER_GROUPS = {"사랑/고백", "위로/슬픔", "감사/존경", "이별/그리움", "행복/즐거움"}
SCENT_GROUPS = {"달콤·화사", "싱그럽고 시원", "은은·차분", "무향"}
COLOR_GROUPS = {"백색/미색", "노랑/주황", "빨강/분홍", "푸른색", "갈색/검정"}
VALID_COLOR_LABELS = {"백색", "연두", "초록", "노랑", "빨강", "분홍", "연보라", "보라", "파랑", "하늘", "살구", "갈색", "검정", "다홍", "주황", "미색"}

# ============================================================
# PHASE 1: Gemini 배치 패치 (flowerGroup + scentInfo)
# ============================================================

BATCH_SIZE = 30
RATE_LIMIT = 2.0

_FG_KEYWORD_MAP = {
    "사랑/고백": ["사랑", "고백", "아름다움", "우아", "신비", "매력", "순수", "고귀한 아름다움"],
    "감사/존경": ["감사", "존경", "겸손", "고귀", "품위", "숭고", "인내", "강인", "성실", "끈기"],
    "행복/즐거움": ["행복", "기쁨", "즐거움", "번영", "희망", "축복", "새로운 시작", "기쁜"],
    "위로/슬픔": ["위로", "치유", "고독", "평화", "안식", "보호", "용기"],
    "이별/그리움": ["이별", "그리움", "기다림", "추억", "복수", "질투", "미움"],
}


def _call_gemini(prompt: str, max_retries: int = 3) -> str:
    import requests
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 8000,
            "responseMimeType": "application/json",
        },
    }
    for attempt in range(1, max_retries + 1):
        time.sleep(RATE_LIMIT)
        try:
            resp = requests.post(
                f"{GEMINI_API_BASE}/models/{GEMINI_MODEL}:generateContent",
                params={"key": GEMINI_API_KEY},
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logging.warning(f"  Gemini attempt {attempt}/{max_retries}: {e}")
            if attempt < max_retries:
                time.sleep(RATE_LIMIT * attempt * 2)
    raise RuntimeError(f"Gemini API {max_retries}회 재시도 실패")


def _match_flower_group_gemini(value: str) -> str:
    """Gemini 반환값을 규격 그룹으로 매칭"""
    if not value:
        return "행복/즐거움"
    value = value.strip()
    if value in FLOWER_GROUPS:
        return value
    for group, keywords in _FG_KEYWORD_MAP.items():
        for kw in keywords:
            if kw in value or value in kw:
                return group
    return "행복/즐거움"


def _gemini_patch_batch(batch: list[dict]) -> dict:
    items_text = "\n".join(
        f'{i+1}. id={it["id"]} | {it["name"]} ({it["scientificName"]}) | 꽃말={it["language"]}'
        for i, it in enumerate(batch)
    )
    prompt = f"""당신은 조말론 수석 조향사이자 식물학 전문가입니다.

■ flowerGroup — 반드시 아래 5개 중 정확히 하나만 선택. "기타" 절대 금지:
  - 사랑/고백
  - 감사/존경
  - 행복/즐거움
  - 위로/슬픔
  - 이별/그리움
  분류 기준:
  - 사랑/고백: 사랑, 아름다움, 우아함, 신비, 매력, 순수한 사랑, 고귀한 아름다움 등 연인에게 선물할 수 있는 감성
  - 감사/존경: 감사, 존경, 겸손, 고귀함, 품위, 숭고, 인내, 강인함, 성실 등 인격적으로 좋은 의미
  - 행복/즐거움: 행복, 기쁨, 즐거움, 번영, 희망, 축복, 새로운 시작 등 밝고 긍정적인 감성
  - 위로/슬픔: 위로, 치유, 고독, 평화, 안식, 보호 등 따뜻하게 감싸는 감성
  - 이별/그리움: 이별, 그리움, 기다림, 추억, 복수, 질투 등 아련한 감성

■ scentTags — 조향사 관점에서 이 식물의 실제 향 프로파일링:
  - 꽃, 잎, 줄기, 수액, 뿌리 등 식물 전체에서 나는 향을 구별
  - 핵심 향만 한글 태그로 작성 (예: ["달콤한 꿀향", "시트러스", "우디"])
  - 빈 배열 []은 금지. 반드시 1개 이상의 향 태그를 작성
  - 코를 가까이 대야 겨우 느낄 수 있는 미세한 향도 반드시 서술 (예: "연한 풀향", "흙내음")
  - 오직 코로 전혀 감지할 수 없는 식물만 ["무향"] 태그 1개 작성

■ scentGroup — 반드시 아래 4개 중에서만 선택 (배열, 복수 가능):
  - 달콤·화사
  - 싱그럽고 시원
  - 은은·차분
  - 무향
  이 4개 외의 값은 절대 금지. "향 없음" 금지. 무향은 코로 전혀 감지 불가능한 식물만.

식물 목록:
{items_text}

JSON 객체만 응답:
{{"id값": {{"flowerGroup": "...", "scentTags": ["...", "..."], "scentGroup": ["..."]}}, ...}}"""

    batch_lang_map = {it["id"]: it["language"] for it in batch}
    result = _call_gemini(prompt)
    try:
        parsed = json.loads(result)
        if not isinstance(parsed, dict):
            logging.error(f"  응답이 dict가 아님: {type(parsed)}")
            return {}
        validated = {}
        for pid, info in parsed.items():
            if not isinstance(info, dict):
                continue
            fg = info.get("flowerGroup", "")
            if fg not in FLOWER_GROUPS:
                fg = _match_flower_group_gemini(fg)
            if fg not in FLOWER_GROUPS:
                fg = _match_flower_group_gemini(batch_lang_map.get(pid, ""))
            st = info.get("scentTags", [])
            if not isinstance(st, list):
                st = []
            st = ["무향" if t == "향 없음" else t for t in st]
            sg = info.get("scentGroup", [])
            if not isinstance(sg, list):
                sg = []
            sg = ["무향" if g == "향 없음" else g for g in sg]
            sg = [g for g in sg if g in SCENT_GROUPS]
            if not sg:
                sg = ["은은·차분"] if st else ["무향"]
            validated[pid] = {
                "flowerGroup": fg,
                "scentTags": st,
                "scentGroup": sg,
            }
        return validated
    except json.JSONDecodeError:
        logging.error(f"  JSON 파싱 실패: {result[:200]}")
        return {}


def phase1_gemini_patch(plants: list) -> dict:
    """Phase 1: Gemini 배치로 flowerGroup + scentInfo 패치"""
    logging.info("=" * 50)
    logging.info("[Phase 1] Gemini 배치 패치 (flowerGroup + scentInfo)")

    if not GEMINI_API_KEY:
        logging.error("GEMINI_API_KEY 환경변수 없음 — Phase 1 스킵")
        return {"fg": 0, "scent": 0}

    # habitat "원산지: " 접두사 제거
    for p in plants:
        h = p.get("habitat", "")
        if h.startswith("원산지: "):
            p["habitat"] = h[len("원산지: "):]
        elif h.startswith("원산지:"):
            p["habitat"] = h[len("원산지:"):]

    # 배치 구성
    batches = []
    for i in range(0, len(plants), BATCH_SIZE):
        batch = []
        for p in plants[i:i + BATCH_SIZE]:
            batch.append({
                "id": p.get("_id", ""),
                "name": p.get("name", ""),
                "scientificName": p.get("scientificName", ""),
                "language": p.get("flowerInfo", {}).get("language", ""),
            })
        batches.append(batch)
    logging.info(f"  {len(batches)}개 배치 ({BATCH_SIZE}건씩)")

    # Gemini 호출
    id_to_patch = {}
    for i, batch in enumerate(batches, 1):
        logging.info(f"  배치 [{i}/{len(batches)}] ({len(batch)}건)")
        result = _gemini_patch_batch(batch)
        id_to_patch.update(result)
        logging.info(f"    → {len(result)}건 완료")

    # 적용
    patched_fg = 0
    patched_scent = 0
    for p in plants:
        pid = p.get("_id", "")
        if pid not in id_to_patch:
            continue
        patch = id_to_patch[pid]
        p["flowerInfo"]["flowerGroup"] = patch["flowerGroup"]
        patched_fg += 1
        new_tags = [t for t in patch["scentTags"] if t not in ("향 없음", "무향")]
        new_group = patch["scentGroup"]
        old_tags = p.get("scentInfo", {}).get("scentTags", [])
        old_group = p.get("scentInfo", {}).get("scentGroup", [])
        if old_tags != new_tags or old_group != new_group:
            p["scentInfo"]["scentTags"] = new_tags
            p["scentInfo"]["scentGroup"] = new_group
            patched_scent += 1

    logging.info(f"  flowerGroup 변경: {patched_fg}건, scentInfo 변경: {patched_scent}건")
    return {"fg": patched_fg, "scent": patched_scent}


# ============================================================
# PHASE 2: 잔존 기타/향 없음 강제 치환
# ============================================================

FG_KEYWORDS = [
    ("이별/그리움", ["이별", "그리움", "기다림", "추억", "복수", "질투", "미움"]),
    ("위로/슬픔", ["위로", "치유", "고독", "평화", "안식", "보호", "용기", "위험", "독"]),
    ("사랑/고백", ["사랑", "고백", "아름다움", "우아", "신비", "매력", "순수", "청초", "섬세", "애교"]),
    ("감사/존경", ["감사", "존경", "겸손", "고귀", "품위", "숭고", "인내", "강인", "성실", "끈기", "경계", "기사"]),
    ("행복/즐거움", ["행복", "기쁨", "즐거움", "번영", "희망", "축복", "새로운 시작", "기쁜", "봄", "부귀", "자유", "단결"]),
]


def _match_flower_group_keyword(language: str) -> str:
    if not language:
        return "행복/즐거움"
    for group, keywords in FG_KEYWORDS:
        for kw in keywords:
            if kw in language:
                return group
    return "행복/즐거움"


def phase2_fix_remaining(plants: list) -> dict:
    """Phase 2: flowerGroup 키워드 재분류 + '향 없음'→'무향' 치환"""
    logging.info("=" * 50)
    logging.info("[Phase 2] flowerGroup 키워드 재분류 + 향 없음→무향")

    fg_changed = 0
    sg_changed = 0

    for p in plants:
        old_fg = p.get("flowerInfo", {}).get("flowerGroup", "")
        lang = p.get("flowerInfo", {}).get("language", "")
        # 꽃말 키워드 매칭 우선
        new_fg = _match_flower_group_keyword(lang)
        # 키워드 기본값(행복/즐거움)이면 기존 Gemini 값 유지 (단, 기타/비규격 제외)
        if new_fg == "행복/즐거움" and old_fg in FLOWER_GROUPS and old_fg != "기타" and old_fg != "행복/즐거움":
            new_fg = old_fg
        if new_fg != old_fg:
            p["flowerInfo"]["flowerGroup"] = new_fg
            fg_changed += 1

        sg = p.get("scentInfo", {}).get("scentGroup", [])
        new_sg = ["무향" if g == "향 없음" else g for g in sg]
        if new_sg != sg:
            p["scentInfo"]["scentGroup"] = new_sg
            sg_changed += 1

        st = p.get("scentInfo", {}).get("scentTags", [])
        new_st = ["무향" if t == "향 없음" else t for t in st]
        if new_st != st:
            p["scentInfo"]["scentTags"] = new_st

    logging.info(f"  기타→강제분류: {fg_changed}건, 향 없음→무향: {sg_changed}건")
    return {"fg": fg_changed, "sg": sg_changed}


# ============================================================
# PHASE 3: colorLabels 16종 정규화
# ============================================================

LABEL_MAP = {
    # 백색 계열
    "흰색": "백색", "하얀색": "백색", "하양": "백색", "순백색": "백색",
    "연한 흰색": "백색", "옅은 흰색": "백색", "아주 연한 흰색": "백색",
    "아주 연한 회색빛 흰색": "백색", "연백색": "백색",
    # 미색 계열
    "크림색": "미색", "아이보리": "미색", "아이보리색": "미색", "베이지색": "미색",
    "연미색": "미색", "크림 베이지": "미색", "아주 연한 미색": "미색",
    "연한 녹색빛 미색": "미색", "연한 미색": "미색",
    # 노랑 계열
    "노란색": "노랑", "연노랑": "노랑", "연노랑색": "노랑", "밝은 노랑": "노랑",
    "밝은 노란색": "노랑", "선명한 노랑": "노랑", "황금색": "노랑", "금색": "노랑",
    "골드": "노랑", "황금빛 노랑": "노랑", "옅은 노란색": "노랑", "옅은 노랑": "노랑",
    "짙은 노랑": "노랑", "진한 노란색": "노랑", "레몬색": "노랑",
    "연두빛 노랑": "노랑", "황금주황색": "주황",
    # 주황 계열
    "주황색": "주황", "진한 주황": "주황", "밝은 주황": "주황", "붉은 주황": "주황",
    "호박색": "주황", "황갈색": "주황",
    # 빨강 계열
    "붉은색": "빨강", "진홍색": "빨강", "선홍색": "빨강", "선명한 붉은색": "빨강",
    "짙은 붉은색": "빨강", "심홍색": "빨강", "벽돌색": "빨강",
    # 다홍 계열
    "적갈색": "다홍", "붉은 갈색": "다홍", "붉은갈색": "다홍", "짙은 적갈색": "다홍",
    "자주빛 갈색": "다홍", "자주갈색": "다홍",
    # 분홍 계열
    "분홍색": "분홍", "연분홍": "분홍", "연분홍색": "분홍", "진분홍": "분홍",
    "진분홍색": "분홍", "장밋빛 분홍": "분홍", "핫핑크": "분홍", "자홍색": "분홍",
    "자주분홍": "분홍",
    # 살구
    "살구색": "살구",
    # 연보라 계열
    "연보라색": "연보라", "연자주색": "연보라", "연자색": "연보라",
    "연한 보라": "연보라",
    # 보라 계열
    "보라색": "보라", "자주색": "보라", "진보라색": "보라", "진한 보라": "보라",
    "진한 보라색": "보라", "짙은 보라": "보라", "짙은 보라색": "보라",
    "짙은 자주색": "보라", "짙은 남보라": "보라", "짙은 남보라색": "보라",
    "보라남색": "보라", "블루 바이올렛": "보라", "블루바이올렛": "보라",
    "보랏빛 파랑": "보라",
    # 파랑 계열
    "파란색": "파랑", "짙은 파랑": "파랑", "진한 파랑": "파랑",
    "선명한 파랑": "파랑", "로얄블루": "파랑", "로얄 블루": "파랑", "로열 블루": "파랑",
    "콘플라워 블루": "파랑", "콘플라워블루": "파랑", "강청색": "파랑",
    "푸른색": "파랑",
    # 하늘 계열
    "하늘색": "하늘", "연하늘색": "하늘", "연한 하늘색": "하늘",
    "스카이블루": "하늘", "스카이 블루": "하늘", "스틸 블루": "하늘",
    "스틸블루": "하늘",
    # 남색/청보라 → 파랑/보라
    "남색": "파랑", "남보라색": "파랑", "남보라": "파랑",
    "청보라색": "보라", "청보라": "보라", "청자색": "보라",
    "슬레이트 블루": "보라", "슬레이트블루": "보라",
    # 초록 계열
    "초록색": "초록", "녹색": "초록", "짙은 녹색": "초록", "진한 녹색": "초록",
    "짙은 초록": "초록", "연녹색": "연두", "연두색": "연두", "옅은 연두색": "연두",
    "연한 황록색": "연두", "황록색": "연두", "연두빛 갈색": "갈색",
    # 올리브 계열
    "올리브 그린": "초록", "올리브색": "초록", "올리브 녹색": "초록",
    "짙은 올리브색": "초록", "올리브 갈색": "갈색",
    # 갈색 계열
    "연갈색": "갈색", "옅은 갈색": "갈색", "짙은 갈색": "갈색", "어두운 갈색": "갈색",
    "밤색": "갈색", "흙갈색": "갈색", "회갈색": "갈색",
    # 회색/은색
    "회색": "미색", "연회색": "미색", "옅은 회색": "미색",
    "은회색": "미색", "은녹색": "연두", "회녹색": "초록", "연회녹색": "연두",
    "짙은 회녹색": "초록", "청회색": "하늘", "푸른회색": "하늘",
    # 청동/녹갈 계열
    "청동색": "갈색", "청동빛 녹색": "초록", "청동 녹색": "초록", "청동녹색": "초록",
    "녹갈색": "갈색", "짙은 녹갈색": "갈색", "초록빛 갈색": "갈색",
    # 기타
    "붉은 반점": "빨강", "자주색 반점": "보라",
}

LABEL_TO_GROUP = {
    "백색": "백색/미색", "미색": "백색/미색",
    "노랑": "노랑/주황", "주황": "노랑/주황", "살구": "노랑/주황",
    "빨강": "빨강/분홍", "분홍": "빨강/분홍", "다홍": "빨강/분홍",
    "연보라": "푸른색", "보라": "푸른색", "파랑": "푸른색", "하늘": "푸른색",
    "연두": "푸른색", "초록": "푸른색",
    "갈색": "갈색/검정", "검정": "갈색/검정",
}


def phase3_normalize_colors(plants: list) -> dict:
    """Phase 3: colorLabels 16종 정규화 + colorGroup 재매핑"""
    logging.info("=" * 50)
    logging.info("[Phase 3] colorLabels 정규화 + colorGroup 재매핑")

    label_changed = 0
    group_changed = 0
    unmapped = Counter()

    for p in plants:
        ci = p.get("colorInfo", {})
        old_labels = ci.get("colorLabels", [])

        new_labels = []
        for lbl in old_labels:
            if lbl in VALID_COLOR_LABELS:
                new_labels.append(lbl)
            elif lbl in LABEL_MAP:
                new_labels.append(LABEL_MAP[lbl])
            else:
                unmapped[lbl] += 1
                new_labels.append(lbl)

        # 중복 제거 (순서 유지)
        seen = set()
        deduped = []
        for lbl in new_labels:
            if lbl not in seen:
                seen.add(lbl)
                deduped.append(lbl)
        new_labels = deduped

        if old_labels != new_labels:
            ci["colorLabels"] = new_labels
            label_changed += 1

        # colorGroup 재매핑
        new_groups = []
        for lbl in new_labels:
            if lbl in LABEL_TO_GROUP:
                g = LABEL_TO_GROUP[lbl]
                if g not in new_groups:
                    new_groups.append(g)
        old_groups = ci.get("colorGroup", [])
        if old_groups != new_groups and new_groups:
            ci["colorGroup"] = new_groups
            group_changed += 1

    if unmapped:
        logging.warning(f"  매핑 없는 라벨: {dict(unmapped)}")
    logging.info(f"  colorLabels 변경: {label_changed}건, colorGroup 변경: {group_changed}건")
    return {"label": label_changed, "group": group_changed}


# ============================================================
# PHASE 4: 최종 정리 (hex 1:1, scentTags, habitat)
# ============================================================

def phase4_final_cleanup(plants: list) -> dict:
    """Phase 4: hex↔label 1:1, 빈 scentTags→["무향"], habitat 누락 채움"""
    logging.info("=" * 50)
    logging.info("[Phase 4] 최종 정리")

    # 4-1. hex↔label 불일치: label 기준으로 hex 자름
    hex_fixed = 0
    for p in plants:
        ci = p.get("colorInfo", {})
        hexes = ci.get("hexCodes", [])
        labels = ci.get("colorLabels", [])
        if len(hexes) > len(labels) and len(labels) > 0:
            ci["hexCodes"] = hexes[:len(labels)]
            hex_fixed += 1

    # 4-2. 무향인데 scentTags 비어있으면 ["무향"] 삽입
    tag_fixed = 0
    for p in plants:
        si = p.get("scentInfo", {})
        tags = si.get("scentTags", [])
        groups = si.get("scentGroup", [])
        if not tags and "무향" in groups:
            si["scentTags"] = ["무향"]
            tag_fixed += 1

    # 4-3. habitat 누락: 같은 속(genus) 참고
    hab_fixed = 0
    genus_habitats: dict[str, list[str]] = {}
    for p in plants:
        sci = p.get("scientificName", "")
        parts = sci.split()
        if len(parts) >= 2:
            genus = parts[0]
            habitat = p.get("habitat", "")
            if habitat:
                genus_habitats.setdefault(genus, []).append(habitat)

    for p in plants:
        if p.get("habitat", ""):
            continue
        sci = p.get("scientificName", "")
        parts = sci.split()
        if len(parts) < 2:
            continue
        genus = parts[0]
        candidates = genus_habitats.get(genus, [])
        if candidates:
            most_common = Counter(candidates).most_common(1)[0][0]
            p["habitat"] = most_common
            hab_fixed += 1
            logging.info(f"  habitat 채움: {p.get('name', sci)} → {most_common}")

    logging.info(f"  hex↔label 수정: {hex_fixed}건, scentTags 삽입: {tag_fixed}건, habitat 채움: {hab_fixed}건")
    return {"hex": hex_fixed, "tag": tag_fixed, "hab": hab_fixed}


# ============================================================
# VALIDATION & STATS
# ============================================================

def validate_and_report(plants: list):
    """최종 검증 및 통계 출력"""
    logging.info("=" * 50)
    logging.info("[검증] 최종 데이터 품질 확인")

    # flowerGroup
    fg_dist = Counter(p.get("flowerInfo", {}).get("flowerGroup", "") for p in plants)
    remaining_gita = fg_dist.get("기타", 0)
    logging.info(f"  [flowerGroup] 총 {len(plants)}건")
    for g in sorted(FLOWER_GROUPS):
        logging.info(f"    {g}: {fg_dist.get(g, 0)}건")
    if remaining_gita:
        logging.warning(f"    ⚠ '기타' 잔존: {remaining_gita}건")

    # scentGroup
    sg_dist = Counter(g for p in plants for g in p.get("scentInfo", {}).get("scentGroup", []))
    remaining_no = sg_dist.get("향 없음", 0)
    logging.info(f"  [scentGroup]")
    for g, cnt in sg_dist.most_common():
        logging.info(f"    {g}: {cnt}건")
    if remaining_no:
        logging.warning(f"    ⚠ '향 없음' 잔존: {remaining_no}건")

    # colorLabels
    all_labels = Counter(l for p in plants for l in p.get("colorInfo", {}).get("colorLabels", []))
    invalid_labels = sum(1 for p in plants for l in p.get("colorInfo", {}).get("colorLabels", []) if l not in VALID_COLOR_LABELS)
    logging.info(f"  [colorLabels] 비규격 잔존: {invalid_labels}건")

    # hex↔label
    hex_mismatch = sum(
        1 for p in plants
        if len(p.get("colorInfo", {}).get("hexCodes", []))
        != len(p.get("colorInfo", {}).get("colorLabels", []))
    )
    logging.info(f"  [hex↔label] 불일치: {hex_mismatch}건")

    # scentTags 비어있음
    empty_tags = sum(
        1 for p in plants
        if not p.get("scentInfo", {}).get("scentTags", [])
    )
    logging.info(f"  [scentTags] 비어있음: {empty_tags}건")

    # habitat 누락
    empty_habitat = sum(1 for p in plants if not p.get("habitat", ""))
    logging.info(f"  [habitat] 누락: {empty_habitat}건")

    # 전체 판정
    issues = remaining_gita + remaining_no + invalid_labels + hex_mismatch + empty_tags + empty_habitat
    if issues == 0:
        logging.info("  ✓ 모든 검증 통과")
    else:
        logging.warning(f"  총 {issues}건 이슈 잔존")

    logging.info("=" * 50)


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Floripedia 후처리 통합 스크립트")
    parser.add_argument("--skip-gemini", action="store_true",
                        help="Phase 1(Gemini 배치) 스킵. 이미 패치된 파일에 2~4만 재적용")
    parser.add_argument("--input", type=str, default=None,
                        help="입력 파일 경로 (기본: v2_data.json, --skip-gemini 시 v2_data_patched.json)")
    args = parser.parse_args()

    # 입력 파일 결정
    if args.input:
        input_path = args.input
    elif args.skip_gemini:
        input_path = OUTPUT_PATH  # 이미 패치된 파일에서 시작
    else:
        input_path = INPUT_PATH

    logging.info(f"Loading {input_path}")
    with open(input_path, "r", encoding="utf-8") as f:
        plants = json.load(f)
    logging.info(f"  {len(plants)}건 로드")

    # Phase 1
    if not args.skip_gemini:
        phase1_gemini_patch(plants)
    else:
        logging.info("[Phase 1] 스킵 (--skip-gemini)")

    # Phase 2
    phase2_fix_remaining(plants)

    # Phase 3
    phase3_normalize_colors(plants)

    # Phase 4
    phase4_final_cleanup(plants)

    # 저장
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(plants, f, ensure_ascii=False, indent=2)
    logging.info(f"저장: {OUTPUT_PATH}")

    # 검증
    validate_and_report(plants)


if __name__ == "__main__":
    main()
