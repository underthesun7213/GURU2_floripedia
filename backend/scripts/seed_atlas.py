# -*- coding: utf-8 -*-
"""
backend/data/floripedia_v2.json 을 MongoDB Atlas 의 plants 컬렉션에 시딩.

앱(backend/app) 기대 스키마:
  - 연결 env: MONGO_URI  (DB: MONGODB_DB_NAME, 기본 'floripedia')
  - 컬렉션: 'plants'
  - 문서 _id: 문자열(str) 그대로 (repository.get_by_id 가 {"_id": str} 로 조회)

모드 (기본은 무조건 dry-run — Atlas 를 건드리지 않음):
  (플래그 없음)   오프라인 dry-run: json 파싱·문서수·_id중복·필수필드 커버리지만 출력
  --execute       실제 Atlas 연결 후 쓰기 (아래 동작과 조합)
    --drop        drop 후 전량 적재. drop 전에 현재 컬렉션을 _backups/ 로 export
    (--drop 없음) _id 기준 upsert

  주의: --execute 가 없으면 어떤 경우에도 Atlas 에 연결/쓰기하지 않는다.

사용 예:
  python backend/scripts/seed_atlas.py                      # 오프라인 dry-run
  python backend/scripts/seed_atlas.py --execute            # upsert (실제 쓰기)
  python backend/scripts/seed_atlas.py --execute --drop     # 백업 후 drop+적재
"""
import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_HERE = Path(__file__).resolve()
_BACKEND = _HERE.parents[1]                 # backend/
_REPO_ROOT = _HERE.parents[2]               # repo root
DEFAULT_DATA = _BACKEND / "data" / "floripedia_v2.json"
BACKUP_DIR = _BACKEND / "data" / "_backups"

# MONGO_URI 등 읽기 전에 backend/.env 로드 (repo 다른 스크립트와 동일 패턴)
load_dotenv(os.path.join(_BACKEND, ".env"))

# 앱이 실제로 읽는 필수 필드 (app/schemas/plant.py 의 Plant: 기본값 없는 필드 +
# repository 쿼리에서 참조하는 중첩 경로). management/preContent/images/imageUrl/
# isRepresentative/popularity_score 는 Optional 또는 기본값 있어 필수에서 제외.
REQUIRED_TOP = [
    "_id", "name", "scientificName", "taxonomy", "horticulture", "habitat",
    "flowerInfo", "stories", "season", "bloomingMonths", "searchKeywords",
    "colorInfo", "scentInfo",
]
REQUIRED_NESTED = {
    "taxonomy": ["genus", "species", "family"],
    "horticulture": ["category", "categoryGroup", "usage"],
    "flowerInfo": ["language", "flowerGroup"],
    "colorInfo": ["hexCodes", "colorLabels", "colorGroup"],
    "scentInfo": ["scentTags", "scentGroup"],
}


