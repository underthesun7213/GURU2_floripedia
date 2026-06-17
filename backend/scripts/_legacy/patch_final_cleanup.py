"""
v2_data_patched.json 최종 정리 (Gemini 호출 없음).
1. hexCodes↔colorLabels 불일치: hex 중복 제거로 1:1 맞춤
2. 무향 식물의 빈 scentTags → ["무향"] 삽입
3. 아카에나 엑시구아 habitat 누락 → 같은 속 참고 삽입
"""

import json
import os
import logging
from collections import Counter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "v2_data_patched.json",
)


def fix_hex_label_mismatch(plants: list) -> int:
    """hex 개수 > label 개수일 때, label 기준으로 대표 hex만 남긴다."""
    fixed = 0
    for p in plants:
        ci = p.get("colorInfo", {})
        hexes = ci.get("hexCodes", [])
        labels = ci.get("colorLabels", [])
        if len(hexes) > len(labels) and len(labels) > 0:
            # label 개수만큼 hex 앞에서 자름
            ci["hexCodes"] = hexes[:len(labels)]
            fixed += 1
    return fixed


def fix_empty_scent_tags(plants: list) -> int:
    """scentGroup이 무향이고 scentTags가 비어있으면 ["무향"] 삽입."""
    fixed = 0
    for p in plants:
        si = p.get("scentInfo", {})
        tags = si.get("scentTags", [])
        groups = si.get("scentGroup", [])
        if not tags and "무향" in groups:
            si["scentTags"] = ["무향"]
            fixed += 1
    return fixed


def fix_missing_habitat(plants: list) -> int:
    """habitat이 비어있는 식물을 같은 속(genus) 식물 참고해서 채운다."""
    fixed = 0
    # 속(genus)별 habitat 수집
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
        habitat = p.get("habitat", "")
        if habitat:
            continue
        sci = p.get("scientificName", "")
        parts = sci.split()
        if len(parts) < 2:
            continue
        genus = parts[0]
        candidates = genus_habitats.get(genus, [])
        if candidates:
            # 가장 많이 나오는 habitat 사용
            most_common = Counter(candidates).most_common(1)[0][0]
            p["habitat"] = most_common
            fixed += 1
            logging.info(f"  habitat 채움: {p.get('koreanName', sci)} → {most_common}")

    return fixed


def main():
    logging.info(f"Loading {DATA_PATH}")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        plants = json.load(f)
    logging.info(f"  {len(plants)}건 로드")

    hex_fixed = fix_hex_label_mismatch(plants)
    tag_fixed = fix_empty_scent_tags(plants)
    hab_fixed = fix_missing_habitat(plants)

    # 저장
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(plants, f, ensure_ascii=False, indent=2)

    # 검증
    hex_mismatch = sum(
        1 for p in plants
        if len(p.get("colorInfo", {}).get("hexCodes", []))
        != len(p.get("colorInfo", {}).get("colorLabels", []))
    )
    empty_tags = sum(
        1 for p in plants
        if not p.get("scentInfo", {}).get("scentTags", [])
        and "무향" in p.get("scentInfo", {}).get("scentGroup", [])
    )
    empty_habitat = sum(1 for p in plants if not p.get("habitat", ""))

    logging.info("=" * 50)
    logging.info(f"[1] hex↔label 불일치 수정: {hex_fixed}건 (잔존: {hex_mismatch}건)")
    logging.info(f"[2] 빈 scentTags→['무향'] 삽입: {tag_fixed}건 (잔존: {empty_tags}건)")
    logging.info(f"[3] habitat 누락 채움: {hab_fixed}건 (잔존: {empty_habitat}건)")
    logging.info(f"저장: {DATA_PATH}")
    logging.info("=" * 50)


if __name__ == "__main__":
    main()
