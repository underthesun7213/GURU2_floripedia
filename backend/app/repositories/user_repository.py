from typing import Optional, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase


class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["users"]

    async def get_by_id(self, user_id: str) -> Optional[dict]:
        """
        ID(Firebase UID)로 유저 조회.
        """
        try:
            return await self.collection.find_one({"_id": user_id})
        except Exception:
            return None

    async def get_by_email(self, email: str) -> Optional[dict]:
        """이메일로 기존 유저 확인"""
        return await self.collection.find_one({"email": email})

    async def create(self, user_dict: dict) -> dict:
        """
        신규 유저 생성.
        user_dict 안에 '_id' (Firebase UID)가 반드시 포함되어 있어야 합니다.
        """
        await self.collection.insert_one(user_dict)
        return user_dict

    async def update(self, user_id: str, update_data: dict) -> Optional[dict]:
        """유저 정보 수정"""
        update_data["updatedAt"] = datetime.now(timezone.utc)
        try:
            # String ID 사용
            await self.collection.update_one(
                {"_id": user_id},
                {"$set": update_data}
            )
            return await self.get_by_id(user_id)
        except Exception:
            return None

    async def soft_delete(self, user_id: str) -> bool:
        """유저 소프트 삭제 (isActive = False)"""
        try:
            # String ID 사용
            result = await self.collection.update_one(
                {"_id": user_id},
                {"$set": {"isActive": False, "updatedAt": datetime.now(timezone.utc)}}
            )
            return result.modified_count > 0
        except Exception:
            return False

    async def add_favorite(self, user_id: str, plant_id: str) -> bool:
        """
        찜 목록에 식물 ID 추가.
        plant_id는 MongoDB ObjectId의 문자열 표현(Hex string)을 저장합니다.
        """
        try:
            result = await self.collection.update_one(
                {"_id": user_id},
                {"$addToSet": {"favoritePlantIds": plant_id}}
            )
            return result.modified_count > 0
        except Exception:
            return False

    async def remove_favorite(self, user_id: str, plant_id: str) -> bool:
        """찜 목록에서 식물 ID 제거"""
        try:
            result = await self.collection.update_one(
                {"_id": user_id},
                {"$pull": {"favoritePlantIds": plant_id}}
            )
            return result.modified_count > 0
        except Exception:
            return False

    async def get_favorites(self, user_id: str) -> List[str]:
        """유저의 찜 목록(Plant ID 리스트) 조회"""
        user = await self.get_by_id(user_id)
        if user:
            return user.get("favoritePlantIds", [])
        return []