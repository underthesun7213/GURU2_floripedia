"""
이미지 검색 서비스 (2026 최신 SDK 대응)
- Gemini 검색 그라운딩 기반 이미지 URL 검색
- 기존 Custom Search API 의존성 완전 제거
"""
import logging
from typing import List, Optional
# [참고] GeminiService가 이미 최신 SDK로 수정되었다고 가정합니다.
from app.services.gemini_service import GeminiService, gemini_service

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


class ImageSearchService:
    """
    Gemini 검색 그라운딩 기반 이미지 검색 서비스

    [변경 사항]
    - Google Custom Search API 호출 로직 제거 (403 에러 원인 차단)
    - Gemini의 google_search 도구를 통해 실시간 웹 이미지 경로 획득
    """

    def __init__(self, gemini_svc: Optional[GeminiService] = None):
        self.gemini_service = gemini_svc or gemini_service
        logger.debug("[ImageSearchService] 초기화 완료 (Gemini 그라운딩 기반)")

    async def get_plant_images_tiered(
        self,
        korean_name: str,
        english_name: str,
        scientific_name: str
    ) -> List[str]:
        """
        Gemini 검색 그라운딩을 사용하여 이미지 URL 검색

        [흐름]
        1. GeminiService의 search_plant_images 호출 (내부적으로 최신 SDK 그라운딩 사용)
        2. 검색 실패 시 사용자 경험을 위해 Placeholder 이미지 반환
        """
        logger.info(f"[get_plant_images_tiered] 시작: {korean_name} ({scientific_name})")

        target_count = 3

        try:
            # Gemini 그라운딩을 통해 실시간 웹 검색 기반 이미지 URL 수집
            images = await self.gemini_service.search_plant_images(
                korean_name=korean_name,
                english_name=english_name,
                scientific_name=scientific_name,
                count=target_count
            )

            if images and len(images) > 0:
                logger.info(f"[get_plant_images_tiered] 성공: {len(images)}개 이미지 확보")
                return images[:target_count]

        except Exception as e:
            logger.error(f"[get_plant_images_tiered] 에러 발생: {e}")

        # Fallback: 검색 결과가 없거나 에러 발생 시
        logger.warning("[get_plant_images_tiered] 유효한 이미지를 찾지 못함, placeholder 반환")
        return ["https://via.placeholder.com/600x400?text=Flower+Image+Coming+Soon"]


# =========================================================
# 싱글톤 인스턴스 생성
# =========================================================
image_search_service = ImageSearchService()