"""
Gemini API 서비스 클래스
- 식물 식별, 데이터 생성, 추천 에세이 작성
- 데이터 정제(Sanitization) 로직 포함
- Google Search Tool (검색 그라운딩) 적용 - 2026 API
"""
import json
import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any

import google.generativeai as genai
from google.generativeai.types import Tool
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

# Gemini API 설정
genai.configure(api_key=settings.GEMINI_API_KEY)


class GeminiService:
    """
    Gemini API 서비스 클래스
    - 데이터 정제(Sanitization) 로직 포함 (500 에러 및 데이터 불일치 방지용)
    - Google Search Tool (2026 API)로 검색 그라운딩 적용 (할루시네이션 방지)
    """

    def __init__(self):
        # =========================================================
        # 1. 기본 모델 (JSON 응답용 - 이미지 식별, 검증 등)
        #    - gemini-2.5-flash-lite: 빠르고 가벼운 모델
        # =========================================================
        self.model = genai.GenerativeModel(model_name='gemini-2.5-flash-lite')
        
        # =========================================================
        # 2. 검색 그라운딩 모델 (식물 데이터 생성용)
        #    - gemini-2.5-flash-lite + Google Search Tool (2026 API)
        #    - 최신/희귀 식물 정보도 정확하게 생성
        # =========================================================
        self.grounded_model = genai.GenerativeModel(
            model_name='gemini-2.5-flash-lite',
            tools=[{"google_search_retrieval": {}}]
        )
        
        # =========================================================
        # 3. 에세이 작성 모델 (추천 에세이 전용)
        #    - gemini-3-flash-preview: 감성적 글쓰기에 최적화
        # =========================================================
        self.essay_model = genai.GenerativeModel(model_name='gemini-3-flash-preview')
        
        logger.info("[GeminiService] 초기화 완료")
        logger.info("  - 기본 모델: gemini-2.5-flash-lite")
        logger.info("  - 검색 그라운딩 모델: gemini-2.5-flash-lite + Google Search Tool (2026)")
        logger.info("  - 에세이 작성 모델: gemini-3-flash-preview")

    async def _generate_json_content(self, parts: list, prompt_text: str = "") -> Optional[dict]:
        """Gemini API 호출 및 JSON 파싱 (기본 모델)"""
        start_time = datetime.now()
        try:
            logger.debug("[Gemini] API 호출 시작...")
            response = await self.model.generate_content_async(
                parts,
                generation_config={"response_mime_type": "application/json"}
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.debug(f"[Gemini] API 응답 수신 (소요시간: {elapsed:.2f}초)")
            
            result = json.loads(response.text)
            logger.debug("[Gemini] JSON 파싱 성공")
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"[Gemini] JSON 파싱 실패: {e}")
            return self._parse_json_fallback(prompt_text)
        except Exception as e:
            logger.error(f"[Gemini] API 호출 실패: {e}")
            return self._parse_json_fallback(prompt_text)

    async def _generate_grounded_json_content(self, prompt: str) -> Optional[dict]:
        """
        검색 그라운딩 모델을 사용한 JSON 생성
        
        [흐름]
        1. 검색 그라운딩 모델로 텍스트 응답 생성 (실시간 구글 검색 활용)
        2. 응답에서 JSON 추출 및 파싱
        """
        start_time = datetime.now()
        try:
            logger.debug("[Gemini Grounded] 검색 그라운딩 API 호출 시작...")
            
            # 검색 그라운딩 모델은 response_mime_type을 지원하지 않을 수 있으므로
            # 텍스트 응답을 받아서 JSON으로 파싱
            response = await self.grounded_model.generate_content_async(prompt)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.debug(f"[Gemini Grounded] API 응답 수신 (소요시간: {elapsed:.2f}초)")
            
            # 검색 그라운딩 메타데이터 로깅
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                    metadata = candidate.grounding_metadata
                    if hasattr(metadata, 'search_entry_point'):
                        logger.info("[Gemini Grounded] 검색 그라운딩 활성화됨")
                    if hasattr(metadata, 'grounding_chunks') and metadata.grounding_chunks:
                        logger.info(f"[Gemini Grounded] 참조 소스: {len(metadata.grounding_chunks)}개")
            
            # 응답 텍스트에서 JSON 추출
            response_text = response.text.strip()
            logger.debug(f"[Gemini Grounded] 응답 길이: {len(response_text)}자")
            
            # JSON 블록 추출 (```json ... ``` 형식 처리)
            if "```json" in response_text:
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
                if json_match:
                    response_text = json_match.group(1)
            elif "```" in response_text:
                json_match = re.search(r'```\s*([\s\S]*?)\s*```', response_text)
                if json_match:
                    response_text = json_match.group(1)
            
            result = json.loads(response_text)
            logger.debug("[Gemini Grounded] JSON 파싱 성공")
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"[Gemini Grounded] JSON 파싱 실패: {e}")
            logger.debug(f"[Gemini Grounded] 원본 응답: {response_text[:500] if response_text else 'None'}...")
            return None
        except Exception as e:
            logger.error(f"[Gemini Grounded] API 호출 실패: {e}")
            return None

    # =========================================================
    # 데이터 정제 (Sanitizer)
    # Gemini가 제멋대로 보낸 데이터를 규격에 맞게 강제 변환
    # =========================================================
    def _sanitize_plant_data(self, data: dict) -> dict:
        """Gemini 응답 데이터 정제"""
        if not data:
            logger.warning("[Sanitizer] 빈 데이터 수신")
            return data
            
        logger.debug(f"[Sanitizer] 정제 시작: {data.get('name', 'Unknown')}")

        # -------------------------------------------------------
        # 1. Season (한글/영어 -> ENUM 변환)
        # -------------------------------------------------------
        season_map = {
            "봄": "SPRING", "여름": "SUMMER", "가을": "FALL", "겨울": "WINTER",
            "Spring": "SPRING", "Summer": "SUMMER", "Fall": "FALL", "Winter": "WINTER"
        }
        if "season" in data:
            val = data["season"]
            if val in season_map:
                data["season"] = season_map[val]
                logger.debug(f"  - season 변환: {val} -> {data['season']}")
            elif val not in ["SPRING", "SUMMER", "FALL", "WINTER"]:
                data["season"] = "SPRING"
                logger.debug(f"  - season 기본값 적용: {val} -> SPRING")

        # -------------------------------------------------------
        # 2. Stories (문자열 -> 객체 변환)
        # -------------------------------------------------------
        if "stories" in data and isinstance(data["stories"], list):
            new_stories = []
            for item in data["stories"]:
                if isinstance(item, str):
                    new_stories.append({"genre": "EPISODE", "content": item})
                elif isinstance(item, dict):
                    if "genre" in item:
                        item["genre"] = item["genre"].upper()
                        if item["genre"] not in ["HISTORY", "MYTH", "SCIENCE", "EPISODE"]:
                            item["genre"] = "EPISODE"
                    new_stories.append(item)
            data["stories"] = new_stories
            logger.debug(f"  - stories 정제: {len(new_stories)}개")

        # -------------------------------------------------------
        # 3. 카테고리/그룹 강제 매핑
        # -------------------------------------------------------
        
        # (1) 식물 분류 그룹 (categoryGroup)
        valid_cat_groups = ['꽃과 풀', '나무와 조경', '실내 인테리어', '텃밭과 정원']
        horti = data.get("horticulture", {})
        if horti and "categoryGroup" in horti:
            val = horti["categoryGroup"]
            if val not in valid_cat_groups:
                if "나무" in val or "조경" in val:
                    horti["categoryGroup"] = "나무와 조경"
                elif "실내" in val:
                    horti["categoryGroup"] = "실내 인테리어"
                elif "채소" in val or "텃밭" in val:
                    horti["categoryGroup"] = "텃밭과 정원"
                else:
                    horti["categoryGroup"] = "꽃과 풀"
                logger.debug(f"  - categoryGroup 변환: {val} -> {horti['categoryGroup']}")

        # (2) 꽃말 감성 그룹 (flowerGroup)
        valid_flower_groups = ['사랑/고백', '위로/슬픔', '감사/존경', '이별/그리움', '행복/즐거움']
        flower_info = data.get("flowerInfo", {})
        if flower_info and "flowerGroup" in flower_info:
            val = flower_info["flowerGroup"]
            if val not in valid_flower_groups:
                flower_info["flowerGroup"] = "행복/즐거움"
                logger.debug(f"  - flowerGroup 변환: {val} -> 행복/즐거움")

        # (3) 향기 그룹 (scentGroup)
        valid_scent_groups = ['달콤·화사', '싱그러운·시원', '은은·차분', '무향']
        scent_info = data.get("scentInfo", {})
        if scent_info and "scentGroup" in scent_info:
            origin_vals = scent_info["scentGroup"]
            if not isinstance(origin_vals, list):
                origin_vals = [origin_vals]
            
            cleaned_scents = []
            for v in origin_vals:
                if v in valid_scent_groups:
                    cleaned_scents.append(v)
                else:
                    if v in ["SWEET", "FLORAL"]:
                        cleaned_scents.append("달콤·화사")
                    elif v in ["FRESH", "COOL", "GREEN"]:
                        cleaned_scents.append("싱그러운·시원")
                    elif v in ["SOFT", "CALM", "WOODY"]:
                        cleaned_scents.append("은은·차분")
                    else:
                        cleaned_scents.append("은은·차분")
            
            scent_info["scentGroup"] = list(set(cleaned_scents)) if cleaned_scents else ["무향"]

        # (4) 색상 그룹 (colorGroup)
        valid_color_groups = ['백색/미색', '노랑/주황', '빨강/분홍', '푸른색', '갈색/검정']
        color_info = data.get("colorInfo", {})
        cleaned_colors = []
        
        if color_info and "colorGroup" in color_info:
            origin_vals = color_info["colorGroup"]
            if not isinstance(origin_vals, list):
                origin_vals = [origin_vals]
            
            for v in origin_vals:
                if v in valid_color_groups:
                    cleaned_colors.append(v)
                else:
                    if v == "WHITE" or "백" in str(v):
                        cleaned_colors.append("백색/미색")
                    elif v in ["YELLOW", "ORANGE"] or "노랑" in str(v):
                        cleaned_colors.append("노랑/주황")
                    elif v in ["RED", "PINK", "MAGENTA"] or "붉" in str(v):
                        cleaned_colors.append("빨강/분홍")
                    elif v in ["BLUE", "SKY", "PURPLE", "VIOLET"] or "푸" in str(v):
                        cleaned_colors.append("푸른색")
                    elif v in ["BROWN", "BLACK"] or "검" in str(v):
                        cleaned_colors.append("갈색/검정")
                    else:
                        cleaned_colors.append("백색/미색")
            
            color_info["colorGroup"] = list(set(cleaned_colors)) if cleaned_colors else ["백색/미색"]

        # (5) 세부 색상 라벨 (colorLabels)
        valid_labels = ['백색', '연두', '초록', '노랑', '빨강', '분홍', '연보라', '보라', '파랑', '하늘', '살구', '갈색', '검정', '다홍', '주황', '미색']
        if color_info and "colorLabels" in color_info:
            origin_labels = color_info["colorLabels"]
            if not isinstance(origin_labels, list):
                origin_labels = [origin_labels]
            filtered = [l for l in origin_labels if l in valid_labels]
            if not filtered and cleaned_colors:
                if "백색/미색" in cleaned_colors:
                    filtered.append("백색")
                elif "노랑/주황" in cleaned_colors:
                    filtered.append("노랑")
                else:
                    filtered.append("초록")
            color_info["colorLabels"] = filtered

        # 4. _id 제거
        if "_id" in data:
            del data["_id"]
            
        logger.debug("[Sanitizer] 정제 완료")
        return data

    # =========================================================
    # 이미지 검증
    # =========================================================
    async def is_plant_image(self, image_data: bytes) -> bool:
        """이미지가 식물인지 검증"""
        logger.debug(f"[is_plant_image] 이미지 검증 시작 ({len(image_data):,} bytes)")
        
        prompt = """
        Analyze this image and determine if it contains a plant (flower, tree, grass, or any botanical subject).
        Return ONLY a JSON object with this schema:
        {
            "isPlant": true or false,
            "confidence": "high" or "medium" or "low"
        }
        """
        try:
            image = Image.open(io.BytesIO(image_data))
            result = await self._generate_json_content([prompt, image])
            
            if not result:
                logger.warning("[is_plant_image] 결과 없음")
                return False
            
            is_plant = result.get("isPlant", False)
            confidence = result.get("confidence", "low")
            
            logger.info(f"[is_plant_image] 결과: isPlant={is_plant}, confidence={confidence}")
            
            # high 또는 medium confidence일 때만 True 반환
            return is_plant and confidence in ["high", "medium"]
            
        except Exception as e:
            logger.error(f"[is_plant_image] 에러: {e}")
            return False

    # =========================================================
    # 이미지에서 식물 식별
    # =========================================================
    async def get_plant_name_from_image(self, image_data: bytes) -> Optional[dict]:
        """이미지에서 식물 이름 추출 (검증 포함)"""
        logger.info(f"[get_plant_name_from_image] 시작 ({len(image_data):,} bytes)")
        
        # 1. 식물인지 먼저 검증
        is_plant = await self.is_plant_image(image_data)
        if not is_plant:
            logger.warning("[get_plant_name_from_image] 식물이 아닌 이미지")
            return None
        
        # 2. 식물이면 식별 진행
        prompt = """
        Analyze this image and identify the plant.
        Return ONLY a JSON object with this schema:
        {
            "name": "Korean common name",
            "englishName": "English common name",
            "scientificName": "Scientific name"
        }
        If unidentified, return null.
        """
        try:
            image = Image.open(io.BytesIO(image_data))
            result = await self._generate_json_content([prompt, image])
            
            if result:
                logger.info(f"[get_plant_name_from_image] 식별 성공: {result.get('name')}")
            else:
                logger.warning("[get_plant_name_from_image] 식별 실패")
                
            return result
            
        except Exception as e:
            logger.error(f"[get_plant_name_from_image] 에러: {e}")
            return None

    # =========================================================
    # 텍스트에서 식물 추천
    # =========================================================
    async def get_plant_name_from_text(self, user_input: str) -> Optional[dict]:
        """상황 텍스트에서 식물 추천"""
        logger.info(f"[get_plant_name_from_text] 상황: {user_input[:30]}...")
        
        prompt = f"""
        User Situation: "{user_input}"
        Recommend 1 suitable plant.
        Return ONLY a JSON object:
        {{
            "name": "Korean name",
            "englishName": "English name",
            "scientificName": "Scientific name"
        }}
        """
        result = await self._generate_json_content([prompt])
        
        if result:
            logger.info(f"[get_plant_name_from_text] 추천: {result.get('name')}")
        else:
            logger.warning("[get_plant_name_from_text] 추천 실패")
            
        return result

    # =========================================================
    # 식물 데이터 스키마 생성 (검색 그라운딩 적용)
    # =========================================================
    async def generate_plant_data_schema(self, name: str, scientific_name: str) -> Optional[dict]:
        """
        식물 데이터 전체 스키마 생성
        
        [검색 그라운딩]
        - Google Search Tool (2026 API)을 사용하여 실시간 웹 검색 수행
        - 최신 품종, 희귀 식물도 정확한 정보 제공
        - 할루시네이션(거짓 정보) 방지
        """
        start_time = datetime.now()
        logger.info("=" * 60)
        logger.info(f"[generate_plant_data_schema] 시작: {name} ({scientific_name})")
        logger.info("[generate_plant_data_schema] 검색 그라운딩 활성화됨")
        
        # 검색 그라운딩을 활용하는 프롬프트
        prompt = f"""
        Use Google Search to find the most accurate and up-to-date information about the plant '{name}' (Scientific Name: {scientific_name}).
        
        [SEARCH INSTRUCTIONS]
        - Search for accurate taxonomy (genus, species, family)
        - Verify the actual flowering months and seasons
        - Find real historical or cultural stories about this plant
        - Confirm the flower language (꽃말) in Korean culture
        - Check the plant's characteristics: color, scent, habitat
        
        [OUTPUT INSTRUCTIONS]
        1. Return ONLY a valid JSON object (no markdown, no explanation).
        2. Generate 2 or more stories based on REAL facts found via search.
           - Allowed Genres: HISTORY, MYTH, SCIENCE, EPISODE
           - Each story should be factually grounded.
        3. season must be one of: SPRING, SUMMER, FALL, WINTER
        4. Select values ONLY from these lists:
           - horticulture.categoryGroup: ['꽃과 풀', '나무와 조경', '실내 인테리어', '텃밭과 정원']
           - flowerInfo.flowerGroup: ['사랑/고백', '위로/슬픔', '감사/존경', '이별/그리움', '행복/즐거움']
           - scentInfo.scentGroup (List): ['달콤·화사', '싱그러운·시원', '은은·차분', '무향']
           - colorInfo.colorGroup (List): ['백색/미색', '노랑/주황', '빨강/분홍', '푸른색', '갈색/검정']
           - colorInfo.colorLabels (List): ['백색', '연두', '초록', '노랑', '빨강', '분홍', '연보라', '보라', '파랑', '하늘', '살구', '갈색', '검정', '다홍', '주황', '미색']
        
        [JSON STRUCTURE]
        {{
             "name": "{name}",
             "scientificName": "{scientific_name}",
             "englishName": "English common name from search",
             "isRepresentative": false,
             "taxonomy": {{ 
                "genus": "Genus from search", 
                "species": "Species from search", 
                "family": "Family in Korean from search" 
             }},
             "horticulture": {{ 
                "category": "Specific category", 
                "categoryGroup": "Pick one from the list above", 
                "usage": ["usage1", "usage2"], 
                "management": "Care instructions from search", 
                "preContent": "2-3 sentence description in Korean" 
             }},
             "habitat": "Natural habitat from search",
             "stories": [ 
                 {{
                    "genre": "HISTORY or MYTH or SCIENCE or EPISODE", 
                    "content": "Factual story in Korean (2-3 sentences)"
                 }},
                 {{
                    "genre": "HISTORY or MYTH or SCIENCE or EPISODE", 
                    "content": "Another factual story in Korean (2-3 sentences)"
                 }}
             ],
             "season": "SPRING or SUMMER or FALL or WINTER",
             "bloomingMonths": [1, 2, 3],
             "searchKeywords": ["keyword1", "keyword2", "keyword3"],
             "popularity_score": 0,
             "colorInfo": {{ 
                "hexCodes": ["#FFFFFF"], 
                "colorLabels": ["백색"], 
                "colorGroup": ["백색/미색"] 
             }},
             "scentInfo": {{ 
                "scentTags": ["향기 특성"], 
                "scentGroup": ["은은·차분"] 
             }},
             "flowerInfo": {{ 
                "language": "꽃말 from search", 
                "flowerGroup": "Pick one from the list above" 
             }},
             "images": [],
             "imageUrl": null
        }}
        """
        
        # 검색 그라운딩 모델 사용
        data = await self._generate_grounded_json_content(prompt)
        
        # Fallback: 검색 그라운딩 실패 시 기본 모델 사용
        if not data:
            logger.warning("[generate_plant_data_schema] 검색 그라운딩 실패, 기본 모델로 재시도...")
            data = await self._generate_json_content([prompt])
        
        if data:
            # 정제 로직 실행
            clean_data = self._sanitize_plant_data(data)
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"[generate_plant_data_schema] 완료 (소요시간: {elapsed:.2f}초)")
            logger.info("=" * 60)
            return clean_data
        else:
            logger.error("[generate_plant_data_schema] 데이터 생성 실패")
            logger.info("=" * 60)
            return None

    # =========================================================
    # 추천 에세이 생성
    # =========================================================
    async def generate_recommendation_essay(self, user_situation: str, plant_data: dict) -> str:
        """
        추천 에세이 작성
        
        [모델]
        - gemini-3-flash-preview 사용 (감성적 글쓰기에 최적화)
        """
        logger.debug(f"[generate_recommendation_essay] 식물: {plant_data.get('name')}")
        logger.debug("[generate_recommendation_essay] 모델: gemini-3-flash-preview")
        
        flower_lang = plant_data.get('flowerInfo', {}).get('language', '아름다움')
        pre_content = plant_data.get('horticulture', {}).get('preContent', '')
        
        prompt = f"""
        Role: 30-year Veteran Florist & Essayist.
        Task: Write a touching, comforting essay (around 400 characters).
        Tone: Warm, gentle, polite Korean (~해요 style).
        
        User Situation: "{user_situation}"
        Plant: {plant_data['name']} (Flower Language: {flower_lang})
        Feature: {pre_content}
        
        Output: Only the essay text.
        """
        try:
            # 에세이 전용 모델 사용
            response = await self.essay_model.generate_content_async(prompt)
            essay = response.text.strip()
            logger.info(f"[generate_recommendation_essay] 완료 ({len(essay)}자)")
            return essay
        except Exception as e:
            logger.error(f"[generate_recommendation_essay] 에러: {e}")
            return "에세이 작성 중 오류가 발생했습니다."

    def _parse_json_fallback(self, text: str) -> dict:
        """JSON 파싱 실패 시 fallback"""
        try:
            if not text:
                return {}
            text = text.strip()
            if "```" in text:
                text = re.sub(r'```json|```', '', text).strip()
            return json.loads(text)
        except json.JSONDecodeError:
            return {}


# =========================================================
# 싱글톤 인스턴스 생성 (앱 전체에서 공유)
# =========================================================
gemini_service = GeminiService()
