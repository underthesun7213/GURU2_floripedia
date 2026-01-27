import httpx
import logging
from typing import List, Optional
from app.core.config import settings
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
    Google Custom Search 기반 이미지 검색 서비스
    전략: Unsplash(감성) -> Pixabay(스톡) -> iNaturalist(야생) -> Wikimedia(도감)
    검색된 이미지가 식물인지 검증하는 로직 포함
    
    [검증 모델]
    - Gemini 2.5 Flash Lite 사용 (빠르고 효율적)
    """
    
    SEARCH_API_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, gemini_svc: Optional[GeminiService] = None):
        self.api_key = settings.GOOGLE_SEARCH_API_KEY
        self.cx = settings.GOOGLE_SEARCH_ENGINE_ID
        # 싱글톤 인스턴스 사용 (메모리 효율적)
        self.gemini_service = gemini_svc or gemini_service
        logger.debug("[ImageSearchService] 초기화 완료 (검증 모델: gemini-2.5-flash-lite)")

    async def get_plant_images_tiered(
        self, 
        korean_name: str, 
        english_name: str, 
        scientific_name: str
    ) -> List[str]:
        """
        계층적 전략으로 이미지 3장을 수집합니다.
        반환값은 Pydantic Schema의 'images' 필드(List[str])에 매핑됩니다.
        """
        if not self.api_key or not self.cx:
            logger.warning("[get_plant_images_tiered] Google Search API 키 미설정")
            return []

        collected_images = []
        target_count = 3

        # 검색 티어 정의
        tiers = [
            {
                "site": "unsplash.com",
                "query": f"{english_name} {scientific_name} plant aesthetic wallpaper"
            },
            {
                "site": "pixabay.com",
                "query": f"{english_name} {scientific_name} plant"
            },
            {
                "site": "inaturalist.org",
                "query": f"{korean_name} {english_name} {scientific_name}"
            },
            {
                "site": "commons.wikimedia.org",
                "query": f"{scientific_name} plant"
            }
        ]

        # Gemini 응답 대기 시간을 고려하여 타임아웃을 넉넉하게 설정 (60초)
        timeout = httpx.Timeout(60.0, connect=10.0)
        all_candidate_images = []  # 검증 전 후보 이미지들
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            for tier in tiers:
                if len(collected_images) >= target_count:
                    break
                
                needed = target_count - len(collected_images)
                
                if needed > 0:
                    # 더 많은 후보를 가져와서 검증 실패에 대비 (needed * 3)
                    new_images = await self._fetch_images(client, tier["query"], tier["site"], min(needed * 3, 10))
                    all_candidate_images.extend(new_images)
                    
                    # 각 이미지가 식물인지 검증
                    for img_url in new_images:
                        if img_url not in collected_images:
                            # 이미지 다운로드 및 식물 검증
                            is_valid = await self._validate_plant_image(client, img_url)
                            if is_valid:
                                collected_images.append(img_url)
                                logger.info(f"[이미지 검증 통과] {img_url[:80]}...")
                                if len(collected_images) >= target_count:
                                    break
        
        logger.info(f"[이미지 수집 결과] 후보: {len(all_candidate_images)}개, 검증 통과: {len(collected_images)}개")
        
        # 검증된 이미지가 없으면, 검증 없이 첫 번째 후보 사용 (fallback)
        if not collected_images and all_candidate_images:
            logger.warning("[Fallback] 검증된 이미지 없음, 첫 번째 후보 사용")
            collected_images = all_candidate_images[:target_count]
        
        # 그래도 없으면 기본 이미지
        if not collected_images:
            logger.error("[최종 실패] 이미지를 찾을 수 없음, placeholder 반환")
            return ["https://via.placeholder.com/600x400?text=No+Image"]
            
        return collected_images[:target_count]

    async def _fetch_images(self, client, query, site, num) -> List[str]:
        """내부 헬퍼: 특정 사이트 검색"""
        try:
            params = {
                "key": self.api_key,
                "cx": self.cx,
                "q": f"{query} site:{site}",
                "searchType": "image",
                "num": num,
                "safe": "active",
                "imgSize": "large",
                "imgType": "photo"
            }
            logger.debug(f"[이미지 검색] 쿼리: {query}, 사이트: {site}")
            res = await client.get(self.SEARCH_API_URL, params=params)
            data = res.json()
            
            # API 에러 응답 확인
            if "error" in data:
                error_msg = data["error"].get("message", "Unknown error")
                error_code = data["error"].get("code", "N/A")
                logger.error(f"[이미지 검색 API 에러] 코드: {error_code}, 메시지: {error_msg}")
                return []
            
            items = data.get("items", [])
            logger.info(f"[이미지 검색 결과] {site}에서 {len(items)}개 발견")
            
            return [item["link"] for item in items if "link" in item]
        except Exception as e:
            logger.error(f"이미지 검색 에러 ({site}): {e}")
            return []

    async def _validate_plant_image(self, client: httpx.AsyncClient, image_url: str) -> bool:
        """
        이미지 URL을 다운로드하여 식물인지 검증하는 내부 헬퍼 메서드
        """
        try:
            # 이미지 다운로드 (타임아웃 15초 - Gemini 검증 시간 고려)
            response = await client.get(image_url, timeout=15.0, follow_redirects=True)
            response.raise_for_status()
            
            # Content-Type 확인
            content_type = response.headers.get("content-type", "").lower()
            if not content_type.startswith("image/"):
                logger.debug(f"[검증 실패] 이미지가 아닌 파일: {image_url[:80]}...")
                return False
            
            # 이미지 바이트 데이터로 검증
            image_data = response.content
            if len(image_data) == 0:
                logger.debug(f"[검증 실패] 빈 이미지: {image_url[:80]}...")
                return False
            
            # GeminiService를 사용하여 식물인지 검증
            is_plant = await self.gemini_service.is_plant_image(image_data)
            
            if not is_plant:
                logger.debug(f"[검증 실패] 식물이 아닌 이미지: {image_url[:80]}...")
            
            return is_plant
        except httpx.TimeoutException:
            logger.debug(f"[검증 실패] 이미지 다운로드 타임아웃: {image_url[:80]}...")
            return False
        except httpx.HTTPStatusError as e:
            logger.debug(f"[검증 실패] HTTP 에러 ({e.response.status_code}): {image_url[:80]}...")
            return False
        except Exception as e:
            logger.debug(f"[검증 실패] 예외 발생: {image_url[:80]}..., 에러: {e}")
            return False


# =========================================================
# 싱글톤 인스턴스 생성 (GeminiService 싱글톤 사용)
# =========================================================
image_search_service = ImageSearchService()