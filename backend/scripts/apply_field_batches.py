# -*- coding: utf-8 -*-
"""
에이전트 배치 산출물을 검증 후 DB + v2.json 반영 (habitat / usage 공용).

  py scripts/apply_field_batches.py --field habitat            # 검증만
  py scripts/apply_field_batches.py --field habitat --commit
  py scripts/apply_field_batches.py --field usage --commit

입력: data/new_species/{field}_batch_*.json
  habitat 항목: {"_id": "...", "habitat": "..."}
  usage   항목: {"_id": "...", "usage": ["...", ...]}
"""
import argparse
import glob
import json
import os
import sys

import certifi
from pymongo import MongoClient, UpdateOne

sys.path.insert(0, ".")
from app.core.config import settings

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
NEW_DIR = os.path.join(DATA, "new_species")
V2 = os.path.join(DATA, "floripedia_v2.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", required=True, choices=["habitat", "usage"])
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    targets_path = os.path.join(NEW_DIR, f"{args.field}_targets.json")
    targets = {t["_id"]: t for t in json.load(open(targets_path, encoding="utf-8"))}

    items, errors, seen = {}, [], set()
    for f in sorted(glob.glob(os.path.join(NEW_DIR, f"{args.field}_batch_*.json"))):
        for it in json.load(open(f, encoding="utf-8")):
            pid = it.get("_id")
            val = it.get(args.field)
            if pid in seen:
                errors.append(f"{pid}: 배치 간 중복")
                continue
            seen.add(pid)
            if pid not in targets:
                errors.append(f"{pid}: 대상 목록에 없음")
                continue
            if args.field == "habitat":
                text = (val or "").strip()
                if not (30 <= len(text) <= 300) or "니다" not in text:
                    errors.append(f"{pid} {targets[pid]['name']}: habitat 형식 미달 ({len(text)}자)")
                    continue
                items[pid] = text
            else:  # usage: 리스트, 합쳐서 습니다체·길이 검증
                lst = [s.strip() for s in (val or []) if (s or "").strip()]
                joined = " ".join(lst)
                if not lst or not (30 <= len(joined) <= 450) or "니다" not in joined:
                    errors.append(f"{pid} {targets[pid]['name']}: usage 형식 미달 ({len(joined)}자)")
                    continue
                items[pid] = lst

    missing = set(targets) - set(items)
    print(f"[{args.field}] 대상 {len(targets)} | 수집 {len(seen)} | 유효 {len(items)} | "
          f"검증 실패 {len(errors)} | 미생성 {len(missing)}")
    for e in errors[:20]:
        print("  -", e)
    if missing and len(missing) <= 25:
        print("  미생성:", sorted(missing, key=lambda x: int(x) if x.isdigit() else 0))

    if not args.commit:
        print("\n[dry-run] --commit 으로 반영")
        return
    if not items:
        print("반영할 항목 없음")
        return

    db_field = "habitat" if args.field == "habitat" else "horticulture.usage"
    c = MongoClient(settings.MONGO_URI, tlsCAFile=certifi.where())
    db = c[settings.MONGODB_DB_NAME]
    ops = [UpdateOne({"_id": pid}, {"$set": {db_field: v}}) for pid, v in items.items()]
    res = db.plants.bulk_write(ops, ordered=False)
    print(f"[DB] matched={res.matched_count} modified={res.modified_count}")

    v2 = json.load(open(V2, encoding="utf-8"))
    n = 0
    for e in v2:
        if e["_id"] in items:
            if args.field == "habitat":
                e["habitat"] = items[e["_id"]]
            else:
                e.setdefault("horticulture", {})["usage"] = items[e["_id"]]
            n += 1
    json.dump(v2, open(V2, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[v2] {n}건 동기화")


if __name__ == "__main__":
    main()
