"""
MongoDB 비동기 연결 관리 모듈.

Motor(AsyncIO MongoDB Driver)를 사용하여 비동기 DB 연결을 관리한다.
애플리케이션 전역에서 mongodb 싱글톤 인스턴스를 사용한다.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings


class MongoDB:
    """
    MongoDB 연결 관리 클래스.

    FastAPI lifespan 이벤트에서 connect/close를 호출하여
    애플리케이션 생명주기에 맞게 연결을 관리한다.
    """

    def __init__(self):
        self.client: AsyncIOMotorClient | None = None
        self.db: AsyncIOMotorDatabase | None = None

    async def connect(self) -> None:
        """MongoDB Atlas 연결 수립."""
        self.client = AsyncIOMotorClient(settings.MONGO_URI)
        self.db = self.client[settings.MONGODB_DB_NAME]
        print(f"[MongoDB] Connected to '{settings.MONGODB_DB_NAME}'")

    async def close(self) -> None:
        """MongoDB 연결 해제."""
        if self.client:
            self.client.close()
            print("[MongoDB] Connection closed")


# 전역 싱글톤 인스턴스
mongodb = MongoDB()