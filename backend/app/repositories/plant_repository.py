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

    async def find_by_scientific_name_fuzzy(self, scientific_name: str) -> Optional[dict]:
        """
        학명 속(genus) 기준 퍼지 매칭.
        'Myosotis' → 'Myosotis sylvatica' 매칭 가능.
        """
        if not scientific_name:
            return None

        # 속(genus) 추출: "Myosotis sylvatica" → "Myosotis"
        genus = scientific_name.split()[0]
        if not genus:
            return None

        return await self.collection.find_one({
            "scientificName": {"$regex": f"^{genus}", "$options": "i"}
        })



    async def create(self, plant_data: dict) -> dict:
        """새 식물 데이터 저장"""
        # _id 생성 (없으면 자동 생성)
        if "_id" not in plant_data:
            # 전체 _id를 숫자로 변환하여 max 구하기 (문자열 정렬 버그 방지)
            max_id = 0
            async for doc in self.collection.find({}, {"_id": 1}):
                try:
                    max_id = max(max_id, int(doc["_id"]))
                except (ValueError, TypeError):
                    continue
            plant_data["_id"] = str(max_id + 1)

        await self.collection.insert_one(plant_data)
        return plant_data

    def _build_filter_query(
        self,
        plant_ids: Optional[List[str]] = None,
        season: Optional[str] = None,
        blooming_month: Optional[int] = None,
        category_group: Optional[str] = None,
        color_group: Optional[str] = None,
        scent_group: Optional[str] = None,
        flower_group: Optional[str] = None,
        story_genre: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> dict:
        """
        plants 컬렉션 공용 필터 쿼리 빌더.
        get_list()·count()가 동일한 쿼리를 쓰도록 단일 소스로 둔다(쿼리 어긋남 방지).

        plant_ids:
          - None  → _id 제약 없음 (전체 대상)
          - [...] → 해당 id 집합 내에서만 (존재검증 포함)
          - []    → {"$in": []} 로 결과 0 (찜 0개 정합)
        """
        query: dict = {}

        # 특정 ID 집합 내 검색 (꽃갈피 등)
        if plant_ids is not None:
            query["_id"] = {"$in": plant_ids}

        # --- 단일 필터 조건 ---
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

        return query

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
        # [핵심] 꽃갈피 빈 목록 빠른 반환: 찜한 게 없으면 결과 0개
        # ({"$in": []} 로도 동일 결과지만 불필요한 쿼리를 피하는 기존 동작 유지)
        if plant_ids is not None and not plant_ids:
            return []

        query = self._build_filter_query(
            plant_ids=plant_ids,
            season=season,
            blooming_month=blooming_month,
            category_group=category_group,
            color_group=color_group,
            scent_group=scent_group,
            flower_group=flower_group,
            story_genre=story_genre,
            keyword=keyword,
        )

        projection = {
            "_id": 1,
            "name": 1,
            "flowerInfo": 1,
            "imageUrl": 1,
            "season": 1,
            "horticulture.preContent": 1,
        }

        # 인기도 정렬 시 같은 점수끼리 랜덤 셔플 (이름/id 정렬 편향 방지)
        if sort_by == "popularity_score":
            pipeline = [
                {"$match": query},
                {"$project": {**projection, "popularity_score": 1}},
                {"$addFields": {"_rand": {"$rand": {}}}},
                {"$sort": {"popularity_score": sort_order, "_rand": 1}},
                {"$skip": skip},
                {"$limit": limit},
                {"$project": {"_rand": 0}},
            ]
            return await self.collection.aggregate(pipeline).to_list(length=limit)

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
        season: Optional[str] = None,
        blooming_month: Optional[int] = None,
        category_group: Optional[str] = None,
        color_group: Optional[str] = None,
        scent_group: Optional[str] = None,
        flower_group: Optional[str] = None,
        story_genre: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> int:
        """
        필터 조건에 맞는 plants 문서 수 반환 (get_list 와 동일 쿼리 빌더 사용).

        - plant_ids=None : 전체에서 필터 카운트 (일반 GET /plants/count).
        - plant_ids=[...]: 해당 id 집합 ∩ 필터의 '실제 존재' 개수
          (꽃갈피 개수 정합 — 삭제/누락된 찜 id 는 제외됨).
        - plant_ids=[]   : 0 ({"$in": []}).
        """
        query = self._build_filter_query(
            plant_ids=plant_ids,
            season=season,
            blooming_month=blooming_month,
            category_group=category_group,
            color_group=color_group,
            scent_group=scent_group,
            flower_group=flower_group,
            story_genre=story_genre,
            keyword=keyword,
        )
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

    async def get_popular_stories(
        self,
        skip: int = 0,
        limit: int = 10,
    ) -> List[dict]:
        """
        인기 스토리 조회 (Lazy Aggregation).

        필터링 규칙:
        - genre != SCIENCE인 모든 스토리 포함
        - genre == SCIENCE인 경우, 해당 식물의 첫 번째 SCIENCE 스토리만 포함
        - plant의 popularity_score 기준 내림차순 정렬
        """
        pipeline = [
            # 1. 각 식물에서 첫 번째 SCIENCE 스토리의 인덱스를 계산
            {"$addFields": {
                "_firstSciIdx": {
                    "$indexOfArray": [
                        {"$map": {"input": "$stories", "as": "s", "in": "$$s.genre"}},
                        "SCIENCE"
                    ]
                }
            }},
            # 2. stories 배열을 개별 문서로 전개 (인덱스 포함)
            {"$unwind": {"path": "$stories", "includeArrayIndex": "_storyIdx"}},
            # 3. 필터: SCIENCE가 아닌 것 OR (SCIENCE이면서 첫 번째인 것)
            {"$match": {
                "$or": [
                    {"stories.genre": {"$ne": "SCIENCE"}},
                    {"$expr": {"$eq": ["$_storyIdx", "$_firstSciIdx"]}}
                ]
            }},
            # 4. 인기도 내림차순 + 동점 시 랜덤 셔플
            {"$addFields": {"_rand": {"$rand": {}}}},
            {"$sort": {"popularity_score": -1, "_rand": 1}},
            # 5. 페이지네이션
            {"$skip": skip},
            {"$limit": limit},
            # 6. 응답 형태로 프로젝션
            {"$project": {
                "_id": 0,
                "plantId": "$_id",
                "plantName": "$name",
                "imageUrl": "$imageUrl",
                "genre": "$stories.genre",
                "content": "$stories.content",
                "popularityScore": "$popularity_score",
            }},
        ]
        return await self.collection.aggregate(pipeline).to_list(length=limit)

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
        pipeline = [
            {"$project": {**projection, "popularity_score": 1}},
            {"$addFields": {"_rand": {"$rand": {}}}},
            {"$sort": {"popularity_score": -1, "_rand": 1}},
            {"$limit": limit},
            {"$project": {"_rand": 0}},
        ]
        return await self.collection.aggregate(pipeline).to_list(length=limit)


