"""
v2_data_patched.json의 colorLabels를 규격 16종으로 정규화.
colorGroup도 규격 5종에 맞춰 재매핑.
Gemini 호출 없이 키워드 매핑.
"""

import json
import os
import sys
import logging
from collections import Counter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "v2_data_patched.json",
)

VALID_LABELS = {"백색", "연두", "초록", "노랑", "빨강", "분홍", "연보라", "보라", "파랑", "하늘", "살구", "갈색", "검정", "다홍", "주황", "미색"}

COLOR_GROUPS = {"백색/미색", "노랑/주황", "빨강/분홍", "푸른색", "갈색/검정"}

# 비규격 → 규격 매핑 (우선순위 순서)
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
    # 남색/청보라 → 파랑
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
    # 회색/은색 → 미색 or 갈색
    "회색": "미색", "연회색": "미색", "옅은 회색": "미색",
    "은회색": "미색", "은녹색": "연두", "회녹색": "초록", "연회녹색": "연두",
    "짙은 회녹색": "초록", "청회색": "하늘", "푸른회색": "하늘",
    # 청동/녹갈 계열
    "청동색": "갈색", "청동빛 녹색": "초록", "청동 녹색": "초록", "청동녹색": "초록",
    "녹갈색": "갈색", "짙은 녹갈색": "갈색", "초록빛 갈색": "갈색",
    # 기타
    "붉은 반점": "빨강", "자주색 반점": "보라",
    "연회녹색": "연두",
}

# colorLabel → colorGroup 매핑
LABEL_TO_GROUP = {
    "백색": "백색/미색", "미색": "백색/미색",
    "노랑": "노랑/주황", "주황": "노랑/주황", "살구": "노랑/주황",
    "빨강": "빨강/분홍", "분홍": "빨강/분홍", "다홍": "빨강/분홍",
    "연보라": "푸른색", "보라": "푸른색", "파랑": "푸른색", "하늘": "푸른색",
    "연두": "푸른색", "초록": "푸른색",
    "갈색": "갈색/검정", "검정": "갈색/검정",
}


def main():
    logging.info(f"Loading {DATA_PATH}")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        plants = json.load(f)
    logging.info(f"  {len(plants)}건 로드")

    label_changed = 0
    group_changed = 0
    unmapped = Counter()

    for p in plants:
        ci = p.get("colorInfo", {})
        old_labels = ci.get("colorLabels", [])

        # 1. colorLabels 정규화
        new_labels = []
        for l in old_labels:
            if l in VALID_LABELS:
                new_labels.append(l)
            elif l in LABEL_MAP:
                new_labels.append(LABEL_MAP[l])
            else:
                unmapped[l] += 1
                # fallback: 그냥 제거하지 않고 가장 가까운 것 시도
                new_labels.append(l)

        # 중복 제거 (순서 유지)
        seen = set()
        deduped = []
        for l in new_labels:
            if l not in seen:
                seen.add(l)
                deduped.append(l)
        new_labels = deduped

        if old_labels != new_labels:
            ci["colorLabels"] = new_labels
            label_changed += 1

        # 2. colorGroup 재매핑 (colorLabels 기반)
        new_groups = []
        for l in new_labels:
            if l in LABEL_TO_GROUP:
                g = LABEL_TO_GROUP[l]
                if g not in new_groups:
                    new_groups.append(g)

        old_groups = ci.get("colorGroup", [])
        if old_groups != new_groups and new_groups:
            ci["colorGroup"] = new_groups
            group_changed += 1

    # 저장
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(plants, f, ensure_ascii=False, indent=2)

    # 통계
    all_labels = Counter(l for p in plants for l in p.get("colorInfo", {}).get("colorLabels", []))
    all_groups = Counter(g for p in plants for g in p.get("colorInfo", {}).get("colorGroup", []))
    empty_group = sum(1 for p in plants if not p.get("colorInfo", {}).get("colorGroup"))
    invalid = sum(1 for p in plants for l in p.get("colorInfo", {}).get("colorLabels", []) if l not in VALID_LABELS)

    logging.info("=" * 50)
    logging.info(f"colorLabels 변경: {label_changed}건")
    logging.info(f"colorGroup 변경: {group_changed}건")
    logging.info(f"[colorLabels 분포]")
    for l, cnt in all_labels.most_common():
        tag = "OK" if l in VALID_LABELS else "XX"
        logging.info(f"  [{tag}] {l}: {cnt}")
    logging.info(f"[colorGroup 분포]")
    for g, cnt in all_groups.most_common():
        logging.info(f"  {g}: {cnt}")
    logging.info(f"colorGroup 비어있음: {empty_group}건")
    logging.info(f"비규격 라벨 잔존: {invalid}건")
    if unmapped:
        logging.warning(f"매핑 없는 라벨: {dict(unmapped)}")
    logging.info(f"저장: {DATA_PATH}")
    logging.info("=" * 50)


if __name__ == "__main__":
    main()
