"""
사용자 관련 비즈니스 로직 서비스.
프로필 관리, 찜 기능, 계정 관리 등 사용자 관련 핵심 로직을 처리합니다.
- 디버그 로깅 포함
- 찜 토글 시 트랜잭션 처리 (롤백 포함)
"""
import logging
from typing import List, Optional

from app.repositories import UserRepository, PlantRepository
from app.services.firebase_service import firebase_storage

# 로거 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(handler)


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
        logger.debug(f"[get_profile] user_id={user_id}")
        
        user = await self.user_repo.get_by_id(user_id)

        if not user:
            logger.warning(f"[get_profile] 사용자를 찾을 수 없음: {user_id}")
            return None

        if not user.get("isActive", True):
            logger.warning(f"[get_profile] 탈퇴한 계정: {user_id}")
            raise ValueError("탈퇴한 계정입니다")

        logger.debug(f"[get_profile] 조회 성공: {user.get('nickname', 'Unknown')}")
        return user

    async def update_profile(self, user_id: str, update_data: dict) -> Optional[dict]:
        """프로필 정보 수정."""
        logger.info(f"[update_profile] user_id={user_id}, fields={list(update_data.keys())}")
        
        if not update_data:
            logger.warning("[update_profile] 업데이트 데이터 없음")
            return None
            
        result = await self.user_repo.update(user_id, update_data)
        
        if result:
            logger.info(f"[update_profile] 업데이트 성공")
        else:
            logger.warning(f"[update_profile] 업데이트 실패")
            
        return result

    async def upload_profile_image(
        self, user_id: str, file_data: bytes, content_type: str
    ) -> dict:
        """프로필 이미지 업로드 및 URL 저장."""
        logger.info(f"[upload_profile_image] user_id={user_id}, size={len(file_data):,} bytes")
        
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            logger.error(f"[upload_profile_image] 유저를 찾을 수 없음: {user_id}")
            raise ValueError("유저를 찾을 수 없습니다")

        try:
            # Firebase Storage 업로드
            logger.debug("[upload_profile_image] Firebase Storage 업로드 시작...")
            image_url = firebase_storage.upload_profile_image(
                user_id=user_id,
                file_data=file_data,
                content_type=content_type,
            )
            logger.info(f"[upload_profile_image] 업로드 성공: {image_url[:50]}...")
            
            # DB 업데이트
            updated_user = await self.user_repo.update(
                user_id, {"profileImageUrl": image_url}
            )
            logger.info("[upload_profile_image] DB 업데이트 완료")
            
            return updated_user

        except Exception as e:
            logger.error(f"[upload_profile_image] 실패: {e}")
            raise RuntimeError(f"이미지 업로드 실패: {str(e)}")

    # ==========================================
    # 찜(꽃갈피) 기능
    # ==========================================

    async def toggle_favorite(self, user_id: str, plant_id: str) -> dict:
        """
        식물 찜하기/취소 토글.
        
        [트랜잭션 처리]
        1. User의 favoritePlantIds 업데이트
        2. Plant의 favorite_count 업데이트
        에러 발생 시 롤백 처리
        """
        logger.info("=" * 50)
        logger.info(f"[toggle_favorite] 시작: user={user_id}, plant={plant_id}")
        
        # 1. 유효성 검사
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            logger.error(f"[toggle_favorite] 유저를 찾을 수 없음: {user_id}")
            raise ValueError("유저를 찾을 수 없습니다")

        plant = await self.plant_repo.get_by_id(plant_id)
        if not plant:
            logger.error(f"[toggle_favorite] 식물을 찾을 수 없음: {plant_id}")
            raise ValueError("식물을 찾을 수 없습니다")

        current_favorites = user.get("favoritePlantIds", [])
        is_currently_favorite = plant_id in current_favorites
        
        logger.debug(f"  - 현재 찜 상태: {'찜됨' if is_currently_favorite else '안됨'}")
        logger.debug(f"  - 현재 찜 개수: {len(current_favorites)}개")

        if is_currently_favorite:
            # ===== 찜 취소 =====
            logger.info("[toggle_favorite] 찜 취소 처리...")
            
            try:
                # Step 1: User에서 제거
                await self.user_repo.remove_favorite(user_id, plant_id)
                logger.debug("  - User favoritePlantIds에서 제거 완료")
                
                # Step 2: Plant favorite_count 감소
                try:
                    await self.plant_repo.increment_favorite_count(plant_id, delta=-1)
                    logger.debug("  - Plant favorite_count 감소 완료")
                except Exception as e:
                    # 롤백: User에 다시 추가
                    logger.error(f"  - Plant 업데이트 실패, 롤백 시작: {e}")
                    await self.user_repo.add_favorite(user_id, plant_id)
                    logger.info("  - 롤백 완료: User에 다시 추가됨")
                    raise
                
                logger.info("[toggle_favorite] 찜 취소 완료")
                return {"isFavorite": False, "message": "찜이 취소되었습니다"}
                
            except Exception as e:
                logger.error(f"[toggle_favorite] 찜 취소 실패: {e}")
                raise
        else:
            # ===== 찜 추가 =====
            logger.info("[toggle_favorite] 찜 추가 처리...")
            
            try:
                # Step 1: User에 추가
                await self.user_repo.add_favorite(user_id, plant_id)
                logger.debug("  - User favoritePlantIds에 추가 완료")
                
                # Step 2: Plant favorite_count 증가
                try:
                    await self.plant_repo.increment_favorite_count(plant_id, delta=1)
                    logger.debug("  - Plant favorite_count 증가 완료")
                except Exception as e:
                    # 롤백: User에서 제거
                    logger.error(f"  - Plant 업데이트 실패, 롤백 시작: {e}")
                    await self.user_repo.remove_favorite(user_id, plant_id)
                    logger.info("  - 롤백 완료: User에서 제거됨")
                    raise
                
                logger.info("[toggle_favorite] 찜 추가 완료")
                return {"isFavorite": True, "message": "찜 목록에 추가되었습니다"}
                
            except Exception as e:
                logger.error(f"[toggle_favorite] 찜 추가 실패: {e}")
                raise

    async def get_favorites(
        self,
        user_id: str,
        # 필터 파라미터 (main /plants와 동일 - 모두 단일 선택)
        season: Optional[str] = None,
        category_group: Optional[str] = None,
        color_group: Optional[str] = None,
        scent_group: Optional[str] = None,
        flower_group: Optional[str] = None,
        keyword: Optional[str] = None,
        # 페이지네이션 & 정렬
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "name",
        sort_order: str = "asc",
    ) -> List[dict]:
        """
        찜 목록 조회 - 찜한 식물 내에서 main plants 필터링 로직 적용
        """
        logger.debug(f"[get_favorites] user={user_id}, sort_by={sort_by}, sort_order={sort_order}")
        logger.debug(f"[get_favorites] filters: season={season}, category_group={category_group}, color_group={color_group}, scent_group={scent_group}, flower_group={flower_group}, keyword={keyword}")

        favorite_ids = await self.user_repo.get_favorites(user_id)

        if not favorite_ids:
            logger.debug("[get_favorites] 찜 목록 없음")
            return []

        logger.debug(f"[get_favorites] 찜 ID 개수: {len(favorite_ids)}개")

        sort_order_int = -1 if sort_order == "desc" else 1

        # main /plants와 동일한 로직으로 찜 목록 내에서 필터링
        plants = await self.plant_repo.get_list(
            plant_ids=favorite_ids,
            season=season,
            category_group=category_group,
            color_group=color_group,
            scent_group=scent_group,
            flower_group=flower_group,
            keyword=keyword,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order_int
        )

        logger.debug(f"[get_favorites] 결과: {len(plants)}개")
        return plants

    async def get_favorites_count(self, user_id: str) -> int:
        """찜 목록 개수 조회."""
        favorite_ids = await self.user_repo.get_favorites(user_id)
        count = len(favorite_ids)
        logger.debug(f"[get_favorites_count] user={user_id}, count={count}")
        return count

    # ==========================================
    # 계정 관리
    # ==========================================

    async def delete_account(self, user_id: str) -> bool:
        """회원 탈퇴 (Soft Delete)."""
        logger.info(f"[delete_account] 회원 탈퇴 요청: {user_id}")
        
        result = await self.user_repo.soft_delete(user_id)
        
        if result:
            logger.info(f"[delete_account] 탈퇴 완료: {user_id}")
        else:
            logger.warning(f"[delete_account] 탈퇴 실패: {user_id}")
            
        return result
