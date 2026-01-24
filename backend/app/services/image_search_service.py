import httpx
from typing import List
from app.core.config import settings

class ImageSearchService:
    """
    Google Custom Search 기반 이미지 검색 서비스
    전략: Unsplash(감성) -> Pixabay(스톡) -> iNaturalist(야생) -> Wikimedia(도감)
    """
    
    SEARCH_API_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self):
        self.api_key = settings.GOOGLE_SEARCH_API_KEY
        self.cx = settings.GOOGLE_SEARCH_ENGINE_ID

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
            print("Google Search API 키 미설정")
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

        async with httpx.AsyncClient(timeout=10.0) as client:
            for tier in tiers:
                if len(collected_images) >= target_count:
                    break
                
                needed = target_count - len(collected_images)
                
                if needed > 0:
                    new_images = await self._fetch_images(client, tier["query"], tier["site"], needed)
                    
                    for img in new_images:
                        if img not in collected_images:
                            collected_images.append(img)
        
        # 실패 시 기본 이미지
        if not collected_images:
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
            res = await client.get(self.SEARCH_API_URL, params=params)
            data = res.json()
            return [item["link"] for item in data.get("items", []) if "link" in item]
        except Exception as e:
            print(f"이미지 검색 에러 ({site}): {e}")
            return []

image_search_service = ImageSearchService()