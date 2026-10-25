"""
new_species/merged.json 에 _id를 부여하고 floripedia_v2.json 에 추가.

- _id: 기존 최대 숫자 _id + 1 부터 순차 부여 (문자열)
- imageUrl/images는 부여하지 않음 (fix_missing_images.py가 채움)
- v2.json 백업 생성 후 추가

사용:
    python scripts/append_new_species.py            # dry-run
    python scripts/append_new_species.py --commit
"""
import argparse
import json
import os
import shutil
from datetime import date

BASE = os.path.join(os.path.dirname(__file__), "..", "data")
MERGED = os.path.join(BASE, "new_species", "merged.json")
V2 = os.path.join(BASE, "floripedia_v2.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    v2 = json.load(open(V2, encoding="utf-8"))
    new = json.load(open(MERGED, encoding="utf-8"))

    max_id = max(int(e["_id"]) for e in v2 if str(e["_id"]).isdigit())
    existing_names = {e["name"] for e in v2}

    dup = [p["name"] for p in new if p["name"] in existing_names]
    if dup:
        raise SystemExit(f"ERROR: v2에 이미 존재: {dup}")

    next_id = max_id + 1
    for p in new:
        p["_id"] = str(next_id)
        next_id += 1

    print(f"기존 {len(v2)}종 (max _id {max_id}) + 신규 {len(new)}종 "
          f"→ {len(v2) + len(new)}종, 신규 _id {new[0]['_id']}~{new[-1]['_id']}")

    if not args.commit:
        print("[dry-run] --commit 으로 실제 반영")
        return

    bak = V2 + f".pre_landscaping_{date.today().strftime('%Y%m%d')}.bak"
    shutil.copyfile(V2, bak)
    print(f"백업: {bak}")

    v2.extend(new)
    json.dump(v2, open(V2, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"저장: {V2} ({len(v2)}종)")

    # merged.json에도 _id 반영 저장 (이미지 파이프라인 추적용)
    json.dump(new, open(MERGED, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("merged.json에 _id 반영")


if __name__ == "__main__":
    main()
