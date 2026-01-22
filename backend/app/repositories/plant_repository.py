from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models import PlantModel


class PlantRepository:
    """식물 데이터 접근 계층"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["plants"]

    async def get_by_id(self, plant_id: str) -> Optional[dict]:
        """ID로 식물 상세 조회"""
        return await self.collection.find_one({"_id": plant_id})

    async def get_by_name(self, name: str) -> Optional[dict]:
        """이름으로 식물 조회 (정확히 일치)"""
        return await self.collection.find_one({"name": name})

    async def search_by_name(self, name: str) -> Optional[dict]:
        """이름으로 식물 검색 (부분 일치, 첫 번째 결과)"""
        return await self.collection.find_one(
            {"name": {"$regex": name, "$options": "i"}}
        )
    async def get_by_scientific_name(self, scientific_name: str) -> Optional[dict]:
        """
        학명(Scientific Name)으로 식물 단건 조회.
        정확히 일치하는 학명을 가진 식물을 찾습니다.
        """
        if not scientific_name:
            return None

        # MongoDB find_one을 사용하여 단일 문서 반환
        return await self.collection.find_one({"scientificName": scientific_name})



    async def create(self, plant_data: dict) -> dict:
        """새 식물 데이터 저장"""
        # _id 생성 (없으면 자동 생성된 것 사용)
        if "_id" not in plant_data:
            # 마지막 ID + 1 로 생성
            last_plant = await self.collection.find_one(
                sort=[("_id", -1)]
            )
            if last_plant:
                try:
                    new_id = str(int(last_plant["_id"]) + 1)
                except ValueError:
                    new_id = str(await self.collection.count_documents({}) + 1)
            else:
                new_id = "1"
            plant_data["_id"] = new_id

        await self.collection.insert_one(plant_data)
        return plant_data

    async def get_list(
        self,
        # 1. 특정 식물 ID 리스트 내에서만 검색 (꽃갈피 기능용)
        plant_ids: Optional[List[str]] = None,
        
        # 2. 필터 조건 (단일 선택)
        season: Optional[str] = None,
        blooming_month: Optional[int] = None,
        category_group: Optional[str] = None,
        color_group: Optional[str] = None,
        scent_group: Optional[str] = None,
        flower_group: Optional[str] = None,
        story_genre: Optional[str] = None,
        keyword: Optional[str] = None,
        
        # 3. 페이지네이션 & 정렬
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "name",
        sort_order: int = 1,
    ) -> List[dict]:
        """
        식물 목록 조회 (일반 목록 & 꽃갈피 목록 통합)
        """
        query = {}

        # [핵심] 꽃갈피 필터링: 전달받은 ID 리스트가 있으면 그 안에서만 찾음
        if plant_ids is not None:
            # plant_ids가 빈 리스트([])라면 찜한게 없다는 뜻이므로 결과도 0개여야 함
            if not plant_ids:
                return []
            query["_id"] = {"$in": plant_ids}

        # --- 단일 필터 조건  ---
        if season:
            query["season"] = season
        if blooming_month:
            query["bloomingMonths"] = blooming_month
        if category_group:
            query["horticulture.categoryGroup"] = category_group
        if color_group:
            query["colorInfo.colorGroup"] = color_group
        if scent_group:
            query["scentInfo.scentGroup"] = scent_group
        if flower_group:
            query["flowerInfo.flowerGroup"] = flower_group
        if story_genre:
            query["stories.genre"] = story_genre
            
        # 키워드 검색
        if keyword:
            query["$or"] = [
                {"name": {"$regex": keyword, "$options": "i"}},
                {"flowerInfo.language": {"$regex": keyword, "$options": "i"}},
                {"searchKeywords": {"$regex": keyword, "$options": "i"}},
            ]

        projection = {
            "_id": 1,
            "name": 1,
            "flowerInfo": 1,
            "imageUrl": 1,
            "season": 1,
            "horticulture.preContent": 1,
        }

        cursor = (
            self.collection.find(query, projection)
            .sort(sort_by, sort_order)
            .skip(skip)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def count(
        self,
        plant_ids: Optional[List[str]] = None,
        **kwargs  # 서비스에서 던지는 모든 필터 인자를 여기서 흡수하여 무시함. 이걸 제거시 카테고리별 cnt 구할 수 있음(추후 확장 가능성)
    ) -> int:
        """
        [꽃갈피 전용] 사용자가 찜한 식물의 전체 개수만 반환.
        필터 조건이 들어와도 무시하고 plant_ids의 전체 길이를 카운트함.
        """
        if not plant_ids:
            return 0

        # 필터링 로직을 모두 제거하고 오직 ID 리스트로만 카운트
        query = {"_id": {"$in": plant_ids}}
        
        return await self.collection.count_documents(query)

    async def increment_view_count(self, plant_id: str) -> None:
        """조회수 증가 + 인기도 실시간 업데이트"""
        popularity_delta = PlantModel.calculate_popularity_delta(view_delta=1)
        await self.collection.update_one(
            {"_id": plant_id},
            {"$inc": {"view_count": 1, "popularity_score": popularity_delta}}
        )

    async def increment_favorite_count(self, plant_id: str, delta: int = 1) -> None:
        """찜 수 증가/감소 + 인기도 실시간 업데이트 (delta: 1 또는 -1)"""
        popularity_delta = PlantModel.calculate_popularity_delta(favorite_delta=delta)
        await self.collection.update_one(
            {"_id": plant_id},
            {"$inc": {"favorite_count": delta, "popularity_score": popularity_delta}}
        )

    async def get_for_recommendation(self, limit: int = 50) -> List[dict]:
        """
        AI 추천용 식물 목록 조회 (필요한 필드만)
        인기도 순으로 정렬하여 상위 N개 반환
        """
        projection = {
            "_id": 1,
            "name": 1,
            "flowerInfo": 1,
            "season": 1,
            "horticulture.categoryGroup": 1,
            "colorInfo.colorGroup": 1,
            "scentInfo.scentGroup": 1,
        }
        cursor = self.collection.find({}, projection).sort(
            "popularity_score", -1
        ).limit(limit)
        return await cursor.to_list(length=limit)


