"""
캐시 통합 테스트: 서비스 계층 캐시 동작 + HTTP 캐시 헤더/ETag + 관리자 무효화.
"""
import pytest

from app.core.config import settings


# ---------------- 서비스: 상세 조회 캐시 (D2-A) ----------------
@pytest.mark.asyncio
async def test_detail_is_cached(plant_service, mock_db_full):
    """상세 조회 후 DB를 바꿔도, TTL 내 재조회는 캐시된 값을 반환한다."""
    first = await plant_service.get_plant_detail("1")
    assert first is not None
    original_name = first["name"]

    # DB의 이름을 직접 변경 (캐시가 없다면 반영될 것)
    await mock_db_full["plants"].update_one({"_id": "1"}, {"$set": {"name": "변경된이름"}})

    second = await plant_service.get_plant_detail("1")
    assert second["name"] == original_name   # 캐시 히트 → 옛 값 유지


@pytest.mark.asyncio
async def test_detail_negative_cache(plant_service, mock_db_full):
    """존재하지 않는 id는 None을 캐시 → 이후 생성돼도 TTL 내엔 None."""
    assert await plant_service.get_plant_detail("999999") is None

    await mock_db_full["plants"].insert_one({"_id": "999999", "name": "새식물"})

    # negative 캐시(None)가 살아있어 여전히 None
    assert await plant_service.get_plant_detail("999999") is None


@pytest.mark.asyncio
async def test_detail_is_favorite_not_leaked_across_users(plant_service, mock_db_full):
    """캐시된 문서를 복사해 is_favorite를 주입 → 유저별로 오염되지 않는다."""
    # user1이 식물 "1"을 찜한 상태로 세팅
    await mock_db_full["users"].update_one(
        {"_id": "user1"}, {"$set": {"favoritePlantIds": ["1"]}}, upsert=True
    )
    as_user1 = await plant_service.get_plant_detail("1", user_id="user1")
    as_anon = await plant_service.get_plant_detail("1", user_id=None)

    assert as_user1["is_favorite"] is True
    assert as_anon["is_favorite"] is False   # 캐시 공유 객체가 오염되지 않음


# ---------------- API: HTTP 캐시 헤더 + ETag/304 ----------------
@pytest.mark.asyncio
async def test_detail_endpoint_cache_headers(client):
    r = await client.get("/api/v1/plants/1")
    assert r.status_code == 200
    assert r.headers["cache-control"] == f"public, max-age={settings.CACHE_TTL}"
    assert "etag" in r.headers
    assert "Authorization" in r.headers.get("vary", "")


@pytest.mark.asyncio
async def test_etag_returns_304(client):
    r1 = await client.get("/api/v1/plants/1")
    etag = r1.headers["etag"]

    r2 = await client.get("/api/v1/plants/1", headers={"If-None-Match": etag})
    assert r2.status_code == 304


@pytest.mark.asyncio
async def test_favorites_endpoint_not_publicly_cached(client):
    """per-user 목록(/plants/favorites)엔 public 캐시 헤더가 붙지 않는다."""
    r = await client.get("/api/v1/plants/favorites")
    # 미들웨어 제외 대상 → public max-age 헤더 없음
    assert "public" not in r.headers.get("cache-control", "")


# ---------------- 관리자 무효화 ----------------
@pytest.mark.asyncio
async def test_invalidate_requires_token(client, monkeypatch):
    monkeypatch.setattr(settings, "CACHE_INVALIDATE_TOKEN", "s3cret")
    # 토큰 없음 → 401
    r = await client.post("/api/v1/admin/cache/invalidate")
    assert r.status_code == 401
    # 틀린 토큰 → 401
    r = await client.post("/api/v1/admin/cache/invalidate",
                          headers={"X-Admin-Token": "wrong"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_invalidate_clears_cache(client, monkeypatch):
    monkeypatch.setattr(settings, "CACHE_INVALIDATE_TOKEN", "s3cret")
    # 캐시를 채운다
    await client.get("/api/v1/plants/1")
    # prefix 무효화
    r = await client.post("/api/v1/admin/cache/invalidate",
                          headers={"X-Admin-Token": "s3cret"},
                          json={"prefix": "species"})
    assert r.status_code == 200
    assert r.json()["removed"] >= 1


@pytest.mark.asyncio
async def test_invalidate_disabled_when_no_token(client):
    """토큰 미설정(기본 빈값)이면 무효화 엔드포인트는 열리지 않는다(401)."""
    # 기본 CACHE_INVALIDATE_TOKEN="" 상태
    r = await client.post("/api/v1/admin/cache/invalidate",
                          headers={"X-Admin-Token": ""})
    assert r.status_code == 401
