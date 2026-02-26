"""
Gemini API 서비스 클래스 (2026 최신 SDK 버전)
- google-genai (최신 SDK) 적용
- 식물 식별, 데이터 생성, 추천 에세이 작성
- Google Search Tool (검색 그라운딩) 완벽 지원
"""
import json
import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any

# [변경] 최신 SDK로 임포트 변경
from google import genai
from google.genai import types
from PIL import Image
import io

from app.core.config import settings

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


class GeminiService:
    def __init__(self):
        # 새로운 클라이언트 객체 생성 방식
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        # 모델명 설정
        self.model_name = 'gemini-2.5-flash-lite'
        self.essay_model_name = 'gemini-3-flash-preview'
        
        logger.info("[GeminiService] 초기화 완료 (Google Gen AI SDK 적용)")

    async def _generate_content(self, parts: list, is_grounded: bool = False, is_json: bool = False) -> Optional[Any]:
        try:
            tools = [types.Tool(google_search=types.GoogleSearch())] if is_grounded else None
            mime_type = "application/json" if (is_json and not is_grounded) else "text/plain"
            
            config = types.GenerateContentConfig(
                tools=tools,
                response_mime_type=mime_type
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=parts,
                config=config
            )

            response_text = response.text
            if not is_json:
                return response_text

            try:
                if "```json" in response_text:
                    json_str = re.search(r'```json\s*([\s\S]*?)\s*```', response_text).group(1)
                elif "```" in response_text:
                    json_str = re.search(r'```\s*([\s\S]*?)\s*```', response_text).group(1)
                else:
                    json_str = response_text
                return json.loads(json_str)
            except Exception as e:
                logger.error(f"JSON Parsing Error: {e}")
                return None

        except Exception as e:
            logger.error(f"[Gemini API Error] {e}")
            return None

    async def is_plant_image(self, image_data: bytes) -> bool:
        prompt = "Determine if this image is a plant. Return JSON: {\"isPlant\": bool, \"confidence\": \"high\"|\"medium\"|\"low\"}"
        image = Image.open(io.BytesIO(image_data))
        result = await self._generate_content([prompt, image], is_json=True)
        
        if isinstance(result, list):
            result = result[0] if result else {}
        
        return result.get("isPlant", False) if result else False

    async def get_plant_name_from_image(self, image_data: bytes) -> Optional[dict]:
        if not await self.is_plant_image(image_data):
            return None
        prompt = "Identify this plant. Return JSON: {\"name\": \"..\", \"englishName\": \"..\", \"scientificName\": \"..\"}"
        image = Image.open(io.BytesIO(image_data))
        result = await self._generate_content([prompt, image], is_json=True)

        if isinstance(result, list):
            result = result[0] if result else None

        return result

    async def get_plant_name_from_text(self, user_input: str) -> Optional[dict]:
        """상황 텍스트에서 적합한 식물 추천"""
        logger.info(f"[get_plant_name_from_text] 상황: {user_input[:30]}...")

        prompt = f"""
        User situation: "{user_input}"
        Recommend 1 suitable plant for this situation.
        Return JSON: {{"name": "Korean name", "englishName": "English name", "scientificName": "Scientific name"}}
        """
        result = await self._generate_content([prompt], is_json=True)

        if isinstance(result, list):
            result = result[0] if result else None

        if result:
            logger.info(f"[get_plant_name_from_text] 추천: {result.get('name')}")
        else:
            logger.warning("[get_plant_name_from_text] 추천 실패")

        return result

    async def generate_plant_data_schema(self, name: str, scientific_name: str) -> Optional[dict]:
        """
        식물 데이터 스키마 생성 - 에러 나도 기본값으로 반환
        """
        logger.info(f"[Grounded Schema] 시작: {name}")
        
        try:
            prompt = f"""
            Search for '{name}' ({scientific_name}) and return plant data in JSON.
            [IMPORTANT: SCHEMA COMPLIANCE]
            학술명을 제외하고 무조건 한국어로 대답해라. 
            You MUST use the exact field names provided in the JSON schema.
            - Do NOT use 'native_habitat', use 'habitat'.
            - Do NOT use 'care_instructions', use 'horticulture'.
            - Ensure 'flowerInfo', 'stories', 'season', 'blooming_months', 'searchKeywords',
             'colorInfo', 'scentInfo' are ALWAYS included, even if empty.
            Instructions: Use real facts for stories, accurate flower language, and taxonomy.
            """
            
            data = await self._generate_content([prompt], is_grounded=True, is_json=True)
            
            # 데이터 정제 (fallback 값 전달)
            return self._sanitize_plant_data(data, name, scientific_name)
            
        except Exception as e:
            logger.error(f"[generate_plant_data_schema] 에러 발생: {e}")
            # 에러 나도 기본값으로 반환 (500 방지)
            return self._sanitize_plant_data(None, name, scientific_name)

    async def generate_recommendation_essay(self, user_situation: str, plant_data: dict) -> str:
        prompt = f"Role: Expert Florist(한국어로만 말을 한다). Situation: {user_situation}. Plant: {plant_data['name']}. Write a 400-char touching essay."
        result = await self._generate_content([prompt])
        return result if result else "에세이를 작성할 수 없습니다."

    def _sanitize_plant_data(self, data, fallback_name: str = "Unknown", fallback_scientific_name: str = "Unknown") -> dict:
        """
        Pydantic 모델 규격에 맞게 제미나이 응답을 강제 교정.
        어떤 에러가 나도 필수 필드는 무조건 채워서 반환.

        [중요] _is_fallback 플래그
        - True: Gemini API 실패로 기본값만 들어간 데이터 (DB 저장 금지)
        - False: 정상적으로 생성된 데이터 (DB 저장 가능)
        """
        # 데이터가 없거나 잘못된 타입이면 빈 dict로 시작
        if not data:
            data = {}

        if isinstance(data, list):
            data = data[0] if data else {}

        if not isinstance(data, dict):
            data = {}

        # ========================================
        # [핵심] Fallback 여부 판단
        # Gemini가 핵심 필드를 제대로 생성했는지 확인
        # 최소한 name, taxonomy, flowerInfo 중 하나라도 있어야 유효
        # ========================================
        has_valid_name = bool(data.get("name"))
        has_valid_taxonomy = isinstance(data.get("taxonomy"), dict) and bool(data["taxonomy"])
        has_valid_flower_info = isinstance(data.get("flowerInfo"), dict) and bool(data["flowerInfo"])
        has_valid_stories = isinstance(data.get("stories"), list) and len(data.get("stories", [])) > 0

        # 핵심 필드 중 2개 이상 있어야 유효한 데이터로 판단
        valid_field_count = sum([has_valid_name, has_valid_taxonomy, has_valid_flower_info, has_valid_stories])
        is_fallback = valid_field_count < 2

        logger.debug(f"[Sanitize] 유효 필드 수: {valid_field_count}/4 (name={has_valid_name}, taxonomy={has_valid_taxonomy}, flowerInfo={has_valid_flower_info}, stories={has_valid_stories})")
        logger.debug(f"[Sanitize] 데이터 정제 시작: {data.get('name', fallback_name)}, is_fallback={is_fallback}")

        # ========================================
        # 필수 최상위 필드
        # ========================================
        if not data.get("name"):
            data["name"] = fallback_name
        
        if not data.get("scientificName"):
            data["scientificName"] = fallback_scientific_name
        
        if not data.get("englishName"):
            data["englishName"] = fallback_name

        # ========================================
        # taxonomy (genus, species, family 필수)
        # ========================================
        if "taxonomy" not in data or not isinstance(data["taxonomy"], dict):
            data["taxonomy"] = {}
        
        t = data["taxonomy"]
        if not t.get("genus"):
            # scientificName에서 추출 시도 (예: "Rosa canina" → "Rosa")
            parts = fallback_scientific_name.split()
            t["genus"] = parts[0] if parts else "Unknown"
        if not t.get("species"):
            # scientificName에서 추출 시도 (예: "Rosa canina" → "canina")
            parts = fallback_scientific_name.split()
            t["species"] = parts[1] if len(parts) > 1 else "sp."
        if not t.get("family"):
            t["family"] = "Unknown"

        # ========================================
        # horticulture
        # ========================================
        if "horticulture" not in data or not isinstance(data["horticulture"], dict):
            data["horticulture"] = {}
        
        h = data["horticulture"]
        if not h.get("category"):
            h["category"] = "관엽식물"
        if not h.get("categoryGroup"):
            h["categoryGroup"] = "실내 인테리어"
        if not h.get("usage"):
            h["usage"] = ["관상용"]
        if not h.get("management"):
            h["management"] = "적절한 습도와 빛을 유지해주세요."
        if not h.get("preContent"):
            h["preContent"] = f"{data['name']}에 대한 정보입니다."

        # ========================================
        # flowerInfo
        # ========================================
        if "flowerInfo" not in data or not isinstance(data["flowerInfo"], dict):
            data["flowerInfo"] = {}
        
        f = data["flowerInfo"]
        if not f.get("language"):
            f["language"] = "아름다움"
        if not f.get("flowerGroup"):
            f["flowerGroup"] = "행복/즐거움"

        # ========================================
        # stories
        # ========================================
        raw_stories = data.get("stories", [])
        clean_stories = []
        if isinstance(raw_stories, list):
            for s in raw_stories:
                if isinstance(s, str):
                    clean_stories.append({"genre": "HISTORY", "content": s})
                elif isinstance(s, dict):
                    if not s.get("content"):
                        s["content"] = str(s)
                    if not s.get("genre"):
                        s["genre"] = "HISTORY"
                    clean_stories.append(s)
        
        if not clean_stories:
            clean_stories = [{"genre": "EPISODE", "content": f"{data['name']}에 대한 이야기가 준비 중입니다."}]
        data["stories"] = clean_stories

        # ========================================
        # season
        # ========================================
        raw_season = str(data.get("season", "SPRING")).upper()
        if "SPRING" in raw_season:
            data["season"] = "SPRING"
        elif "SUMMER" in raw_season:
            data["season"] = "SUMMER"
        elif "FALL" in raw_season or "AUTUMN" in raw_season:
            data["season"] = "FALL"
        elif "WINTER" in raw_season:
            data["season"] = "WINTER"
        else:
            data["season"] = "SPRING"

        # ========================================
        # colorInfo
        # ========================================
        if "colorInfo" not in data or not isinstance(data["colorInfo"], dict):
            data["colorInfo"] = {}
        
        c = data["colorInfo"]
        if not c.get("hexCodes"):
            c["hexCodes"] = ["#4CAF50"]
        if not c.get("colorLabels"):
            c["colorLabels"] = ["녹색"]
        if not c.get("colorGroup"):
            c["colorGroup"] = ["녹색/연두"]

        # ========================================
        # scentInfo
        # ========================================
        if "scentInfo" not in data or not isinstance(data["scentInfo"], dict):
            data["scentInfo"] = {}
        
        s = data["scentInfo"]
        if not s.get("scentTags"):
            s["scentTags"] = ["은은한"]
        if not s.get("scentGroup"):
            s["scentGroup"] = ["은은·차분"]

        # ========================================
        # 기타 필수 필드
        # ========================================
        if "bloomingMonths" not in data or not isinstance(data["bloomingMonths"], list):
            data["bloomingMonths"] = [4, 5, 6]
        
        if not data.get("searchKeywords"):
            data["searchKeywords"] = [data["name"], data["englishName"]]
        
        if not data.get("habitat"):
            data["habitat"] = "다양한 환경에서 자랍니다."

        # fallback 플래그 추가 (DB 저장 여부 판단용)
        data["_is_fallback"] = is_fallback

        if is_fallback:
            logger.warning("[Sanitize] Fallback 데이터 생성됨 (Gemini API 실패)")
        else:
            logger.debug("[Sanitize] 정상 데이터 정제 완료")

        return data

    async def search_plant_images(self, korean_name: str, english_name: str, scientific_name: str, count: int = 3) -> List[str]:
        prompt = f"Find 3 real image URLs for plant: {korean_name} ({scientific_name}). Return JSON: {{\"images\": [\"url1\", \"url2\"]}}"
        result = await self._generate_content([prompt], is_grounded=True, is_json=True)
        
        if isinstance(result, list):
            result = result[0] if result else {}
        
        return result.get("images", []) if result else []


# 싱글톤 인스턴스
gemini_service = GeminiService()