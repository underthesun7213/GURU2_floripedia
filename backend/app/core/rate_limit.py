"""
uid별 일일 요청 rate limit (AI 과금 엔드포인트 남용 방지).

Google 프로젝트 할당량은 전체 합산이라 "1인당" 제한이 안 된다.
익명 uid를 키로 하루 단위 카운터를 MongoDB에 두어 1인당 상한을 건다.
(인메모리 대신 DB를 쓰는 이유: 재시작/배포에도 카운트가 유지되어야 함)

문서 스키마: { _id: "<uid>:<YYYY-MM-DD>", count: int, expireAt: datetime }
expireAt에 TTL 인덱스를 걸어 지난 카운터는 자동 삭제된다(create_rate_limit_index).
"""
import logging
from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument

logger = logging.getLogger(__name__)

COLLECTION = "rate_limits"


async def create_rate_limit_index(db) -> None:
    """expireAt 기준 TTL 인덱스 생성(멱등). 앱 startup에서 1회 호출."""
    await db[COLLECTION].create_index("expireAt", expireAfterSeconds=0)


async def check_and_increment(db, uid: str, limit: int) -> bool:
    """
    uid의 오늘 카운터를 원자적으로 +1 하고, 상한 초과 여부를 반환한다.

    Returns:
        True  → 허용(상한 이내)
        False → 거부(상한 초과)

    DB 오류 시에는 fail-open(허용)하여 우리 버그로 정상 사용자를 막지 않는다.
    (App Check·인증·Google 할당량이 추가 방어선으로 존재)
    """
    now = datetime.now(timezone.utc)
    key = f"{uid}:{now.strftime('%Y-%m-%d')}"
    try:
        doc = await db[COLLECTION].find_one_and_update(
            {"_id": key},
            {
                "$inc": {"count": 1},
                "$setOnInsert": {"expireAt": now + timedelta(days=2)},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        count = doc.get("count", 1)
        if count > limit:
            logger.warning(f"[RateLimit] 상한 초과: uid={uid} count={count}/{limit}")
            return False
        return True
    except Exception as e:
        logger.error(f"[RateLimit] 카운터 처리 실패(fail-open): {e}")
        return True
