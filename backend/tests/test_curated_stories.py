"""
인기 스토리 큐레이션 + $rand 제거(결정적 정렬) 테스트.
"""
import pytest

from app.core.config import settings


@pytest.mark.asyncio
async def test_get_list_popularity_deterministic(plant_repo):
    """popularity_score 정렬이 매 호출 동일해야 한다($rand 제거 → 캐시/재현 정합)."""
    a = await plant_repo.get_list(sort_by="popularity_score", sort_order=-1, limit=10)
    b = await plant_repo.get_list(sort_by="popularity_score", sort_order=-1, limit=10)
    assert [x["_id"] for x in a] == [x["_id"] for x in b]


@pytest.mark.asyncio
async def test_curated_stories_served_in_order(plant_service, mock_db_full):
    """큐레이션이 있으면 지정 순서대로 스토리를 반환한다."""
    await mock_db_full["plants"].insert_many([
        {"_id": "c1", "name": "식물A", "imageUrl": "http://x/a.jpg", "popularity_score": 0,
         "stories": [{"genre": "EPISODE", "content": "A 이야기"}]},
        {"_id": "c2", "name": "식물B", "imageUrl": "http://x/b.jpg", "popularity_score": 0,
         "stories": [{"genre": "MYTH", "content": "B 신화"}]},
    ])
    await mock_db_full["config"].replace_one(
        {"_id": "curated_popular_stories"},
        {"_id": "curated_popular_stories",
         "items": [{"plantId": "c2", "genre": "MYTH"}, {"plantId": "c1", "genre": "EPISODE"}]},
        upsert=True,
    )

    res = await plant_service.get_popular_stories(skip=0, limit=10)
    assert [r["plantId"] for r in res[:2]] == ["c2", "c1"]   # 지정 순서
    assert res[0]["genre"] == "MYTH"
    assert res[0]["content"] == "B 신화"


@pytest.mark.asyncio
async def test_curated_skips_missing_plant(plant_service, mock_db_full):
    """큐레이션에 삭제된 식물 id가 있어도 건너뛰고 정상 반환."""
    await mock_db_full["plants"].insert_one(
        {"_id": "c3", "name": "식물C", "imageUrl": "http://x/c.jpg", "popularity_score": 0,
         "stories": [{"genre": "ART", "content": "C 예술"}]}
    )
    await mock_db_full["config"].replace_one(
        {"_id": "curated_popular_stories"},
        {"_id": "curated_popular_stories",
         "items": [{"plantId": "gone", "genre": "MYTH"}, {"plantId": "c3", "genre": "ART"}]},
        upsert=True,
    )
    res = await plant_service.get_popular_stories(skip=0, limit=10)
    assert [r["plantId"] for r in res] == ["c3"]


# (폴백 알고리즘 aggregation은 $indexOfArray 등을 써 mongomock에서 실행 불가 →
#  실 MongoDB에서 검증. 여기선 큐레이션 경로/결정적 정렬/무효화만 단위 검증.)


# ---------------- 관리자 큐레이션 설정 API ----------------
@pytest.mark.asyncio
async def test_admin_set_curated(client, monkeypatch):
    monkeypatch.setattr(settings, "CACHE_INVALIDATE_TOKEN", "tok")
    # 토큰 없으면 401
    r = await client.post("/api/v1/admin/curated/stories", json=[{"plantId": "1", "genre": "MYTH"}])
    assert r.status_code == 401
    # 토큰 있으면 저장
    r = await client.post(
        "/api/v1/admin/curated/stories",
        headers={"X-Admin-Token": "tok"},
        json=[{"plantId": "1", "genre": "MYTH"}, {"plantId": "2", "genre": "EPISODE"}],
    )
    assert r.status_code == 200
    assert r.json()["count"] == 2
