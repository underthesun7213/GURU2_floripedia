# -*- coding: utf-8 -*-
"""
변환된 스토리(습니다체) 적용.

converted/ 폴더의 converted_*.json (각 {key: after} dict)들을 병합해
DB plants.stories[idx].content + floripedia_v2.json 에 반영한다.
key 형식: "{pid}#{idx}".

  py scripts/apply_converted_stories.py           # 검증/미리보기(저장X)
  py scripts/apply_converted_stories.py --commit   # 실제 반영(백업 후)
"""
import sys, os, io, json, re, glob, argparse
sys.path.insert(0, ".")
import certifi
from pymongo import MongoClient
from app.core.config import settings

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CONV_DIR = os.path.join(DATA, "converted")
V2 = os.path.join(DATA, "floripedia_v2.json")
SENT_SPLIT = re.compile(r"[.!?]+")

def plain_endings(text):
    out=[]
    for s in SENT_SPLIT.split(text):
        s2=s.strip().strip('"\'”’‘“()（）~ ')
        if s2.endswith("다") and not s2.endswith("니다"):
            out.append(s2)
    return out

def load_converted():
    merged={}
    for f in sorted(glob.glob(os.path.join(CONV_DIR, "converted_*.json"))):
        d=json.load(io.open(f, encoding="utf-8"))
        merged.update(d)
    return merged

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--commit", action="store_true")
    dry=not ap.parse_args().commit
    conv=load_converted()
    print(f"수집된 변환: {len(conv)}건")

    # 원본 대상 목록과 대조
    targets=json.load(io.open(os.path.join(DATA,"stories_to_convert.json"), encoding="utf-8"))
    tkeys={t["key"] for t in targets}
    missing=tkeys - set(conv.keys())
    extra=set(conv.keys()) - tkeys
    print(f"대상 {len(tkeys)}건 중 미변환: {len(missing)}건, 대상외 변환: {len(extra)}건")
    if missing: print(f"  미변환 예: {sorted(missing)[:10]}")
    if extra: print(f"  대상외 예: {sorted(extra)[:10]}")

    # 품질 검증: 변환 결과에 평서 종결 잔존?
    resid=[k for k,v in conv.items() if plain_endings(v)]
    print(f"⚠️ 변환 후에도 평서 종결 잔존: {len(resid)}건 {resid[:10]}")

    if dry:
        print("\n검증 모드 — 저장 안 함. --commit 으로 반영."); return

    c=MongoClient(settings.MONGO_URI, tlsCAFile=certifi.where()); db=c[settings.MONGODB_DB_NAME]
    # 백업(원본 stories) — 최초 1회
    bpath=os.path.join(DATA,"stories_backup_pre_polite_20260716.json")
    if not os.path.exists(bpath):
        allp=list(db.plants.find({"stories":{"$exists":True}}, {"_id":1,"stories":1}))
        json.dump(allp, io.open(bpath,"w",encoding="utf-8"), ensure_ascii=False, default=str)
        print(f"[백업] {len(allp)}종 → {bpath}")

    # pid별 묶기
    bypid={}
    for key,after in conv.items():
        pid,idx=key.split("#"); bypid.setdefault(pid,{})[int(idx)]=after
    n_doc=n_sent=0
    for pid,idxmap in bypid.items():
        doc=db.plants.find_one({"_id":pid},{"stories":1})
        if not doc: print(f"  [skip] {pid} 없음"); continue
        stories=doc["stories"]
        for idx,after in idxmap.items():
            if idx<len(stories): stories[idx]["content"]=after; n_sent+=1
        db.plants.update_one({"_id":pid},{"$set":{"stories":stories}}); n_doc+=1
    print(f"[DB] {n_doc}종 {n_sent}스토리 갱신")

    # v2.json 동기화
    data=json.load(io.open(V2,encoding="utf-8"))
    bak=V2+".pre_polite_20260716.bak"
    if not os.path.exists(bak):
        json.dump(data, io.open(bak,"w",encoding="utf-8"), ensure_ascii=False)
        print(f"[v2] 백업 → {bak}")
    dmap={str(p["_id"]):p for p in data}
    n2=0
    for pid,idxmap in bypid.items():
        dp=dmap.get(str(pid))
        if dp and dp.get("stories"):
            for idx,after in idxmap.items():
                if idx<len(dp["stories"]): dp["stories"][idx]["content"]=after; n2+=1
    json.dump(data, io.open(V2,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[v2] {n2}스토리 동기화")
    c.close(); print("\n=== 완료 ===")

if __name__=="__main__":
    main()
