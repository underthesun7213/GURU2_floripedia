# -*- coding: utf-8 -*-
"""
season_batch_*.json (에이전트 생성 seasonDescription)을 검증 후 DB + v2.json 반영.

  py scripts/apply_season_descriptions.py            # 검증 리포트만
  py scripts/apply_season_descriptions.py --commit   # 실제 반영
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
TARGETS = os.path.join(NEW_DIR, "season_targets.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    targets = {t["_id"]: t for t in json.load(open(TARGETS, encoding="utf-8"))}

    items, errors, seen = {}, [], set()
    for f in sorted(glob.glob(os.path.join(NEW_DIR, "season_batch_*.json"))):
        for it in json.load(open(f, encoding="utf-8")):
            pid = it.get("_id")
            text = (it.get("seasonDescription") or "").strip()
            if pid in seen:
                errors.append(f"{pid}: 배치 간 중복")
                continue
            seen.add(pid)
            if pid not in targets:
                errors.append(f"{pid}: 대상 목록에 없음")
                continue
            if not (40 <= len(text) <= 260):
                errors.append(f"{pid} {targets[pid]['name']}: 길이 {len(text)}자 (40~260 밖)")
                continue
            if "니다" not in text:
                errors.append(f"{pid} {targets[pid]['name']}: 습니다체 아님")
                continue
            items[pid] = text

    missing = set(targets) - set(items)
    print(f"대상 {len(targets)} | 수집 {len(seen)} | 유효 {len(items)} | "
          f"검증 실패 {len(errors)} | 미생성 {len(missing)}")
    for e in errors[:20]:
        print("  -", e)
    if missing and len(missing) <= 20:
        print("  미생성:", sorted(missing, key=int))

    if not args.commit:
        print("\n[dry-run] --commit 으로 반영")
        return

    if not items:
        print("반영할 항목 없음")
        return

    c = MongoClient(settings.MONGO_URI, tlsCAFile=certifi.where())
    db = c[settings.MONGODB_DB_NAME]
    ops = [UpdateOne({"_id": pid}, {"$set": {"seasonDescription": t}})
           for pid, t in items.items()]
    res = db.plants.bulk_write(ops, ordered=False)
    print(f"[DB] matched={res.matched_count} modified={res.modified_count}")

    v2 = json.load(open(V2, encoding="utf-8"))
    n = 0
    for e in v2:
        if e["_id"] in items:
            e["seasonDescription"] = items[e["_id"]]
            n += 1
    json.dump(v2, open(V2, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[v2] {n}건 동기화")


if __name__ == "__main__":
    main()
