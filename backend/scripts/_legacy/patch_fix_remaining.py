"""
v2_data_patched.json에 남은 '기타', '향 없음' 정리.
Gemini 호출 없이 키워드 매칭 + 단순 치환.
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

FLOWER_GROUPS = {"사랑/고백", "위로/슬픔", "감사/존경", "이별/그리움", "행복/즐거움"}

# 우선순위 순서대로 매칭 (먼저 걸리는 게 우선)
FG_KEYWORDS = [
    ("이별/그리움", ["이별", "그리움", "기다림", "추억", "복수", "질투", "미움"]),
    ("위로/슬픔", ["위로", "치유", "고독", "평화", "안식", "보호", "용기", "위험", "독"]),
    ("사랑/고백", ["사랑", "고백", "아름다움", "우아", "신비", "매력", "순수", "청초", "섬세", "애교"]),
    ("감사/존경", ["감사", "존경", "겸손", "고귀", "품위", "숭고", "인내", "강인", "성실", "끈기", "경계", "기사"]),
    ("행복/즐거움", ["행복", "기쁨", "즐거움", "번영", "희망", "축복", "새로운 시작", "기쁜", "봄", "부귀", "자유", "단결"]),
]


def match_flower_group(language: str) -> str:
    if not language:
        return "행복/즐거움"
    for group, keywords in FG_KEYWORDS:
        for kw in keywords:
            if kw in language:
                return group
    return "행복/즐거움"


def main():
    logging.info(f"Loading {DATA_PATH}")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        plants = json.load(f)
    logging.info(f"  {len(plants)}건 로드")

    fg_changed = 0
    sg_changed = 0

    for p in plants:
        # 1. 기타 → 꽃말 기반 강제 분류
        fg = p.get("flowerInfo", {}).get("flowerGroup", "")
        if fg == "기타" or fg not in FLOWER_GROUPS:
            lang = p.get("flowerInfo", {}).get("language", "")
            new_fg = match_flower_group(lang)
            p["flowerInfo"]["flowerGroup"] = new_fg
            fg_changed += 1

        # 2. 향 없음 → 무향
        sg = p.get("scentInfo", {}).get("scentGroup", [])
        new_sg = ["무향" if g == "향 없음" else g for g in sg]
        if new_sg != sg:
            p["scentInfo"]["scentGroup"] = new_sg
            sg_changed += 1

        # scentTags에서도 "향 없음" 제거
        st = p.get("scentInfo", {}).get("scentTags", [])
        new_st = ["무향" if t == "향 없음" else t for t in st]
        if new_st != st:
            p["scentInfo"]["scentTags"] = new_st

    # 저장
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(plants, f, ensure_ascii=False, indent=2)

    # 통계
    fg_dist = Counter(p.get("flowerInfo", {}).get("flowerGroup", "") for p in plants)
    sg_dist = Counter(g for p in plants for g in p.get("scentInfo", {}).get("scentGroup", []))

    logging.info("=" * 50)
    logging.info(f"기타→강제분류: {fg_changed}건")
    logging.info(f"향 없음→무향: {sg_changed}건")
    logging.info("[flowerGroup]")
    for g in sorted(FLOWER_GROUPS):
        logging.info(f"  {g}: {fg_dist.get(g, 0)}건")
    logging.info("[scentGroup]")
    for g, cnt in sg_dist.most_common():
        logging.info(f"  {g}: {cnt}건")

    # 잔존 검증
    remaining_gita = sum(1 for p in plants if p.get("flowerInfo", {}).get("flowerGroup") == "기타")
    remaining_no = sum(1 for p in plants if "향 없음" in p.get("scentInfo", {}).get("scentGroup", []))
    if remaining_gita or remaining_no:
        logging.warning(f"  잔존: 기타={remaining_gita}, 향 없음={remaining_no}")
    else:
        logging.info("  검증 통과: '기타', '향 없음' 없음")
    logging.info(f"저장: {DATA_PATH}")
    logging.info("=" * 50)


if __name__ == "__main__":
    main()
