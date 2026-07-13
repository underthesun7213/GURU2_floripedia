"""
캐시 추상화 계층.

- `CacheBackend` 프로토콜: 백엔드 교체용 인터페이스 (지금은 인메모리, 추후 Redis)
- `InMemoryCache`: cachetools.TTLCache 기반 구현 + 키별 stampede 락 + negative caching
- `make_key` / `make_list_key`: 키 규약 헬퍼

설계 원칙:
- 캐시 실패는 절대 요청 실패로 이어지지 않는다 → 예외는 로그만 남기고 로더(DB)로 폴백.
- "캐시 미스"(MISS)와 "캐시된 None"(negative)을 구분한다.
- Redis 도입 시 `RedisCache(CacheBackend)`만 추가하고 이 파일의 나머지는 그대로 둔다.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Optional, Protocol, runtime_checkable

from cachetools import TTLCache

from app.core.config import settings

logger = logging.getLogger(__name__)


# ==========================================================
# 센티넬: "캐시에 아무것도 없음"을 나타낸다.
# (캐시된 None = negative 캐시는 실제 None 값으로 저장하고,
#  get()의 기본값을 MISS로 두어 둘을 구분한다.)
# ==========================================================
class _Miss:
    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover
        return "<MISS>"


MISS: Any = _Miss()


# ==========================================================
# 백엔드 인터페이스
# ==========================================================
@runtime_checkable
class CacheBackend(Protocol):
    """캐시 백엔드 프로토콜. Redis 등으로 교체 시 이 시그니처를 구현한다."""

    async def get(self, key: str) -> Any:
        """키의 값을 반환. 없으면 MISS 반환(캐시된 None과 구분)."""
        ...

    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """값 저장(ttl 초). ttl None이면 기본 TTL."""
        ...

    async def delete(self, key: str) -> None:
        """단일 키 삭제."""
        ...

    async def delete_prefix(self, prefix: str) -> int:
        """prefix로 시작하는 모든 키 삭제. 삭제된 개수 반환."""
        ...


# ==========================================================
# 인메모리 구현
# ==========================================================
class _Entry:
    """값 + 만료 시각(단조시계) 래퍼. per-entry TTL 지원용."""
    __slots__ = ("value", "expire_at")

    def __init__(self, value: Any, expire_at: float):
        self.value = value
        self.expire_at = expire_at


class InMemoryCache:
    """
    cachetools.TTLCache 기반 프로세스 로컬 캐시.

    - maxsize LRU 축출 + per-entry TTL(negative는 짧은 TTL) 지원.
    - 키별 asyncio.Lock으로 cache stampede 방지(락 후 double-check).
    - 락 dict는 in-flight 키만 유지(refcount)해 무한 증식 방지.
    """

    def __init__(
        self,
        maxsize: int = 2048,
        default_ttl: float = 3600.0,
        negative_ttl: float = 60.0,
    ):
        self.default_ttl = float(default_ttl)
        self.negative_ttl = float(negative_ttl)
        # TTLCache ttl은 물리적 백스톱(기본 TTL). 실제 만료는 _Entry.expire_at으로 판단.
        self._store: TTLCache = TTLCache(maxsize=maxsize, ttl=self.default_ttl)
        self._locks: dict[str, asyncio.Lock] = {}
        self._lock_users: dict[str, int] = {}

    # -------- CacheBackend 구현 --------
    async def get(self, key: str) -> Any:
        entry = self._store.get(key, MISS)
        if entry is MISS:
            return MISS
        if time.monotonic() > entry.expire_at:
            # 논리적 만료 → 미스 취급 + 제거
            self._store.pop(key, None)
            return MISS
        return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        ttl = self.default_ttl if ttl is None else float(ttl)
        self._store[key] = _Entry(value, time.monotonic() + ttl)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def delete_prefix(self, prefix: str) -> int:
        keys = [k for k in list(self._store.keys()) if k.startswith(prefix)]
        for k in keys:
            self._store.pop(k, None)
        return len(keys)

    async def clear(self) -> int:
        """전체 비우기. 삭제 개수 반환."""
        n = len(self._store)
        self._store.clear()
        return n

    # -------- stampede-safe 로드 --------
    async def get_or_load(
        self,
        key: str,
        loader: Callable[[], Awaitable[Any]],
        ttl: Optional[float] = None,
    ) -> Any:
        """
        캐시 조회 → 없으면 로더 실행 후 저장. Stampede 방지 포함.

        - CACHE_ENABLED=false면 캐시를 완전히 우회하고 로더만 실행.
        - 로더 결과가 None이면 negative TTL로 캐싱(반복 미존재 조회 차단).
        - 캐시 계층 예외는 로그만 남기고 로더로 폴백(요청 실패 방지).
        - 로더 자체 예외(=DB 오류)는 그대로 전파.
        """
        if not settings.CACHE_ENABLED:
            return await loader()

        # 1차 조회 (락 없이)
        hit = await self._safe_get(key)
        if hit is not MISS:
            return hit

        # 미스 → 키별 락
        lock = self._acquire_lock(key)
        try:
            async with lock:
                # double-check: 대기 중 다른 코루틴이 이미 채웠을 수 있음
                hit = await self._safe_get(key)
                if hit is not MISS:
                    return hit

                result = await loader()  # DB 오류는 여기서 전파됨

                entry_ttl = self.negative_ttl if result is None else ttl
                await self._safe_set(key, result, entry_ttl)
                return result
        finally:
            self._release_lock(key)

    # -------- 내부: 예외 안전 래퍼 (캐시 실패 → 폴백) --------
    async def _safe_get(self, key: str) -> Any:
        try:
            return await self.get(key)
        except Exception as e:  # pragma: no cover
            logger.warning("[cache] get 실패 key=%s: %s", key, e)
            return MISS

    async def _safe_set(self, key: str, value: Any, ttl: Optional[float]) -> None:
        try:
            await self.set(key, value, ttl)
        except Exception as e:  # pragma: no cover
            logger.warning("[cache] set 실패 key=%s: %s", key, e)

    # -------- 내부: refcount 기반 키별 락 --------
    def _acquire_lock(self, key: str) -> asyncio.Lock:
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        self._lock_users[key] = self._lock_users.get(key, 0) + 1
        return lock

    def _release_lock(self, key: str) -> None:
        n = self._lock_users.get(key, 0) - 1
        if n <= 0:
            self._locks.pop(key, None)
            self._lock_users.pop(key, None)
        else:
            self._lock_users[key] = n


# ==========================================================
# 키 규약 헬퍼:  {리소스}:{식별자}:v{스키마버전}
# ==========================================================
def make_key(resource: str, identifier: str) -> str:
    """예: make_key('species', '12345') -> 'species:12345:v1'"""
    return f"{resource}:{identifier}:v{settings.CACHE_SCHEMA_VERSION}"


def make_list_key(resource: str, params: dict) -> str:
    """
    목록 엔드포인트용 키. 파라미터를 정렬해 순서 무관 동일 키 생성.
    None 값은 제외. 예: 'species:list:page=2&size=20:v1'
    """
    items = sorted((str(k), str(v)) for k, v in params.items() if v is not None)
    ident = "&".join(f"{k}={v}" for k, v in items)
    return f"{resource}:list:{ident}:v{settings.CACHE_SCHEMA_VERSION}"


# ==========================================================
# 모듈 싱글톤 (앱 전역 공유; lifespan에서 app.state에도 부착)
# 테스트/무효화에서 교체 가능하도록 함수로 접근.
# ==========================================================
cache = InMemoryCache(
    maxsize=settings.CACHE_MAXSIZE,
    default_ttl=settings.CACHE_TTL,
    negative_ttl=settings.CACHE_NEGATIVE_TTL,
)


def get_cache() -> InMemoryCache:
    """현재 캐시 인스턴스 반환(DI/무효화 엔드포인트용)."""
    return cache
