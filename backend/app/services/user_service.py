"""
사용자 관련 비즈니스 로직 서비스.
프로필 관리, 찜 기능, 계정 관리 등 사용자 관련 핵심 로직을 처리합니다.
"""
from typing import List, Optional

from app.repositories import UserRepository, PlantRepository
from app.services.firebase_service import firebase_storage


class UserService:
    """사용자 비즈니스 로직 서비스"""

    def __init__(self, user_repo: UserRepository, plant_repo: PlantRepository):
        self.user_repo = user_repo
        self.plant_repo = plant_repo

    # ==========================================
    # 프로필 관리
    # ==========================================

    async def get_profile(self, user_id: str) -> Optional[dict]:
        """사용자 프로필 조회."""
        # user_id는 Firebase UID (String)
        user = await self.user_repo.get_by_id(user_id)

        if not user:
            return None

        if not user.get("isActive", True):
            raise ValueError("탈퇴한 계정입니다")

        return user

    async def update_profile(self, user_id: str, update_data: dict) -> Optional[dict]:
        """프로필 정보 수정."""
        if not update_data:
            return None
        return await self.user_repo.update(user_id, update_data)

    async def upload_profile_image(
        self, user_id: str, file_data: bytes, content_type: str
    ) -> dict:
        """프로필 이미지 업로드 및 URL 저장."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("유저를 찾을 수 없습니다")

        try:
            # Firebase Storage 업로드
            image_url = firebase_storage.upload_profile_image(
                user_id=user_id,
                file_data=file_data,
                content_type=content_type,
            )
            
            # DB 업데이트
            updated_user = await self.user_repo.update(
                user_id, {"profileImageUrl": image_url}
            )
            return updated_user

        except Exception as e:
            raise RuntimeError(f"이미지 업로드 실패: {str(e)}")

    # ==========================================
    # 찜(꽃갈피) 기능
    # ==========================================

    async def toggle_favorite(self, user_id: str, plant_id: str) -> dict:
        """식물 찜하기/취소 토글."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("유저를 찾을 수 없습니다")

        # Plant ID 유효성 검사 (Repository 내부에서 ObjectId 변환 수행됨)
        plant = await self.plant_repo.get_by_id(plant_id)
        if not plant:
            raise ValueError("식물을 찾을 수 없습니다")

        current_favorites = user.get("favoritePlantIds", [])
        is_currently_favorite = plant_id in current_favorites

        if is_currently_favorite:
            await self.user_repo.remove_favorite(user_id, plant_id)
            await self.plant_repo.increment_favorite_count(plant_id, delta=-1)
            return {"isFavorite": False, "message": "찜이 취소되었습니다"}
        else:
            await self.user_repo.add_favorite(user_id, plant_id)
            await self.plant_repo.increment_favorite_count(plant_id, delta=1)
            return {"isFavorite": True, "message": "찜 목록에 추가되었습니다"}

    async def get_favorites(
        self,
        user_id: str,
        sort_by: str = "name",
        sort_order: str = "asc",
    ) -> List[dict]:
        """찜 목록 조회."""
        favorite_ids = await self.user_repo.get_favorites(user_id)

        if not favorite_ids:
            return []

        plants = []
        # 저장된 ID들로 식물 정보를 조회
        for plant_id in favorite_ids:
            plant = await self.plant_repo.get_by_id(plant_id)
            if plant:
                plants.append({
                    "_id": str(plant["_id"]),
                    "name": plant["name"],
                    "flowerInfo": plant.get("flowerInfo", {"language": "", "flowerGroup": "기타"}),
                    "imageUrl": plant.get("imageUrl", "")
                })

        # 정렬
        reverse = sort_order == "desc"
        if sort_by == "name":
            plants.sort(key=lambda x: x["name"], reverse=reverse)
        elif sort_by == "recent":
            if not reverse: 
                plants.reverse() 
            
        return plants

    async def get_favorites_count(self, user_id: str) -> int:
        """찜 목록 개수 조회."""
        favorite_ids = await self.user_repo.get_favorites(user_id)
        return len(favorite_ids)

    # ==========================================
    # 계정 관리
    # ==========================================

    async def delete_account(self, user_id: str) -> bool:
        """회원 탈퇴 (Soft Delete)."""
        return await self.user_repo.soft_delete(user_id)