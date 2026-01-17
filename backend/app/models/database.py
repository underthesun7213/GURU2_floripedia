from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


class Database:
    client: AsyncIOMotorClient = None


db = Database()


async def connect_to_mongo():
    """MongoDB 연결"""
    db.client = AsyncIOMotorClient(settings.MONGODB_URL)
    # 연결 테스트
    await db.client.admin.command('ping')


async def close_mongo_connection():
    """MongoDB 연결 종료"""
    if db.client:
        db.client.close()