def load_docs(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise SystemExit(f"ERROR: {path} 최상위가 list 가 아님")
    return data


def missing_required(doc):
    """문서에서 누락(키 없음 또는 빈 값)인 앱 필수 필드 경로 리스트."""
    miss = []
    for k in REQUIRED_TOP:
        v = doc.get(k, None)
        if v is None or v == "" or v == [] or v == {}:
            miss.append(k)
    for parent, children in REQUIRED_NESTED.items():
        pv = doc.get(parent)
        if not isinstance(pv, dict):
            continue  # 부모 누락은 위에서 이미 잡힘
        for c in children:
            cv = pv.get(c, None)
            if cv is None or cv == "" or cv == [] or cv == {}:
                miss.append(f"{parent}.{c}")
    # stories 내부 genre/content
    stories = doc.get("stories")
    if isinstance(stories, list):
        for i, s in enumerate(stories):
            if not s.get("genre"):
                miss.append(f"stories[{i}].genre")
            if not s.get("content"):
                miss.append(f"stories[{i}].content")
    return miss


def offline_report(docs):
    import collections
    n = len(docs)
    print(f"[dry-run] 문서 수: {n}")

    # _id 타입 / 중복
    types = collections.Counter(type(d.get("_id")).__name__ for d in docs)
    print(f"[dry-run] _id 타입 분포: {dict(types)}")
    ids = [d.get("_id") for d in docs]
    dups = [k for k, c in collections.Counter(ids).items() if c > 1]
    print(f"[dry-run] _id 중복 개수: {len(dups)}" + (f" -> {dups[:10]}" if dups else ""))
    print(f"[dry-run] _id 샘플(앞5): {ids[:5]}")
    print(f"[dry-run] _id 샘플(뒤5): {ids[-5:]}")

    # 필수 필드 커버리지
    field_missing = collections.Counter()
    docs_with_missing = 0
    examples = []
    for d in docs:
        miss = missing_required(d)
        if miss:
            docs_with_missing += 1
            if len(examples) < 10:
                examples.append((d.get("_id"), miss))
            for m in miss:
                # stories[i] 는 인덱스 떼고 집계
                key = m.split("[")[0] + ("[]" if "[" in m else "")
                field_missing[key] += 1
    print(f"[dry-run] 앱 필수 필드 누락 종 수: {docs_with_missing} / {n}")
    if field_missing:
        print("[dry-run] 누락 필드별 종 수:")
        for k, c in sorted(field_missing.items(), key=lambda x: -x[1]):
            print(f"    {k}: {c}")
        print("[dry-run] 누락 샘플(최대10):")
        for pid, miss in examples:
            print(f"    _id={pid}: {miss}")
    else:
        print("[dry-run] 누락 없음 — 모든 종이 앱 필수 필드를 보유")

    return docs_with_missing, dups


def do_execute(docs, uri, db_name, coll_name, drop):
    if not uri:
        raise SystemExit("ERROR: MONGO_URI 가 비어 있음 (env 또는 --uri 필요)")
    try:
        from pymongo import MongoClient, ReplaceOne
    except ImportError:
        raise SystemExit("ERROR: pymongo 미설치 — `pip install pymongo` 후 재시도")

    client = MongoClient(uri, serverSelectionTimeoutMS=8000,
                         tlsAllowInvalidCertificates=True)  # app/db/session.py 와 동일 옵션
    client.admin.command("ping")
    coll = client[db_name][coll_name]
    print(f"[execute] connected: db='{db_name}' collection='{coll_name}'")

    if drop:
        existing = coll.count_documents({})
        if existing:
            import datetime
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            bpath = BACKUP_DIR / f"{coll_name}_{ts}.json"
            cur = list(coll.find({}))
            with open(bpath, "w", encoding="utf-8") as f:
                json.dump(cur, f, ensure_ascii=False, default=str)
            print(f"[execute] 기존 {existing}건 백업 -> {bpath}")
        coll.drop()
        print("[execute] 컬렉션 drop 완료, 전량 적재 시작")
        coll.insert_many(docs, ordered=False)
        print(f"[execute] insert_many 완료: {len(docs)}건")
    else:
        ops = [ReplaceOne({"_id": d["_id"]}, d, upsert=True) for d in docs]
        res = coll.bulk_write(ops, ordered=False)
        print(f"[execute] upsert 완료: matched={res.matched_count} "
              f"upserted={len(res.upserted_ids)} modified={res.modified_count}")

    client.close()


def main():
    ap = argparse.ArgumentParser(description="floripedia_v2.json -> MongoDB Atlas seeding")
    ap.add_argument("--data", default=str(DEFAULT_DATA), help="시드 json 경로")
    ap.add_argument("--uri", default=os.getenv("MONGO_URI", ""), help="MongoDB 연결 URI (기본 env MONGO_URI)")
    ap.add_argument("--db", default=os.getenv("MONGODB_DB_NAME", "floripedia"), help="DB 이름")
    ap.add_argument("--collection", default="plants", help="컬렉션 이름")
    ap.add_argument("--execute", action="store_true", help="실제 Atlas 연결/쓰기 (없으면 dry-run)")
    ap.add_argument("--drop", action="store_true", help="(--execute 시) drop 후 전량 적재 (drop 전 백업)")
    args = ap.parse_args()

    docs = load_docs(args.data)
    print(f"데이터: {args.data}")

    missing_cnt, dups = offline_report(docs)

    if not args.execute:
        print("\n=== DRY-RUN 종료 (Atlas 미연결). 실제 적재는 --execute 필요. ===")
        return

    # 안전장치: _id 중복 있으면 실제 쓰기 중단
    if dups:
        raise SystemExit(f"ERROR: _id 중복 {len(dups)}건 — 실제 쓰기 중단")
    print(f"\n=== EXECUTE 모드 (drop={args.drop}) ===")
    do_execute(docs, args.uri, args.db, args.collection, args.drop)


if __name__ == "__main__":
    main()
