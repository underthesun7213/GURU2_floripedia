# -*- coding: utf-8 -*-
"""
preContent를 카드용 짧은 블러브로 단축 (2026-07-16).

배경: preContent는 앱에서 '추천/카드 설명'으로만 노출(상세의 식물설명 섹션 제거됨).
원문은 150~500자라 카드 2~3줄에 안 들어가 `...`로 잘림. 사용자 결정: 시안처럼 컴팩트하게
→ preContent 데이터를 첫 문장 위주(대략 1문장, 과도하게 길면 어절 경계 컷)로 줄인다.
전문은 백업(precontent_full_backup_20260716.json)해서 복원 가능.

  py scripts/shorten_precontent.py            # DRY-RUN 미리보기
  py scripts/shorten_precontent.py --commit    # 반영(백업 후, DB + v2.json)
"""
import sys, os, io, json, re, argparse
sys.path.insert(0, ".")
import certifi
from pymongo import MongoClient
from app.core.config import settings

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
V2 = os.path.join(DATA, "floripedia_v2.json")
MAXLEN = 95   # 첫 문장이 이보다 길면 어절 경계로 컷

def shorten(pc):
    if not pc:
        return pc
    pc = pc.strip()
    # 첫 문장(마침표/느낌표/물음표까지)
    m = re.search(r"[.!?]", pc)
    first = pc[:m.end()].strip() if m else pc
    if len(first) <= MAXLEN:
        return first
    # 너무 긴 단문 → 어절 경계 컷(마침표 없이 자연스럽게)
    cut = first[:MAXLEN]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,·")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--commit", action="store_true")
    dry = not ap.parse_args().commit
    print(f"=== preContent 단축 ({'DRY-RUN' if dry else 'COMMIT'}) ===")
    c = MongoClient(settings.MONGO_URI, tlsCAFile=certifi.where()); db = c[settings.MONGODB_DB_NAME]

    docs = list(db.plants.find({}, {"_id":1,"name":1,"horticulture":1}))
    plan = []
    for d in docs:
        h = d.get("horticulture") or {}
        old = h.get("preContent") or ""
        new = shorten(old)
        if new != old:
            plan.append((d["_id"], d["name"], old, new))
    lens = [len(n) for _,_,_,n in plan]
    print(f"대상 {len(plan)}종 / 전체 {len(docs)}종")
    if lens:
        import statistics
        print(f"단축 후 길이: min={min(lens)} p50={sorted(lens)[len(lens)//2]} max={max(lens)} avg={sum(lens)/len(lens):.0f}")
    print("\n샘플 5:")
    for pid, name, old, new in plan[:5]:
        print(f"  [{name}] ({len(old)}→{len(new)}자)\n    {new}")

    if dry:
        print("\nDRY-RUN — 변경 없음. --commit 으로 반영."); c.close(); return

    # 백업(전문)
    bpath = os.path.join(DATA, "precontent_full_backup_20260716.json")
    if not os.path.exists(bpath):
        backup = {d["_id"]: (d.get("horticulture") or {}).get("preContent","") for d in docs}
        json.dump(backup, io.open(bpath,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"[백업] 전문 {len(backup)}종 → {bpath}")

    # DB 반영
    n = 0
    for pid, name, old, new in plan:
        db.plants.update_one({"_id": pid}, {"$set": {"horticulture.preContent": new}})
        n += 1
    print(f"[DB] {n}종 preContent 단축")

    # v2.json 동기화
    if os.path.exists(V2):
        data = json.load(io.open(V2, encoding="utf-8"))
        bak = V2 + ".pre_shorten_20260716.bak"
        if not os.path.exists(bak):
            json.dump(data, io.open(bak,"w",encoding="utf-8"), ensure_ascii=False)
        nmap = {pid: new for pid,_,_,new in plan}
        n2 = 0
        for p in data:
            pid = str(p.get("_id"))
            if pid in nmap and isinstance(p.get("horticulture"), dict):
                p["horticulture"]["preContent"] = nmap[pid]; n2 += 1
        json.dump(data, io.open(V2,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"[v2] {n2}종 동기화")
    c.close(); print("\n=== 완료 ===")

if __name__ == "__main__":
    main()
