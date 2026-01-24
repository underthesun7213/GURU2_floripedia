import asyncio
import json
import uuid
from typing import List, Optional, Dict

from app.repositories import PlantRepository, UserRepository
from app.services.gemini_service import GeminiService
from app.services.image_search_service import image_search_service

class PlantService:
    """
    식물 비즈니스 로직 담당 (Service Layer)
    """

    def __init__(
        self,
        plant_repo: PlantRepository,
        user_repo: UserRepository,
        gemini_service: GeminiService = None,
    ):
        self.plant_repo = plant_repo
        self.user_repo = user_repo
        self.gemini = gemini_service or GeminiService()

    # =========================================================
    # 1. 이미지 기반 검색 (학명 조회 + 병렬 생성)
    # =========================================================
    async def search_by_image(self, image_data: bytes, user_id: Optional[str] = None) -> dict:
        # 1. Gemini: 이미지에서 식물 이름 및 학명 추출
        identified = await self.gemini.get_plant_name_from_image(image_data)
        
        # [디버그 로그]
        print(f"DEBUG: identified result: {identified}")
        
        if not identified or not identified.get("name"):
            raise ValueError("식물을 식별할 수 없습니다.")
        
        target_name = identified["name"]
        target_scientific_name = identified.get("scientificName", "").strip()
        
        # 2. DB 조회 (학명 우선, spp 제외 로직)
        plant_in_db = None
        is_specific_scientific_name = (
            target_scientific_name 
            and "spp" not in target_scientific_name.lower() 
            and "sp." not in target_scientific_name.lower()
        )

        if is_specific_scientific_name:
            try:
                plant_in_db = await self.plant_repo.get_by_scientific_name(target_scientific_name)
            except AttributeError:
                pass
        
        if not plant_in_db:
            plant_in_db = await self.plant_repo.get_by_name(target_name)

        # 3. 이미 DB에 존재하면 반환
        if plant_in_db:
            is_fav = False
            if user_id:
                favorites = await self.user_repo.get_favorites(user_id)
                is_fav = str(plant_in_db["_id"]) in favorites

            result = plant_in_db.copy()
            result["is_newly_created"] = False
            result["is_favorite"] = is_fav
            return result

        # 4. 없으면 신규 생성 (병렬 처리)
        print(f"[{target_name}] 신규 생성 시작 (Parallel)...")
        
        task_data = self.gemini.generate_plant_data_schema(target_name, target_scientific_name)
        task_images = image_search_service.get_plant_images_tiered(
            target_name, 
            identified.get("englishName", ""), 
            target_scientific_name
        )

        new_plant_data, image_urls = await asyncio.gather(task_data, task_images)

        if not new_plant_data:
            raise RuntimeError("식물 데이터 생성 실패")

        # 5. 데이터 병합 & ID 충돌 방지 로직 
        new_plant_data["images"] = image_urls
        new_plant_data["imageUrl"] = image_urls[0] if image_urls else None

        # [FIX] Gemini가 만든 _id가 있다면 삭제
        if "_id" in new_plant_data:
            del new_plant_data["_id"]
        
        # [FIX] 고유한 UUID를 _id로 할당 (DuplicateKeyError 방지)
        new_plant_data["_id"] = str(uuid.uuid4())

        # 6. DB 저장
        saved_plant = await self.plant_repo.create(new_plant_data)

        # 7. 반환
        result = saved_plant.copy()
        result["is_newly_created"] = True
        result["is_favorite"] = False
        
        return result

    # =========================================================
    # 2. 텍스트 기반 추천 (학명 조회 + 에세이)
    # =========================================================
    async def recommend_plants(self, situation: str) -> dict:
        # 1. Gemini: 이름 선정
        identified = await self.gemini.get_plant_name_from_text(situation)
        if not identified or not identified.get("name"):
            raise ValueError("적절한 식물을 추천하지 못했습니다.")
            
        target_name = identified["name"]
        target_scientific_name = identified.get("scientificName", "").strip()
        
        # 2. DB 조회
        plant_in_db = None
        if target_scientific_name:
            try:
                plant_in_db = await self.plant_repo.get_by_scientific_name(target_scientific_name)
            except AttributeError:
                pass
        
        if not plant_in_db:
            plant_in_db = await self.plant_repo.get_by_name(target_name)
        
        # 3. 없으면 생성
        if not plant_in_db:
            print(f"[{target_name}] 추천 식물 생성 시작...")
            task_data = self.gemini.generate_plant_data_schema(target_name, target_scientific_name)
            task_images = image_search_service.get_plant_images_tiered(
                target_name, 
                identified.get("englishName", ""), 
                target_scientific_name
            )
            
            new_plant_data, image_urls = await asyncio.gather(task_data, task_images)
            
            if new_plant_data:
                new_plant_data["images"] = image_urls
                new_plant_data["imageUrl"] = image_urls[0] if image_urls else None
                
                # [FIX] 여기서도 ID 충돌 방지 로직 적용
                if "_id" in new_plant_data:
                    del new_plant_data["_id"]
                new_plant_data["_id"] = str(uuid.uuid4())
                
                plant_in_db = await self.plant_repo.create(new_plant_data)
            else:
                raise RuntimeError("추천 식물 데이터 생성 실패")

        # 4. 에세이 작성
        essay = await self.gemini.generate_recommendation_essay(situation, plant_in_db)
        
        result = plant_in_db.copy()
        result["recommendation"] = essay
        return result

    # ... (나머지 조회 메서드)
    async def get_plants(self, season: Optional[str] = None, blooming_month: Optional[int] = None, category_group: Optional[str] = None, color_group: Optional[str] = None, scent_group: Optional[str] = None, flower_group: Optional[str] = None, story_genre: Optional[str] = None, keyword: Optional[str] = None, skip: int = 0, limit: int = 20, sort_by: str = "name", sort_order: str = "asc") -> List[dict]:
        order = 1 if sort_order == "asc" else -1
        return await self.plant_repo.get_list(season=season, blooming_month=blooming_month, category_group=category_group, color_group=color_group, scent_group=scent_group, flower_group=flower_group, story_genre=story_genre, keyword=keyword, skip=skip, limit=limit, sort_by=sort_by, sort_order=order)

    async def get_user_favorites(self, user_id: str, season: Optional[str] = None, category_group: Optional[str] = None, color_group: Optional[str] = None, skip: int = 0, limit: int = 20) -> List[dict]:
        favorite_ids = await self.user_repo.get_favorites(user_id)
        if not favorite_ids: return []
        return await self.plant_repo.get_list(plant_ids=favorite_ids, season=season, category_group=category_group, color_group=color_group, skip=skip, limit=limit, sort_by="name")

    async def get_plants_count(self, season: Optional[str] = None, blooming_month: Optional[int] = None, category_group: Optional[str] = None, color_group: Optional[str] = None, scent_group: Optional[str] = None, flower_group: Optional[str] = None, story_genre: Optional[str] = None, keyword: Optional[str] = None) -> int:
        return await self.plant_repo.count(season=season, blooming_month=blooming_month, category_group=category_group, color_group=color_group, scent_group=scent_group, flower_group=flower_group, story_genre=story_genre, keyword=keyword)

    async def get_plant_detail(self, plant_id: str, user_id: Optional[str] = None) -> Optional[dict]:
        plant = await self.plant_repo.get_by_id(plant_id)
        if not plant: return None
        await self.plant_repo.increment_view_count(plant_id)
        is_favorite = False
        if user_id:
            favorites = await self.user_repo.get_favorites(user_id)
            is_favorite = plant_id in favorites
        plant["is_favorite"] = is_favorite
        return plant