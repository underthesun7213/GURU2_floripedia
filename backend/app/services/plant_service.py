"""
식물 비즈니스 로직 담당 (Service Layer)
- 디버그 로깅 포함
- 데이터 생성 시 롤백 처리 포함
"""
import asyncio
import logging
import uuid
from datetime import datetime
from typing import List, Optional

from app.repositories import PlantRepository, UserRepository
from app.services.gemini_service import GeminiService, gemini_service
from app.services.image_search_service import image_search_service

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
    # 1. 이미지 기반 검색 (학명 조회 + 병렬 생성)
    # =========================================================
    async def search_by_image(self, image_data: bytes, user_id: Optional[str] = None) -> dict:
        """
        이미지로 식물 검색. DB에 없으면 신규 생성.
        
        [흐름]
        1. Gemini로 이미지에서 식물 식별
        2. DB 조회 (학명 → 이름 순)
        3. 없으면 신규 생성 (Gemini 데이터 + 이미지 검색 병렬)
        4. DB 저장 후 반환 (저장 직전 최종 중복 체크 추가)
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
        
        # 2. DB 조회 (학명 우선, spp 제외 로직)
        logger.debug("[Step 2] DB 조회 시작...")
        plant_in_db = None
        is_specific_scientific_name = (
            target_scientific_name 
            and "spp" not in target_scientific_name.lower() 
            and "sp." not in target_scientific_name.lower()
        )

        if is_specific_scientific_name:
            logger.debug(f"   - 학명으로 조회: {target_scientific_name}")
            try:
                plant_in_db = await self.plant_repo.get_by_scientific_name(target_scientific_name)
            except AttributeError:
                pass
        
        if not plant_in_db:
            logger.debug(f"   - 이름으로 조회: {target_name}")
            plant_in_db = await self.plant_repo.get_by_name(target_name)

        # 3. 이미 DB에 존재하면 반환
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

        # 4. 없으면 신규 생성 (병렬 처리)
        logger.info(f"[Step 3] '{target_name}' 신규 생성 시작 (병렬 처리)")
        
        new_plant_id = str(uuid.uuid4())
        logger.debug(f"   - 생성할 ID: {new_plant_id}")
        
        try:
            # 병렬 실행: Gemini 데이터 생성 + 이미지 검색
            logger.debug("   - Gemini 데이터 생성 + 이미지 검색 병렬 시작...")
            task_data = self.gemini.generate_plant_data_schema(target_name, target_scientific_name)
            task_images = image_search_service.get_plant_images_tiered(
                target_name, 
                target_english_name, 
                target_scientific_name
            )

            new_plant_data, image_urls = await asyncio.gather(task_data, task_images)
            
            logger.info(f"   - Gemini 데이터 생성: {'성공' if new_plant_data else '실패'}")
            logger.info(f"   - 이미지 검색 결과: {len(image_urls)}개")

            if not new_plant_data:
                logger.error("[실패] Gemini 데이터 생성 실패")
                raise RuntimeError("식물 데이터 생성 실패")

            # [추가] Fallback 데이터인지 확인 - DB 저장 금지
            if new_plant_data.get("_is_fallback"):
                logger.error("[실패] Gemini API 실패로 기본값만 생성됨 - DB 저장 금지")
                raise RuntimeError("식물 정보를 가져올 수 없습니다. 잠시 후 다시 시도해주세요.")

            # ---------------------------------------------------------
            # [추가] 최종 중복 체크 로직
            # 제미나이가 '물망이'를 '물망초'로 교정했을 경우를 위해 
            # 저장 직전에 다시 한번 DB를 조회합니다.
            final_name = new_plant_data.get('name', target_name)
            final_check = await self.plant_repo.get_by_name(final_name)
            
            if final_check:
                logger.info(f"   - [중복 발견] 생성된 이름 '{final_name}'이(가) 이미 존재함. 기존 데이터 반환.")
                result = final_check.copy()
                result["is_newly_created"] = False
                result["is_favorite"] = False # 신규 유저 흐름이므로 기본값
                return result
            # ---------------------------------------------------------

            # 5. 데이터 병합 & ID 할당
            new_plant_data["images"] = image_urls
            new_plant_data["imageUrl"] = image_urls[0] if image_urls else None

            # 내부 플래그 및 Gemini가 만든 _id 삭제
            new_plant_data.pop("_is_fallback", None)
            if "_id" in new_plant_data:
                del new_plant_data["_id"]
            
            new_plant_data["_id"] = new_plant_id
            new_plant_data["view_count"] = 0
            new_plant_data["favorite_count"] = 0
            new_plant_data["created_at"] = datetime.utcnow().isoformat()

            logger.debug(f"   - 최종 데이터 필드: {list(new_plant_data.keys())}")

            # 6. DB 저장
            logger.debug("[Step 4] DB 저장 시작...")
            try:
                saved_plant = await self.plant_repo.create(new_plant_data)
                logger.info(f"[Step 4 완료] DB 저장 성공: {saved_plant.get('_id')}")
            except Exception as db_err:
                # 마지막 순간에 중복 에러가 났을 경우 (레이스 컨디션 방어)
                if "11000" in str(db_err):
                    logger.warning("   - [중복 에러 방어] 저장 실패(중복), 기존 데이터 재조회")
                    return await self.plant_repo.get_by_name(final_name)
                raise db_err

            # 7. 반환
            result = saved_plant.copy()
            result["is_newly_created"] = True
            result["is_favorite"] = False
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"[search_by_image 완료] 신규 생성 완료 (소요시간: {elapsed:.2f}초)")
            logger.info("=" * 50)
            
            return result
            
        except Exception as e:
            logger.error(f"[에러] 신규 생성 중 예외 발생: {e}")
            # 롤백: 저장 시도 중 에러 났을 때 부분 데이터 삭제
            try:
                await self.plant_repo.delete(new_plant_id)
            except Exception:
                pass
            raise
    # =========================================================
    # 2. 텍스트 기반 추천 (학명 조회 + 에세이)
    # =========================================================
    async def recommend_plants(self, situation: str) -> dict:
        """
        상황 기반 식물 추천.
        
        [흐름]
        1. Gemini로 상황에 맞는 식물 선정
        2. DB 조회 → 없으면 생성
        3. 추천 에세이 생성
        4. 반환
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
        target_english_name = identified.get("englishName", "")
        
        logger.info(f"[Step 1 완료] 추천 식물: {target_name} ({target_scientific_name})")
        
        # 2. DB 조회
        logger.debug("[Step 2] DB 조회 시작...")
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
            logger.info(f"[Step 3] '{target_name}' 신규 생성 시작...")
            new_plant_id = str(uuid.uuid4())
            
            try:
                task_data = self.gemini.generate_plant_data_schema(target_name, target_scientific_name)
                task_images = image_search_service.get_plant_images_tiered(
                    target_name, 
                    target_english_name, 
                    target_scientific_name
                )
                
                new_plant_data, image_urls = await asyncio.gather(task_data, task_images)
                
                logger.info(f"  - Gemini 데이터: {'성공' if new_plant_data else '실패'}")
                logger.info(f"  - 이미지: {len(image_urls)}개")

                # [추가] Fallback 데이터인지 확인 - DB 저장 금지
                if new_plant_data.get("_is_fallback"):
                    logger.error("[실패] Gemini API 실패로 기본값만 생성됨 - DB 저장 금지")
                    raise RuntimeError("식물 정보를 가져올 수 없습니다. 잠시 후 다시 시도해주세요.")

                # [추가] 최종 중복 체크 - Gemini가 이름을 교정했을 경우 대비
                final_name = new_plant_data.get('name', target_name)
                final_check = await self.plant_repo.get_by_name(final_name)
                if final_check:
                    logger.info(f"  - [중복 발견] '{final_name}'이(가) 이미 존재함. 기존 데이터 반환.")
                    plant_in_db = final_check
                else:
                    # 신규 저장
                    new_plant_data["images"] = image_urls
                    new_plant_data["imageUrl"] = image_urls[0] if image_urls else None

                    # 내부 플래그 및 Gemini가 만든 _id 삭제
                    new_plant_data.pop("_is_fallback", None)
                    if "_id" in new_plant_data:
                        del new_plant_data["_id"]
                    new_plant_data["_id"] = new_plant_id
                    new_plant_data["view_count"] = 0
                    new_plant_data["favorite_count"] = 0
                    new_plant_data["created_at"] = datetime.utcnow().isoformat()

                    plant_in_db = await self.plant_repo.create(new_plant_data)
                    logger.info(f"[Step 3 완료] DB 저장 성공: {plant_in_db.get('_id')}")
                    
            except Exception as e:
                logger.error(f"[에러] 추천 식물 생성 중 예외: {e}")
                try:
                    await self.plant_repo.delete(new_plant_id)
                    logger.info(f"[롤백] 부분 저장된 데이터 삭제: {new_plant_id}")
                except Exception:
                    pass
                raise
        else:
            logger.info(f"[Step 2 완료] DB에서 발견: {plant_in_db.get('_id')}")

        # 4. 에세이 작성
        logger.debug("[Step 4] 추천 에세이 생성 중...")
        essay = await self.gemini.generate_recommendation_essay(situation, plant_in_db)
        logger.info(f"[Step 4 완료] 에세이 길이: {len(essay)}자")
        
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
