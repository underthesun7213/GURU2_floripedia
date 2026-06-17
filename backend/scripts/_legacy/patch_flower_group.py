"""
v2_data.json의 flowerGroup + scentInfo를 Gemini API로 일괄 패치.
500건을 배치(50건씩)로 묶어 Gemini 호출 최소화.
"""

import json
import os
import sys
import time
import logging
import shutil
from collections import Counter
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.5-flash-lite")
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "v2_data.json",
)

FLOWER_GROUPS = {"사랑/고백", "위로/슬픔", "감사/존경", "이별/그리움", "행복/즐거움"}
SCENT_GROUPS = {"달콤·화사", "싱그럽고 시원", "은은·차분", "무향"}
BATCH_SIZE = 30
RATE_LIMIT = 2.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def call_gemini(prompt: str, max_retries: int = 3) -> str:
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


_FG_KEYWORD_MAP = {
    "사랑/고백": ["사랑", "고백", "아름다움", "우아", "신비", "매력", "순수", "고귀한 아름다움"],
    "감사/존경": ["감사", "존경", "겸손", "고귀", "품위", "숭고", "인내", "강인", "성실", "끈기"],
    "행복/즐거움": ["행복", "기쁨", "즐거움", "번영", "희망", "축복", "새로운 시작", "기쁜"],
    "위로/슬픔": ["위로", "치유", "고독", "평화", "안식", "보호", "용기"],
    "이별/그리움": ["이별", "그리움", "기다림", "추억", "복수", "질투", "미움"],
}


def _match_flower_group(value: str) -> str:
    """Gemini가 반환한 값이 정확히 안 맞을 때 키워드 기반 강제 매칭"""
    if not value:
        return "행복/즐거움"
    value = value.strip()
    if value in FLOWER_GROUPS:
        return value
    # 부분 매칭: "사랑" → "사랑/고백"
    for group, keywords in _FG_KEYWORD_MAP.items():
        for kw in keywords:
            if kw in value or value in kw:
                return group
    return "행복/즐거움"


def patch_batch(batch: list[dict]) -> dict:
    """
    batch: [{"id": ..., "name": ..., "scientificName": ..., "language": ...}, ...]
    returns: {"id": {"flowerGroup": ..., "scentTags": [...], "scentGroup": [...]}, ...}
    """
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

    # 꽃말 룩업용
    batch_lang_map = {it["id"]: it["language"] for it in batch}

    result = call_gemini(prompt)
    try:
        parsed = json.loads(result)
        if not isinstance(parsed, dict):
            logging.error(f"  응답이 dict가 아님: {type(parsed)}")
            return {}
        # 유효성 검증
        validated = {}
        for pid, info in parsed.items():
            if not isinstance(info, dict):
                continue
            fg = info.get("flowerGroup", "")
            if fg not in FLOWER_GROUPS:
                fg = _match_flower_group(fg)
            # 2차 안전장치: 그래도 FLOWER_GROUPS에 없으면 꽃말 기반 매칭
            if fg not in FLOWER_GROUPS:
                fg = _match_flower_group(batch_lang_map.get(pid, ""))
            st = info.get("scentTags", [])
            if not isinstance(st, list):
                st = []
            # 비규격 태그 정리: "향 없음" → "무향"으로 통일
            st = ["무향" if t == "향 없음" else t for t in st]
            sg = info.get("scentGroup", [])
            if not isinstance(sg, list):
                sg = []
            # "향 없음" → "무향" 통일
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


def main():
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY 환경변수를 설정하세요.")
        sys.exit(1)

    # 1. 로드
    logging.info(f"Loading {DATA_PATH}")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        plants = json.load(f)
    logging.info(f"  {len(plants)}건 로드")

    # 2. 배치 구성
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

    # 4. Gemini 배치 호출
    id_to_patch: dict[str, dict] = {}
    for i, batch in enumerate(batches, 1):
        logging.info(f"  배치 [{i}/{len(batches)}] ({len(batch)}건)")
        result = patch_batch(batch)
        id_to_patch.update(result)
        logging.info(f"    → {len(result)}건 완료")

    # 5. habitat "원산지: " 접두사 제거
    for p in plants:
        h = p.get("habitat", "")
        if h.startswith("원산지: "):
            p["habitat"] = h[len("원산지: "):]
        elif h.startswith("원산지:"):
            p["habitat"] = h[len("원산지:"):]

    # 6. 패치 적용
    patched_fg = 0
    patched_scent = 0
    for p in plants:
        pid = p.get("_id", "")
        if pid not in id_to_patch:
            continue
        patch = id_to_patch[pid]

        # flowerGroup — 무조건 덮어쓰기
        new_fg = patch["flowerGroup"]
        p["flowerInfo"]["flowerGroup"] = new_fg
        patched_fg += 1

        # scentInfo — 무조건 덮어쓰기
        new_tags = patch["scentTags"]
        new_group = patch["scentGroup"]
        # scentTags에 "향 없음" 문자열 제거
        new_tags = [t for t in new_tags if t not in ("향 없음", "무향")]
        old_tags = p.get("scentInfo", {}).get("scentTags", [])
        old_group = p.get("scentInfo", {}).get("scentGroup", [])
        if old_tags != new_tags or old_group != new_group:
            p["scentInfo"]["scentTags"] = new_tags
            p["scentInfo"]["scentGroup"] = new_group
            patched_scent += 1

    # 6. 저장
    output_path = DATA_PATH.replace("v2_data.json", "v2_data_patched.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(plants, f, ensure_ascii=False, indent=2)

    # 7. 통계
    fg_dist = Counter(p.get("flowerInfo", {}).get("flowerGroup", "") for p in plants)
    sg_dist = Counter(
        g for p in plants
        for g in p.get("scentInfo", {}).get("scentGroup", [])
    )
    st_dist = Counter(
        t for p in plants
        for t in p.get("scentInfo", {}).get("scentTags", [])
    )
    empty_tags = sum(1 for p in plants if not p.get("scentInfo", {}).get("scentTags"))

    logging.info("=" * 50)
    logging.info(f"[flowerGroup] 변경: {patched_fg}건")
    for g in sorted(FLOWER_GROUPS):
        logging.info(f"  {g}: {fg_dist.get(g, 0)}건")

    logging.info(f"[scentGroup] 변경: {patched_scent}건")
    for g in sorted(SCENT_GROUPS):
        logging.info(f"  {g}: {sg_dist.get(g, 0)}건")

    logging.info(f"[scentTags] 비어있음: {empty_tags}건 / 상위 20개:")
    for tag, cnt in st_dist.most_common(20):
        logging.info(f"  {tag}: {cnt}건")
    # 8. 잔존 검증
    remaining_gita = sum(1 for p in plants if p.get("flowerInfo", {}).get("flowerGroup") == "기타")
    remaining_no_scent = sum(
        1 for p in plants
        if "향 없음" in p.get("scentInfo", {}).get("scentGroup", [])
    )
    if remaining_gita:
        logging.warning(f"  ⚠ flowerGroup '기타' 잔존: {remaining_gita}건")
    if remaining_no_scent:
        logging.warning(f"  ⚠ scentGroup '향 없음' 잔존: {remaining_no_scent}건")
    if not remaining_gita and not remaining_no_scent:
        logging.info("  검증 통과: '기타', '향 없음' 없음")
    logging.info(f"저장: {output_path}")
    logging.info("=" * 50)


if __name__ == "__main__":
    main()
