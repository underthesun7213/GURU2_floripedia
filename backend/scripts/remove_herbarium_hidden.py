# -*- coding: utf-8 -*-
"""
is_hidden 죽은 플래그 정리 (2026-07-16).

배경: _id>1500 자동 이미지 복구 46종에 붙은 'is_hidden'(검토 대기) 플래그가
어떤 코드에도 연결되지 않아 죽어 있었고, 그 중 상당수가 표본관 압착표본 사진이었다.
실물 검증 결과: 표본지 28종 / 실물사진 18종.

이 스크립트:
  1) 표본지 28종을 활성 카탈로그에서 제거 (백업 → DB delete → v2.json 제거 → 유저 참조 $pull)
  2) is_hidden 필드를 남은 전 문서에서 제거 (DB + v2.json) — 죽은 플래그 완전 삭제

DRY-RUN 기본. 실제 반영은 --commit.
사용법:  py scripts/remove_herbarium_hidden.py [--commit]
"""
import sys, os, io, json, argparse, datetime
sys.path.insert(0, ".")
import certifi
from pymongo import MongoClient
from app.core.config import settings

HERBARIUM = ["1510","1529","1536","1565","1579","1602","1606","1614","1619","1660",
             "1676","1689","1702","1715","1723","1727","1743","1744","1745","1764",
             "1773","1844","1861","1892","1977","1987","2028","2075"]
LIVE = ["1650","1656","1659","1735","1746","1802","1853","1929","1930","1931",
        "1940","1973","2001","2027","2068","2076","2080","2112"]

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
V2 = os.path.join(DATA, "floripedia_v2.json")
STAMP = "20260716"

def log(*a): print(*a, flush=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()
    dry = not args.commit
    mode = "DRY-RUN" if dry else "COMMIT"
    log(f"=== is_hidden 정리 ({mode}) ===")
    log(f"제거(표본지): {len(HERBARIUM)}종, 유지(실물): {len(LIVE)}종")

    c = MongoClient(settings.MONGO_URI, tlsCAFile=certifi.where())
    db = c[settings.MONGODB_DB_NAME]

    total0 = db.plants.count_documents({})
    hidden0 = db.plants.count_documents({"is_hidden": True})
    log(f"[현재] plants={total0}, is_hidden=true {hidden0}")

    present = list(db.plants.find({"_id": {"$in": HERBARIUM}}, {"_id":1,"name":1}))
    log(f"[확인] 제거대상 DB 존재: {len(present)}/{len(HERBARIUM)}")
    missing = set(HERBARIUM) - {p["_id"] for p in present}
    if missing:
        log(f"  ⚠️ DB에 없는 id: {sorted(missing)}")

    live_present = db.plants.count_documents({"_id": {"$in": LIVE}, "is_hidden": True})
    log(f"[확인] 유지대상 중 is_hidden=true: {live_present}/{len(LIVE)}")

    if dry:
        log(f"[예상] 삭제 후 plants={total0-len(present)}, is_hidden 필드 제거 후 남는 문서의 필드=0")
        # orphan preview
        uref = 0
        for u in db.users.find({}, {"favoritePlantIds":1,"viewedPlantIds":1,"discoveredPlantIds":1}):
            for f in ("favoritePlantIds","viewedPlantIds","discoveredPlantIds"):
                uref += len(set(u.get(f,[])) & set(HERBARIUM))
        log(f"[예상] 유저 참조에서 $pull 될 항목 수: {uref}")
        log("\nDRY-RUN — 변경 없음. --commit 으로 실제 반영.")
        c.close(); return

    # ── 백업 ──
    full_docs = list(db.plants.find({"_id": {"$in": HERBARIUM}}))
    bpath = os.path.join(DATA, f"plants_herbarium_removed_backup_{STAMP}.json")
    with io.open(bpath, "w", encoding="utf-8") as f:
        json.dump(full_docs, f, ensure_ascii=False, indent=2, default=str)
    log(f"[백업] 제거 문서 {len(full_docs)}종 → {bpath}")

    users = list(db.users.find({}))
    upath = os.path.join(DATA, f"users_backup_{STAMP}.json")
    with io.open(upath, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2, default=str)
    log(f"[백업] users {len(users)}명 → {upath}")

    # ── DB: 삭제 ──
    r = db.plants.delete_many({"_id": {"$in": HERBARIUM}})
    log(f"[DB] plants 삭제: {r.deleted_count}")

    # ── DB: 유저 참조 정리 ──
    ur = db.users.update_many({}, {"$pull": {
        "favoritePlantIds": {"$in": HERBARIUM},
        "viewedPlantIds": {"$in": HERBARIUM},
        "discoveredPlantIds": {"$in": HERBARIUM},
    }})
    log(f"[DB] 유저 참조 $pull: matched={ur.matched_count} modified={ur.modified_count}")

    # ── DB: is_hidden 필드 전면 제거 ──
    fr = db.plants.update_many({"is_hidden": {"$exists": True}}, {"$unset": {"is_hidden": ""}})
    log(f"[DB] is_hidden 필드 제거: modified={fr.modified_count}")

    total1 = db.plants.count_documents({})
    hidden1 = db.plants.count_documents({"is_hidden": {"$exists": True}})
    log(f"[DB 검증] plants={total1}, is_hidden 필드 보유={hidden1}")

    # ── floripedia_v2.json 동기화 ──
    if os.path.exists(V2):
        with io.open(V2, encoding="utf-8") as f:
            data = json.load(f)
        # .bak (한 번만)
        bak = V2 + f".pre_herbarium_{STAMP}.bak"
        if not os.path.exists(bak):
            with io.open(bak, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            log(f"[v2] 백업 → {bak}")
        hset = set(HERBARIUM)
        kept = []
        for p in data:
            if str(p.get("_id")) in hset:
                continue
            p.pop("is_hidden", None)
            kept.append(p)
        with io.open(V2, "w", encoding="utf-8") as f:
            json.dump(kept, f, ensure_ascii=False, indent=2)
        log(f"[v2] {len(data)} → {len(kept)}종 (is_hidden 필드 제거 완료)")
    else:
        log(f"[v2] 파일 없음: {V2}")

    c.close()
    log("\n=== 완료 ===")

if __name__ == "__main__":
    main()
