"""
식물 비즈니스 로직 담당 (Service Layer)
- 디버그 로깅 포함
- DB-only 모드: 식물 데이터는 사전 큐레이션된 DB에서만 조회
"""
import logging
from datetime import datetime
from typing import List, Optional

from app.repositories import PlantRepository, UserRepository
from app.services.gemini_service import GeminiService, gemini_service

# 로거 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 콘솔 핸들러 (없으면 추가)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(handler)


class PlantService:
    """
    식물 비즈니스 로직 담당 (Service Layer)
    """

    def __init__(
        self,
        plant_repo: PlantRepository,
        user_repo: UserRepository,
        gemini_svc: GeminiService = None,
    ):
        self.plant_repo = plant_repo
        self.user_repo = user_repo
        # 싱글톤 인스턴스 사용 (메모리 효율적)
        self.gemini = gemini_svc or gemini_service

    # =========================================================
    # 1. 이미지 기반 검색 (DB-only 모드)
    # =========================================================
    async def search_by_image(self, image_data: bytes, user_id: Optional[str] = None) -> dict:
        """
        이미지로 식물 검색 (DB-only 모드).

        [흐름]
        1. Gemini로 이미지에서 식물 식별
        2. DB 조회 (학명 정확 → 이름 정확 → 학명 퍼지)
        3. 없으면 에러 반환
        """
        start_time = datetime.now()
        logger.info("=" * 50)
        logger.info("[search_by_image] 이미지 검색 시작")
        logger.info(f"   - 이미지 크기: {len(image_data):,} bytes")
        logger.info(f"   - user_id: {user_id or 'Anonymous'}")

        # 1. Gemini: 이미지에서 식물 이름 및 학명 추출
        logger.debug("[Step 1] Gemini 식물 식별 호출...")
        identified = await self.gemini.get_plant_name_from_image(image_data)

        logger.info(f"[Step 1 완료] Gemini 식별 결과: {identified}")

        if not identified or not identified.get("name"):
            logger.warning("[실패] 식물을 식별할 수 없음")
            raise ValueError("식물을 식별할 수 없습니다.")

        target_name = identified["name"]
        target_scientific_name = identified.get("scientificName", "").strip()
        target_english_name = identified.get("englishName", "")

        logger.info(f"   - 식별된 이름: {target_name}")
        logger.info(f"   - 학명: {target_scientific_name}")
        logger.info(f"   - 영문명: {target_english_name}")

        # 2. DB 조회 (3단계: 학명 정확 → 이름 정확 → 학명 퍼지)
        logger.debug("[Step 2] DB 조회 시작...")
        plant_in_db = None

        # 2-1. 학명 정확 일치
        if target_scientific_name:
            logger.debug(f"   - [1차] 학명 정확 일치 조회: {target_scientific_name}")
            plant_in_db = await self.plant_repo.get_by_scientific_name(target_scientific_name)

        # 2-2. 이름 정확 일치
        if not plant_in_db:
            logger.debug(f"   - [2차] 이름 정확 일치 조회: {target_name}")
            plant_in_db = await self.plant_repo.get_by_name(target_name)

        # 2-3. 학명 퍼지 매칭 (속 기준)
        if not plant_in_db and target_scientific_name:
            logger.debug(f"   - [3차] 학명 퍼지 매칭 조회: {target_scientific_name}")
            plant_in_db = await self.plant_repo.find_by_scientific_name_fuzzy(target_scientific_name)

        # 3. DB에 존재하면 반환
        if plant_in_db:
            logger.info(f"[Step 2 완료] DB에서 발견: {plant_in_db.get('_id')}")
            is_fav = False
            if user_id:
                favorites = await self.user_repo.get_favorites(user_id)
                is_fav = str(plant_in_db["_id"]) in favorites

            result = plant_in_db.copy()
            result["is_newly_created"] = False
            result["is_favorite"] = is_fav

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"[search_by_image 완료] 기존 데이터 반환 (소요시간: {elapsed:.2f}초)")
            logger.info("=" * 50)
            return result

        # 4. DB에 없으면 에러 반환
        logger.warning(f"[실패] '{target_name}' ({target_scientific_name}) - DB에 해당 식물 정보 없음")
        raise ValueError(f"'{target_name}'에 대한 정보가 데이터베이스에 없습니다.")
    # =========================================================
    # 2. 텍스트 기반 추천 (DB-only 모드 + 에세이)
    # =========================================================
    async def recommend_plants(self, situation: str) -> dict:
        """
        상황 기반 식물 추천 (DB-only 모드).

        [흐름]
        1. Gemini로 상황에 맞는 식물 선정
        2. DB 조회 (학명 정확 → 이름 정확 → 학명 퍼지)
        3. 없으면 에러 반환
        4. 추천 에세이 생성
        """
        start_time = datetime.now()
        logger.info("=" * 50)
        logger.info("[recommend_plants] 텍스트 기반 추천 시작")
        logger.info(f"  - 상황: {situation[:50]}{'...' if len(situation) > 50 else ''}")

        # 1. Gemini: 이름 선정
        logger.debug("[Step 1] Gemini 식물 선정 호출...")
        identified = await self.gemini.get_plant_name_from_text(situation)

        if not identified or not identified.get("name"):
            logger.warning("[실패] 적절한 식물을 추천하지 못함")
            raise ValueError("적절한 식물을 추천하지 못했습니다.")

        target_name = identified["name"]
        target_scientific_name = identified.get("scientificName", "").strip()

        logger.info(f"[Step 1 완료] 추천 식물: {target_name} ({target_scientific_name})")

        # 2. DB 조회 (3단계: 학명 정확 → 이름 정확 → 학명 퍼지)
        logger.debug("[Step 2] DB 조회 시작...")
        plant_in_db = None

        # 2-1. 학명 정확 일치
        if target_scientific_name:
            logger.debug(f"   - [1차] 학명 정확 일치 조회: {target_scientific_name}")
            plant_in_db = await self.plant_repo.get_by_scientific_name(target_scientific_name)

        # 2-2. 이름 정확 일치
        if not plant_in_db:
            logger.debug(f"   - [2차] 이름 정확 일치 조회: {target_name}")
            plant_in_db = await self.plant_repo.get_by_name(target_name)

        # 2-3. 학명 퍼지 매칭 (속 기준)
        if not plant_in_db and target_scientific_name:
            logger.debug(f"   - [3차] 학명 퍼지 매칭 조회: {target_scientific_name}")
            plant_in_db = await self.plant_repo.find_by_scientific_name_fuzzy(target_scientific_name)

        # 3. DB에 없으면 에러 반환
        if not plant_in_db:
            logger.warning(f"[실패] '{target_name}' ({target_scientific_name}) - DB에 해당 식물 정보 없음")
            raise ValueError(f"'{target_name}'에 대한 정보가 데이터베이스에 없습니다.")

        logger.info(f"[Step 2 완료] DB에서 발견: {plant_in_db.get('_id')}")

        # 4. 에세이 작성
        logger.debug("[Step 3] 추천 에세이 생성 중...")
        essay = await self.gemini.generate_recommendation_essay(situation, plant_in_db)
        logger.info(f"[Step 3 완료] 에세이 길이: {len(essay)}자")

        result = plant_in_db.copy()
        result["recommendation"] = essay

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"[recommend_plants 완료] 소요시간: {elapsed:.2f}초")
        logger.info("=" * 50)

        return result

    # =========================================================
    # 3. 목록 조회
    # =========================================================
    async def get_plants(
        self, 
        season: Optional[str] = None, 
        blooming_month: Optional[int] = None, 
        category_group: Optional[str] = None, 
        color_group: Optional[str] = None, 
        scent_group: Optional[str] = None, 
        flower_group: Optional[str] = None, 
        story_genre: Optional[str] = None, 
        keyword: Optional[str] = None, 
        skip: int = 0, 
        limit: int = 20, 
        sort_by: str = "name", 
        sort_order: str = "asc"
    ) -> List[dict]:
        """식물 목록 조회 (필터링 + 페이지네이션)"""
        logger.debug(f"[get_plants] skip={skip}, limit={limit}, sort_by={sort_by}")
        
        order = 1 if sort_order == "asc" else -1
        result = await self.plant_repo.get_list(
            season=season, 
            blooming_month=blooming_month, 
            category_group=category_group, 
            color_group=color_group, 
            scent_group=scent_group, 
            flower_group=flower_group, 
            story_genre=story_genre, 
            keyword=keyword, 
            skip=skip, 
            limit=limit, 
            sort_by=sort_by, 
            sort_order=order
        )
        
        logger.debug(f"[get_plants] 결과: {len(result)}개")
        return result

    async def get_user_favorites(
        self, 
        user_id: str, 
        season: Optional[str] = None, 
        category_group: Optional[str] = None, 
        color_group: Optional[str] = None, 
        skip: int = 0, 
        limit: int = 20
    ) -> List[dict]:
        """사용자 찜 목록 조회"""
        logger.debug(f"[get_user_favorites] user_id={user_id}")
        
        favorite_ids = await self.user_repo.get_favorites(user_id)
        if not favorite_ids:
            logger.debug("[get_user_favorites] 찜 목록 없음")
            return []
            
        result = await self.plant_repo.get_list(
            plant_ids=favorite_ids, 
            season=season, 
            category_group=category_group, 
            color_group=color_group, 
            skip=skip, 
            limit=limit, 
            sort_by="name"
        )
        
        logger.debug(f"[get_user_favorites] 결과: {len(result)}개")
        return result

    async def get_plants_count(
        self, 
        season: Optional[str] = None, 
        blooming_month: Optional[int] = None, 
        category_group: Optional[str] = None, 
        color_group: Optional[str] = None, 
        scent_group: Optional[str] = None, 
        flower_group: Optional[str] = None, 
        story_genre: Optional[str] = None, 
        keyword: Optional[str] = None
    ) -> int:
        """필터 조건에 맞는 식물 개수"""
        count = await self.plant_repo.count(
            season=season, 
            blooming_month=blooming_month, 
            category_group=category_group, 
            color_group=color_group, 
            scent_group=scent_group, 
            flower_group=flower_group, 
            story_genre=story_genre, 
            keyword=keyword
        )
        logger.debug(f"[get_plants_count] 결과: {count}개")
        return count

    # =========================================================
    # 4. 상세 조회
    # =========================================================
    async def get_plant_detail(self, plant_id: str, user_id: Optional[str] = None) -> Optional[dict]:
        """식물 상세 조회 (조회수 증가 포함)"""
        logger.debug(f"[get_plant_detail] plant_id={plant_id}, user_id={user_id}")
        
        plant = await self.plant_repo.get_by_id(plant_id)
        if not plant:
            logger.warning(f"[get_plant_detail] 식물을 찾을 수 없음: {plant_id}")
            return None
            
        # 조회수 증가
        await self.plant_repo.increment_view_count(plant_id)
        logger.debug(f"[get_plant_detail] 조회수 증가: {plant_id}")
        
        # 찜 여부 확인
        is_favorite = False
        if user_id:
            favorites = await self.user_repo.get_favorites(user_id)
            is_favorite = plant_id in favorites
            
        plant["is_favorite"] = is_favorite
        
        logger.debug(f"[get_plant_detail] 완료: {plant.get('name')}")
        return plant
