# -*- coding: utf-8 -*-
"""
이름 표시명에서 지역/이명 접미사 (중)/(북) 등 괄호 표기 제거 (2026-07-16).

원전 목록의 지역 표기가 표시명에 새어든 6종:
  1545 가는할미꽃(중), 1710 사후란(중), 1797 각시바위돈꽃(중),
  1866 울릉단풍나무(중), 1792 넓은잎바위솔(북), 1799 알돌나물(북)
괄호 제거 후 이름 충돌 없음 확인됨. 원본 표기는 searchKeywords에 보존(검색 호환).

DRY-RUN 기본. 실제 반영 --commit.
"""
import sys, os, io, json, re, argparse
sys.path.insert(0, ".")
import certifi
from pymongo import MongoClient
from app.core.config import settings

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
V2 = os.path.join(DATA, "floripedia_v2.json")
PAT = re.compile(r"\s*[\(（][^\)）]*[\)）]\s*")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--commit", action="store_true")
    dry = not ap.parse_args().commit
    print(f"=== 이름 접미사 정리 ({'DRY-RUN' if dry else 'COMMIT'}) ===")
    c = MongoClient(settings.MONGO_URI, tlsCAFile=certifi.where())
    db = c[settings.MONGODB_DB_NAME]

    targets = list(db.plants.find({"name": {"$regex": r"[\(（]"}}, {"_id":1,"name":1,"searchKeywords":1}))
    plan = []
    for p in targets:
        new = PAT.sub("", p["name"]).strip()
        if new and new != p["name"]:
            plan.append((p["_id"], p["name"], new, p.get("searchKeywords") or []))
    for pid, old, new, kw in plan:
        print(f"  {pid}  '{old}' -> '{new}'  (원본 searchKeywords 보존: {'있음' if old in kw else '추가'})")

    if dry:
        print("\nDRY-RUN — 변경 없음. --commit 으로 반영."); c.close(); return

    for pid, old, new, kw in plan:
        newkw = kw if old in kw else (kw + [old])   # 원본 표기 검색 보존
        db.plants.update_one({"_id": pid}, {"$set": {"name": new, "searchKeywords": newkw}})
    print(f"[DB] {len(plan)}종 이름 갱신")

    if os.path.exists(V2):
        data = json.load(io.open(V2, encoding="utf-8"))
        bak = V2 + ".pre_namefix_20260716.bak"
        if not os.path.exists(bak):
            json.dump(data, io.open(bak,"w",encoding="utf-8"), ensure_ascii=False)
            print(f"[v2] 백업 → {bak}")
        idmap = {pid: (new, old) for pid, old, new, kw in plan}
        n=0
        for p in data:
            pid = str(p.get("_id"))
            if pid in idmap:
                new, old = idmap[pid]
                p["name"] = new
                kw = p.get("searchKeywords") or []
                if old not in kw: kw.append(old)
                p["searchKeywords"] = kw
                n+=1
        json.dump(data, io.open(V2,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"[v2] {n}종 이름 갱신")
    c.close(); print("\n=== 완료 ===")

if __name__ == "__main__":
    main()
