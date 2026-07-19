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

# ==========================================================
# 구조화 출력(Structured Output) 스키마
# google-genai response_schema로 모델이 스키마에 맞는 JSON을 보장하게 한다
# → 마크다운 펜스 벗기기·파싱 실패·리스트/객체 흔들림 제거.
# (주의: Google Search 그라운딩과는 동시 사용 불가 → grounded 경로에는 미적용)
# ==========================================================
PLANT_IDENTITY_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "name": types.Schema(type=types.Type.STRING),
        "englishName": types.Schema(type=types.Type.STRING),
        "scientificName": types.Schema(type=types.Type.STRING),
    },
    required=["name", "scientificName"],
)

IS_PLANT_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "isPlant": types.Schema(type=types.Type.BOOLEAN),
        "confidence": types.Schema(
            type=types.Type.STRING, enum=["high", "medium", "low"]
        ),
    },
    required=["isPlant"],
)

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
        
        # 모델명 설정 (config.py 중앙 관리)
        self.basic_model = settings.GEMINI_BASIC_MODEL
        self.essay_model = settings.GEMINI_ESSAY_MODEL
        
        logger.info("[GeminiService] 초기화 완료 (Google Gen AI SDK 적용)")

    async def _generate_content(self, parts: list, is_grounded: bool = False, is_json: bool = False, model: str = None, response_schema: Any = None) -> Optional[Any]:
        try:
            tools = [types.Tool(google_search=types.GoogleSearch())] if is_grounded else None
            use_json = is_json and not is_grounded
            mime_type = "application/json" if use_json else "text/plain"

            config = types.GenerateContentConfig(
                tools=tools,
                response_mime_type=mime_type,
                # 그라운딩과 동시 불가하므로 JSON 모드일 때만 스키마 강제
                response_schema=response_schema if use_json else None,
            )

            response = self.client.models.generate_content(
                model=model or self.basic_model,
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
        result = await self._generate_content(
            [prompt, image], is_json=True, response_schema=IS_PLANT_SCHEMA
        )
        
        if isinstance(result, list):
            result = result[0] if result else {}
        
        return result.get("isPlant", False) if result else False

    async def get_plant_name_from_image(self, image_data: bytes) -> Optional[dict]:
        if not await self.is_plant_image(image_data):
            return None
        prompt = """Identify this plant. Return JSON: {"name": "..", "englishName": "..", "scientificName": ".."}
IMPORTANT: scientificName MUST be the FULL binomial name (genus + species), e.g. "Rosa canina", NOT just "Rosa"."""
        image = Image.open(io.BytesIO(image_data))
        result = await self._generate_content(
            [prompt, image], is_json=True, response_schema=PLANT_IDENTITY_SCHEMA
        )

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
        result = await self._generate_content(
            [prompt], is_json=True, response_schema=PLANT_IDENTITY_SCHEMA
        )

        if isinstance(result, list):
            result = result[0] if result else None

        if result:
            logger.info(f"[get_plant_name_from_text] 추천: {result.get('name')}")
        else:
            logger.warning("[get_plant_name_from_text] 추천 실패")

        return result

    async def generate_recommendation_essay(self, user_situation: str, plant_data: dict) -> str:
        flower_language = (plant_data.get("flowerInfo") or {}).get("language") or ""
        flower_hint = f" (꽃말: {flower_language})" if flower_language else ""
        prompt = f"""사용자 상황: "{user_situation}"
추천 식물: {plant_data['name']}{flower_hint}

위 상황의 사용자에게 이 식물을 추천하는 글을 400자 내외의 한국어(습니다체)로 작성하라.

규칙:
- 인사말·자기소개·화자 언급 금지("안녕하세요", "플로리스트입니다" 등 어떤 인격도 드러내지 않는다). 첫 문장부터 바로 본론으로 시작한다.
- 첫 문단에 이 식물을 추천한다는 명확한 문장(예: "'{plant_data['name']}'을 추천합니다")을 넣는다.
- 꽃말과 식물의 특징을 사용자의 상황과 자연스럽게 연결하고, 따뜻한 마무리로 끝맺는다.
- 본문만 출력한다. 제목·머리말·이모지·마크다운을 쓰지 않는다."""
        result = await self._generate_content([prompt], model=self.essay_model)
        return result if result else "에세이를 작성할 수 없습니다."


# 싱글톤 인스턴스
gemini_service = GeminiService()