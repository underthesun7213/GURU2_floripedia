"""
uid별 일일 rate limit 로직 테스트 (app.core.rate_limit).
"""
import pytest

from app.core.rate_limit import check_and_increment, create_rate_limit_index, COLLECTION


@pytest.mark.asyncio
async def test_under_limit_allows(mock_db):
    """상한 이내면 매 호출 True를 반환한다."""
    limit = 3
    for _ in range(limit):
        assert await check_and_increment(mock_db, "uid-a", limit) is True


@pytest.mark.asyncio
async def test_over_limit_rejects(mock_db):
    """상한을 넘는 호출은 False를 반환한다."""
    limit = 3
    for _ in range(limit):
        assert await check_and_increment(mock_db, "uid-b", limit) is True
    # limit+1번째 호출은 거부
    assert await check_and_increment(mock_db, "uid-b", limit) is False


@pytest.mark.asyncio
async def test_counter_is_per_uid(mock_db):
    """카운터는 uid별로 독립적이다."""
    limit = 1
    assert await check_and_increment(mock_db, "uid-x", limit) is True
    # 다른 uid는 영향받지 않음
    assert await check_and_increment(mock_db, "uid-y", limit) is True
    # 같은 uid는 초과
    assert await check_and_increment(mock_db, "uid-x", limit) is False


@pytest.mark.asyncio
async def test_setoninsert_expireat_present(mock_db):
    """최초 생성 시 TTL용 expireAt 필드가 세팅된다."""
    await check_and_increment(mock_db, "uid-ttl", 10)
    doc = await mock_db[COLLECTION].find_one({"count": {"$exists": True}})
    assert doc is not None
    assert doc.get("expireAt") is not None


@pytest.mark.asyncio
async def test_db_error_fails_open(monkeypatch):
    """DB 오류 시 fail-open(True)으로 정상 사용자를 막지 않는다."""
    class BrokenCollection:
        async def find_one_and_update(self, *a, **k):
            raise RuntimeError("db down")

    class BrokenDB:
        def __getitem__(self, _name):
            return BrokenCollection()

    assert await check_and_increment(BrokenDB(), "uid-err", 60) is True


@pytest.mark.asyncio
async def test_create_index_idempotent(mock_db):
    """인덱스 생성은 에러 없이 (반복 호출 포함) 동작한다."""
    await create_rate_limit_index(mock_db)
    await create_rate_limit_index(mock_db)
