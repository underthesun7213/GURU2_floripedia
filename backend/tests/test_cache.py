"""
캐시 계층 단위 테스트.
- 히트/미스, TTL 만료, stampede(동시 N요청 → loader 1회), negative caching,
  무효화(delete/prefix/clear), CACHE_ENABLED=false 우회, 키 규약, 락 정리.
"""
import asyncio

import pytest

from app.cache import InMemoryCache, MISS, make_key, make_list_key
from app.core.config import settings


@pytest.fixture
def cache():
    return InMemoryCache(maxsize=100, default_ttl=10.0, negative_ttl=0.5)


# ---------------- 히트 / 미스 ----------------
@pytest.mark.asyncio
async def test_get_missing_returns_miss(cache):
    assert await cache.get("nope") is MISS


@pytest.mark.asyncio
async def test_set_then_get_hit(cache):
    await cache.set("k", {"v": 1})
    assert await cache.get("k") == {"v": 1}


@pytest.mark.asyncio
async def test_cached_none_is_distinct_from_miss(cache):
    """negative 캐시: 저장된 None과 '캐시 미스'(MISS)를 구분해야 한다."""
    await cache.set("k", None)
    got = await cache.get("k")
    assert got is None
    assert got is not MISS


# ---------------- TTL 만료 ----------------
@pytest.mark.asyncio
async def test_ttl_expiry(cache):
    await cache.set("k", "v", ttl=0.1)
    assert await cache.get("k") == "v"
    await asyncio.sleep(0.15)
    assert await cache.get("k") is MISS


# ---------------- Stampede ----------------
@pytest.mark.asyncio
async def test_stampede_loader_called_once(cache):
    calls = {"n": 0}

    async def loader():
        calls["n"] += 1
        await asyncio.sleep(0.05)   # 로드가 느린 동안 동시 요청 유입
        return "value"

    results = await asyncio.gather(*[
        cache.get_or_load("key", loader) for _ in range(20)
    ])

    assert results == ["value"] * 20
    assert calls["n"] == 1          # 20개 동시 요청이 loader를 딱 1번만 호출


@pytest.mark.asyncio
async def test_locks_cleaned_up_after_load(cache):
    async def loader():
        return 1
    await cache.get_or_load("k", loader)
    # in-flight 키만 유지되어야 함 → 완료 후 락 dict 비어야 함
    assert cache._locks == {}
    assert cache._lock_users == {}


# ---------------- Negative caching ----------------
@pytest.mark.asyncio
async def test_negative_caching_blocks_reload(cache):
    calls = {"n": 0}

    async def loader():
        calls["n"] += 1
        return None                 # 존재하지 않는 리소스

    r1 = await cache.get_or_load("missing", loader)
    r2 = await cache.get_or_load("missing", loader)
    assert r1 is None and r2 is None
    assert calls["n"] == 1          # None도 캐시되어 재조회 시 loader 미호출


@pytest.mark.asyncio
async def test_negative_ttl_expires(cache):
    calls = {"n": 0}

    async def loader():
        calls["n"] += 1
        return None

    await cache.get_or_load("missing", loader)
    await asyncio.sleep(0.6)        # negative_ttl=0.5 경과
    await cache.get_or_load("missing", loader)
    assert calls["n"] == 2          # 만료 후 재조회


# ---------------- 무효화 ----------------
@pytest.mark.asyncio
async def test_delete_and_prefix_and_clear(cache):
    await cache.set("species:1:v1", "a")
    await cache.set("species:2:v1", "b")
    await cache.set("stories:x:v1", "c")

    await cache.delete("species:1:v1")
    assert await cache.get("species:1:v1") is MISS

    removed = await cache.delete_prefix("species:")
    assert removed == 1             # species:2 만 남아있었음
    assert await cache.get("species:2:v1") is MISS
    assert await cache.get("stories:x:v1") == "c"

    n = await cache.clear()
    assert n == 1
    assert await cache.get("stories:x:v1") is MISS


# ---------------- CACHE_ENABLED=false 우회 ----------------
@pytest.mark.asyncio
async def test_disabled_bypasses_cache(cache, monkeypatch):
    monkeypatch.setattr(settings, "CACHE_ENABLED", False)
    calls = {"n": 0}

    async def loader():
        calls["n"] += 1
        return "v"

    await cache.get_or_load("k", loader)
    await cache.get_or_load("k", loader)
    assert calls["n"] == 2          # 캐시 우회 → 매번 loader 호출
    assert await cache.get("k") is MISS   # 저장도 안 됨


# ---------------- 로더 예외는 전파 (DB 오류) ----------------
@pytest.mark.asyncio
async def test_loader_error_propagates(cache):
    async def loader():
        raise RuntimeError("db down")
    with pytest.raises(RuntimeError):
        await cache.get_or_load("k", loader)


# ---------------- 키 규약 ----------------
def test_make_key():
    assert make_key("species", "12345") == f"species:12345:v{settings.CACHE_SCHEMA_VERSION}"


def test_make_list_key_sorted_and_none_dropped():
    k1 = make_list_key("species", {"size": 20, "page": 2, "season": None})
    k2 = make_list_key("species", {"page": 2, "size": 20})   # 순서 다르고 None 제외
    assert k1 == k2
    assert k1 == f"species:list:page=2&size=20:v{settings.CACHE_SCHEMA_VERSION}"
