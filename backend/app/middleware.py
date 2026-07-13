"""
HTTP 캐시 헤더 미들웨어.

전역 읽기(GET) 식물 엔드포인트 응답에:
- `Cache-Control: public, max-age=<CACHE_TTL>`
- `Vary: Authorization`  (상세의 is_favorite가 토큰마다 다르므로 공유 캐시 오염 방지)
- `ETag`(본문 해시) 부여 후, 요청의 `If-None-Match`가 일치하면 304로 응답
  (Android OkHttp 등 클라이언트 캐시가 활용)

per-user 목록(/plants/favorites)과 /users/* 는 대상에서 제외한다.
"""
import hashlib

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


def _is_cacheable(request: Request) -> bool:
    if request.method != "GET":
        return False
    path = request.url.path
    prefix = f"{settings.API_V1_STR}/plants"
    if not path.startswith(prefix):
        return False
    # per-user 찜 목록은 공개 캐시 금지
    if path.endswith("/favorites"):
        return False
    return True


class CacheHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if not _is_cacheable(request) or response.status_code != 200:
            return response

        # 본문을 모아 ETag 계산 (JSONResponse 등 비스트리밍 응답 대상)
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        etag = 'W/"' + hashlib.sha1(body).hexdigest() + '"'
        headers = dict(response.headers)
        headers["Cache-Control"] = f"public, max-age={settings.CACHE_TTL}"
        headers["ETag"] = etag
        # Vary 병합 (기존 값 보존)
        vary = headers.get("Vary")
        headers["Vary"] = f"{vary}, Authorization" if vary else "Authorization"
        headers.pop("content-length", None)  # 본문 재구성 시 재계산되도록

        # 조건부 요청: If-None-Match 일치 → 304 (본문 없음)
        if request.headers.get("if-none-match") == etag:
            not_modified = Response(status_code=304)
            for k in ("ETag", "Cache-Control", "Vary"):
                not_modified.headers[k] = headers[k]
            return not_modified

        return Response(
            content=body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )
