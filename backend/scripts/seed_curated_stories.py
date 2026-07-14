"""
인기 스토리 큐레이션 초기 시드.

기준(품질+다양성):
- 이미지(imageUrl)와 스토리가 있는 식물만 후보
- categoryGroup 라운드로빈으로 다양성 확보, 각 그룹 내 popularity_score 높은 순
- 장르는 이야기성 강한 비-SCIENCE 우선(EPISODE>MYTH>HISTORY>ART>SCIENCE)
- 기본 24개

결과는 config 컬렉션의 단일 문서(_id=curated_popular_stories)에 순서 리스트로 저장.
이후 관리자 API(POST /admin/curated/stories)로 언제든 갈아끼울 수 있다.

사용: python backend/scripts/seed_curated_stories.py [개수]   (기본 24, --dry 로 미리보기)
"""
import os
import sys
from collections import defaultdict

GENRE_PREF = ["EPISODE", "MYTH", "HISTORY", "ART", "SCIENCE"]


def load_env():
    env = {}
    here = os.path.join(os.path.dirname(__file__), "..", ".env")
    for line in open(here, encoding="utf-8"):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k] = v
    return env


def pick_genre(stories):
    genres = {s.get("genre") for s in stories}
    for g in GENRE_PREF:
        if g in genres:
            return g
    return stories[0].get("genre") if stories else None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    target = int(args[0]) if args else 24

    env = load_env()
    from pymongo import MongoClient
    c = MongoClient(env["MONGO_URI"])
    db = c[env.get("MONGODB_DB_NAME", "floripedia")]
    col = db["plants"]

    # 후보: 이미지 + 스토리 보유
    by_cat = defaultdict(list)
    for d in col.find(
        {"imageUrl": {"$nin": [None, ""]}, "stories.0": {"$exists": True}},
        {"name": 1, "stories.genre": 1, "popularity_score": 1,
         "horticulture.categoryGroup": 1, "season": 1},
    ):
        cat = (d.get("horticulture") or {}).get("categoryGroup") or "기타"
        by_cat[cat].append(d)

    for cat in by_cat:
        by_cat[cat].sort(key=lambda d: -(d.get("popularity_score") or 0))

    # 카테고리 라운드로빈 + 계절 다양성 약하게 반영
    items = []
    seen = set()
    cats = list(by_cat.keys())
    idxs = {cat: 0 for cat in cats}
    seasons_used = defaultdict(int)
    while len(items) < target and any(idxs[c] < len(by_cat[c]) for c in cats):
        for cat in cats:
            if len(items) >= target:
                break
            lst = by_cat[cat]
            # 이 카테고리에서 아직 안 쓴 다음 후보
            while idxs[cat] < len(lst):
                d = lst[idxs[cat]]
                idxs[cat] += 1
                if d["_id"] in seen:
                    continue
                g = pick_genre(d.get("stories", []))
                if not g:
                    continue
                items.append({"plantId": d["_id"], "genre": g,
                              "_name": d.get("name"), "_cat": cat,
                              "_season": d.get("season")})
                seen.add(d["_id"])
                seasons_used[d.get("season")] += 1
                break

    print(f"큐레이션 {len(items)}개 (목표 {target}):")
    for i, it in enumerate(items, 1):
        print(f"  {i:2}. {it['plantId']:>5} {it['_name']}  [{it['genre']}] {it['_cat']}/{it['_season']}")

    clean = [{"plantId": it["plantId"], "genre": it["genre"]} for it in items]
    if dry:
        print("\n--dry: 저장 안 함")
        return
    db["config"].replace_one(
        {"_id": "curated_popular_stories"},
        {"_id": "curated_popular_stories", "items": clean},
        upsert=True,
    )
    print(f"\n저장 완료 → config.curated_popular_stories ({len(clean)}개)")
    c.close()


if __name__ == "__main__":
    main()
