"""
관리자 전용 엔드포인트.

- POST /admin/cache/invalidate : 캐시 무효화 (ETL로 종 데이터 갱신 후 호출)
  - prefix 지정 시 해당 접두사 키만, 미지정 시 전체 비우기.
  - X-Admin-Token 헤더 ↔ settings.CACHE_INVALIDATE_TOKEN 검사.
    토큰이 설정되지 않았거나(빈값) 불일치면 401 → 인증 없이 열리지 않는다.
"""
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from app.cache import get_cache
from app.core.config import settings

router = APIRouter()


class InvalidateRequest(BaseModel):
    prefix: Optional[str] = None   # 예: "species", "stories-popular". 없으면 전체.


class InvalidateResponse(BaseModel):
    removed: int
    scope: str


def _check_token(token: Optional[str]) -> None:
    configured = settings.CACHE_INVALIDATE_TOKEN
    # 토큰 미설정이면 기능 자체를 잠근다 (실수로 공개되는 것 방지)
    if not configured or token != configured:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="관리자 토큰이 유효하지 않습니다.",
        )


@router.post("/cache/invalidate", response_model=InvalidateResponse)
async def invalidate_cache(
    body: InvalidateRequest | None = None,
    x_admin_token: Optional[str] = Header(default=None),
):
    _check_token(x_admin_token)
    cache = get_cache()

    prefix = body.prefix if body else None
    if prefix:
        removed = await cache.delete_prefix(prefix)
        return InvalidateResponse(removed=removed, scope=f"prefix:{prefix}")

    removed = await cache.clear()
    return InvalidateResponse(removed=removed, scope="all")
