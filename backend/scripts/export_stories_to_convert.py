# -*- coding: utf-8 -*-
"""변환 대상(평서 종결 포함) 스토리를 작업용 JSON으로 export."""
import sys, os, io, json, re
sys.path.insert(0, ".")
import certifi
from pymongo import MongoClient
from app.core.config import settings

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
# 문장 경계는 마침표/느낌표/물음표 기준(문장 중간의 '내려오다 …' 연결어미 오탐 방지)
SENT_SPLIT = re.compile(r"[.!?]+")

def plain_endings(text):
    out=[]
    for s in SENT_SPLIT.split(text):
        s2=s.strip().strip('"\'”’‘“()（）~ ')
        if not s2: continue
        if s2.endswith("다") and not s2.endswith("니다"):
            out.append(s2)
    return out

c = MongoClient(settings.MONGO_URI, tlsCAFile=certifi.where())
db = c[settings.MONGODB_DB_NAME]
rows=[]
for p in db.plants.find({"stories":{"$exists":True}}, {"_id":1,"name":1,"stories":1}):
    for idx, st in enumerate(p.get("stories",[])):
        body=st.get("content","")
        if plain_endings(body):
            rows.append({"key": f"{p['_id']}#{idx}", "pid": p["_id"], "idx": idx,
                         "name": p["name"], "genre": st.get("genre"), "before": body})
c.close()
out=os.path.join(DATA,"stories_to_convert.json")
json.dump(rows, io.open(out,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"export: {len(rows)}건 -> {out}")
