# -*- coding: utf-8 -*-
"""
스토리 문체를 '습니다체(경어)'로 통일 (2026-07-16).

배경: 원전 사전 콘텐츠=이다체, AI 생성분=습니다체 → 혼재. 사용자 결정=습니다체 통일.
'변환 대상' = 정중 종결(~니다)이 아닌 평서 종결(~다, ~이다, ~한다 등)이 하나라도 있는 스토리.

  py scripts/rewrite_stories_polite.py --count            # 대상 규모만
  py scripts/rewrite_stories_polite.py --pilot 12         # 파일럿(변환 미리보기, 저장X)
  py scripts/rewrite_stories_polite.py --commit [--limit N]# 실제 반영(백업 후)
"""
import sys, os, io, json, re, argparse, time
sys.path.insert(0, ".")
import certifi
from pymongo import MongoClient
from google import genai
from app.core.config import settings

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
V2 = os.path.join(DATA, "floripedia_v2.json")

# 문장 경계는 마침표/느낌표/물음표 기준(문장 중간의 '내려오다 …' 연결어미 오탐 방지)
SENT_SPLIT = re.compile(r"[.!?]+")

def plain_endings(text):
    """평서(비정중) 종결 문장 목록 반환."""
    out=[]
    for s in SENT_SPLIT.split(text):
        s2=s.strip().strip('"\'”’‘“()（）~ ')
        if not s2: continue
        # '...다'로 끝나되 '...니다'(습니다/입니다/ㅂ니다)가 아니면 평서체
        if s2.endswith("다") and not s2.endswith("니다"):
            out.append(s2[-14:])
    return out

def needs_conversion(text):
    return len(plain_endings(text)) > 0

PROMPT = (
    "다음은 식물 앱에 실리는 짧은 이야기입니다. 의미·정보·사실·분량·어조를 그대로 유지한 채, "
    "문장 종결어미만 정중한 '~습니다체'로 자연스럽게 바꿔 주세요.\n"
    "규칙:\n"
    "- 새로운 사실을 추가하거나 기존 내용을 삭제하지 마세요.\n"
    "- 고유명사, 학명, 인용된 시/작품명, 수치, 괄호 표기는 원문 그대로 두세요.\n"
    "- '~이다/~한다/~된다/~였다' 같은 평서 종결을 '~입니다/~합니다/~됩니다/~였습니다' 등으로만 바꾸세요.\n"
    "- 이미 정중체인 문장은 그대로 두세요.\n"
    "- 결과는 변환된 본문만 출력하세요(따옴표·머리말·설명 없이).\n\n"
    "원문:\n{body}"
)

def get_client(): return genai.Client(api_key=settings.GEMINI_API_KEY)

def rewrite(client, model, body, retries=3):
    last=None
    for _ in range(retries):
        try:
            r = client.models.generate_content(model=model, contents=[PROMPT.format(body=body)])
            t = (r.text or "").strip().strip('"').strip()
            if t: return t
        except Exception as e:
            last=e; time.sleep(2)
    print(f"   [WARN] rewrite 실패: {last}")
    return None

def iter_stories(db):
    for p in db.plants.find({"stories": {"$exists": True}}, {"_id":1,"name":1,"stories":1}):
        for idx, st in enumerate(p.get("stories", [])):
            yield p, idx, st

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", action="store_true")
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--model", default=settings.GEMINI_ESSAY_MODEL)
    args = ap.parse_args()

    c = MongoClient(settings.MONGO_URI, tlsCAFile=certifi.where())
    db = c[settings.MONGODB_DB_NAME]

    if args.count:
        total=need=0
        from collections import Counter
        by_g=Counter()
        for p, idx, st in iter_stories(db):
            total+=1
            if needs_conversion(st.get("content","")):
                need+=1; by_g[st.get("genre")]+=1
        print(f"전체 스토리: {total}, 변환 대상(평서 종결 포함): {need}")
        print(f"장르별 대상: {dict(by_g)}")
        c.close(); return

    if args.pilot:
        client=get_client()
        picked=[]; seen_g={}
        for p, idx, st in iter_stories(db):
            body=st.get("content","")
            if not needs_conversion(body): continue
            g=st.get("genre")
            if 60<len(body)<260 and seen_g.get(g,0)<3:
                seen_g[g]=seen_g.get(g,0)+1
                picked.append((p,idx,st,body))
            if len(picked)>=args.pilot: break
        print(f"=== 파일럿 {len(picked)}건 (model={args.model}) ===\n")
        for p,idx,st,body in picked:
            new=rewrite(client,args.model,body)
            print(f"■ {p['_id']} {p['name']} [{st.get('genre')}]")
            print(f"  BEFORE: {body}")
            print(f"  AFTER : {new}")
            print(f"  남은 평서종결: {plain_endings(new) if new else 'N/A'}\n")
        c.close(); return

    if args.commit:
        client=get_client()
        # 백업
        allp=list(db.plants.find({"stories":{"$exists":True}}, {"_id":1,"stories":1}))
        bpath=os.path.join(DATA,"stories_backup_pre_polite_20260716.json")
        if not os.path.exists(bpath):
            json.dump(allp, io.open(bpath,"w",encoding="utf-8"), ensure_ascii=False, default=str)
            print(f"[백업] {len(allp)}종 stories → {bpath}")
        # 대상 수집
        work=[(p,idx,st,st.get("content","")) for p,idx,st in iter_stories(db) if needs_conversion(st.get("content",""))]
        if args.limit: work=work[:args.limit]
        print(f"[반영] 대상 {len(work)}건 변환 시작...")
        # plant별 stories 갱신 집계
        updates={}  # pid -> {idx: newcontent}
        done=fail=0
        for i,(p,idx,st,body) in enumerate(work):
            new=rewrite(client,args.model,body)
            if new and not plain_endings(new):
                updates.setdefault(p["_id"],{})[idx]=new; done+=1
            elif new:
                # 부분 변환이라도 반영(평서 잔존 경고)
                updates.setdefault(p["_id"],{})[idx]=new; done+=1
            else:
                fail+=1
            if (i+1)%25==0: print(f"  {i+1}/{len(work)} (성공 {done}, 실패 {fail})")
        # DB 반영
        for pid, idxmap in updates.items():
            doc=db.plants.find_one({"_id":pid},{"stories":1})
            stories=doc["stories"]
            for idx,new in idxmap.items():
                stories[idx]["content"]=new
            db.plants.update_one({"_id":pid},{"$set":{"stories":stories}})
        print(f"[DB] {len(updates)}종 갱신 (문장 {done}건 변환, 실패 {fail})")
        # v2.json 동기화
        if os.path.exists(V2):
            data=json.load(io.open(V2,encoding="utf-8"))
            bak=V2+".pre_polite_20260716.bak"
            if not os.path.exists(bak):
                json.dump(data, io.open(bak,"w",encoding="utf-8"), ensure_ascii=False)
            dmap={str(p["_id"]):p for p in data}
            for pid, idxmap in updates.items():
                dp=dmap.get(str(pid))
                if dp and dp.get("stories"):
                    for idx,new in idxmap.items():
                        if idx < len(dp["stories"]): dp["stories"][idx]["content"]=new
            json.dump(data, io.open(V2,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"[v2] 동기화 완료")
        c.close(); print("\n=== 완료 ===")
        return

    print("옵션 필요: --count | --pilot N | --commit")
    c.close()

if __name__ == "__main__":
    main()
