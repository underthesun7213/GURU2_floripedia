# -*- coding: utf-8 -*-
"""
학명 정합 스캔(sci_check_c*.json)의 MISMATCH 교정을 DB + v2.json 반영.

- correct_sci가 있는 MISMATCH만 적용, 교정 후 학명이 기존 다른 종과
  충돌(속+종 일치)하면 건너뛰고 보고.
- taxonomy.genus/species도 함께 갱신.
- 제외: 259(살비아 — 키워드 보강으로 대체), 344(베고니아 — 신규종과 중복이라 보류)

  py scripts/apply_sci_corrections.py            # dry-run
  py scripts/apply_sci_corrections.py --commit
"""
import argparse
import glob
import json
import os
import sys

import certifi
from pymongo import MongoClient

sys.path.insert(0, ".")
from app.core.config import settings

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
NEW_DIR = os.path.join(DATA, "new_species")
V2 = os.path.join(DATA, "floripedia_v2.json")

EXCLUDE = {"259", "344"}
# 살비아(259) 검색성 보강: 세이지 별칭 추가
EXTRA_KEYWORDS = {"259": ["세이지", "커먼세이지"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    fixes = {}
    for f in sorted(glob.glob(os.path.join(NEW_DIR, "sci_check_c*.json"))):
        for it in json.load(open(f, encoding="utf-8")):
            if it.get("verdict") == "MISMATCH" and (it.get("correct_sci") or "").strip():
                if it["_id"] not in EXCLUDE:
                    fixes[it["_id"]] = it

    v2 = json.load(open(V2, encoding="utf-8"))
    # 충돌 검사: 교정 후 (속, 종)이 '다른' 종과 겹치면 skip
    sci_index = {}
    for e in v2:
        w = (e.get("scientificName") or "").lower().split()
        if len(w) >= 2:
            sci_index.setdefault((w[0], w[1]), []).append(e["_id"])

    applied, skipped = {}, []
    for pid, it in fixes.items():
        w = it["correct_sci"].lower().split()
        key = (w[0], w[1]) if len(w) >= 2 else None
        owners = [o for o in sci_index.get(key, []) if o != pid]
        if owners:
            skipped.append((pid, it["name"], it["correct_sci"], f"기존 {owners}와 충돌"))
            continue
        applied[pid] = it

    print(f"MISMATCH 교정 대상 {len(fixes)} | 적용 {len(applied)} | 충돌 skip {len(skipped)}")
    for pid, it in sorted(applied.items(), key=lambda x: int(x[0])):
        print(f"  {pid} {it['name']}: {it['sci']} -> {it['correct_sci']}")
    for s in skipped:
        print("  SKIP", s)

    if not args.commit:
        print("\n[dry-run] --commit 으로 반영")
        return

    c = MongoClient(settings.MONGO_URI, tlsCAFile=certifi.where())
    db = c[settings.MONGODB_DB_NAME]

    for pid, it in applied.items():
        sci = it["correct_sci"].strip()
        w = sci.split()
        sets = {"scientificName": sci, "taxonomy.genus": w[0]}
        if len(w) >= 2:
            sets["taxonomy.species"] = w[1]
        db.plants.update_one({"_id": pid}, {"$set": sets})

    for pid, kws in EXTRA_KEYWORDS.items():
        db.plants.update_one({"_id": pid}, {"$addToSet": {"searchKeywords": {"$each": kws}}})

    n = 0
    for e in v2:
        if e["_id"] in applied:
            sci = applied[e["_id"]]["correct_sci"].strip()
            w = sci.split()
            e["scientificName"] = sci
            e.setdefault("taxonomy", {})["genus"] = w[0]
            if len(w) >= 2:
                e["taxonomy"]["species"] = w[1]
            n += 1
        if e["_id"] in EXTRA_KEYWORDS:
            for kw in EXTRA_KEYWORDS[e["_id"]]:
                if kw not in e.setdefault("searchKeywords", []):
                    e["searchKeywords"].append(kw)
    json.dump(v2, open(V2, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[DB+v2] 교정 {n}건 + 키워드 보강 {len(EXTRA_KEYWORDS)}건 반영")


if __name__ == "__main__":
    main()
