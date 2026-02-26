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
from typing import Optional, Any

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
        prompt = """Identify this plant. Return JSON: {"name": "..", "englishName": "..", "scientificName": ".."}
IMPORTANT: scientificName MUST be the FULL binomial name (genus + species), e.g. "Rosa canina", NOT just "Rosa"."""
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
        IMPORTANT: scientificName MUST be the FULL binomial name (genus + species), e.g. "Lavandula angustifolia", NOT just "Lavandula".
        """
        result = await self._generate_content([prompt], is_json=True)

        if isinstance(result, list):
            result = result[0] if result else None

        if result:
            logger.info(f"[get_plant_name_from_text] 추천: {result.get('name')}")
        else:
            logger.warning("[get_plant_name_from_text] 추천 실패")

        return result

    async def generate_recommendation_essay(self, user_situation: str, plant_data: dict) -> str:
        prompt = f"Role: Expert Florist(한국어로만 말을 한다). Situation: {user_situation}. Plant: {plant_data['name']}. Write a 400-char touching essay."
        result = await self._generate_content([prompt])
        return result if result else "에세이를 작성할 수 없습니다."


# 싱글톤 인스턴스
gemini_service = GeminiService()