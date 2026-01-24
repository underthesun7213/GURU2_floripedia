import json
import re
from typing import Optional, List, Dict, Any
import google.generativeai as genai
from PIL import Image
import io
from app.core.config import settings

# 설정 로드
genai.configure(api_key=settings.GEMINI_API_KEY)

class GeminiService:
    """
    Gemini API 서비스 클래스
    - 데이터 정제(Sanitization) 로직 포함 (500 에러 및 데이터 불일치 방지용)
    """

    def __init__(self):
        # Gemini 3 Flash 사용
        self.model = genai.GenerativeModel(model_name='gemini-3-flash-preview')

    async def _generate_json_content(self, parts: list, prompt_text: str = "") -> Optional[dict]:
        try:
            response = await self.model.generate_content_async(
                parts,
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"Gemini 생성/파싱 실패: {e}")
            return self._parse_json_fallback(prompt_text)

    # =========================================================
    # [핵심] 똥 데이터 치우는 청소부 메서드 (Sanitizer)
    # Gemini가 제멋대로 보낸 데이터를 규격에 맞게 강제 변환함
    # =========================================================
    def _sanitize_plant_data(self, data: dict) -> dict:
        if not data:
            return data
            
        print(f"[DEBUG] 정제 전 데이터 확인: {data.get('name')}")

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
            elif val not in ["SPRING", "SUMMER", "FALL", "WINTER"]:
                 data["season"] = "SPRING" # 기본값

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

        # -------------------------------------------------------
        # 3. [신규] 카테고리/그룹 강제 매핑 (사용자 요청 반영)
        # -------------------------------------------------------
        
        # (1) 식물 분류 그룹 (categoryGroup)
        valid_cat_groups = ['꽃과 풀', '나무와 조경', '실내 인테리어', '텃밭과 정원']
        horti = data.get("horticulture", {})
        if horti and "categoryGroup" in horti:
            val = horti["categoryGroup"]
            if val not in valid_cat_groups:
                # 엉뚱한 값이면 '꽃과 풀'로 초기화하거나 매핑 시도
                if "나무" in val or "조경" in val: horti["categoryGroup"] = "나무와 조경"
                elif "실내" in val: horti["categoryGroup"] = "실내 인테리어"
                elif "채소" in val or "텃밭" in val: horti["categoryGroup"] = "텃밭과 정원"
                else: horti["categoryGroup"] = "꽃과 풀"

        # (2) 꽃말 감성 그룹 (flowerGroup)
        valid_flower_groups = ['사랑/고백', '위로/슬픔', '감사/존경', '이별/그리움', '행복/즐거움']
        flower_info = data.get("flowerInfo", {})
        if flower_info and "flowerGroup" in flower_info:
            val = flower_info["flowerGroup"]
            # 만약 Gemini가 "국화과" 같은 걸 넣었다면 기본값으로 변경
            if val not in valid_flower_groups:
                flower_info["flowerGroup"] = "행복/즐거움" # 안전한 기본값

        # (3) 향기 그룹 (scentGroup) - 배열로 들어올 수도 있고 단일 값일 수도 있음
        valid_scent_groups = ['달콤·화사', '싱그러운·시원', '은은·차분', '무향']
        scent_info = data.get("scentInfo", {})
        if scent_info and "scentGroup" in scent_info:
            origin_vals = scent_info["scentGroup"]
            if not isinstance(origin_vals, list): origin_vals = [origin_vals]
            
            cleaned_scents = []
            for v in origin_vals:
                if v in valid_scent_groups:
                    cleaned_scents.append(v)
                else:
                    # 영어 등 엉뚱한 값 매핑
                    if v in ["SWEET", "FLORAL"]: cleaned_scents.append("달콤·화사")
                    elif v in ["FRESH", "COOL", "GREEN"]: cleaned_scents.append("싱그러운·시원")
                    elif v in ["SOFT", "CALM", "WOODY"]: cleaned_scents.append("은은·차분")
                    else: cleaned_scents.append("은은·차분") # 기본값
            
            # 중복 제거 후 리스트로 다시 저장 (빈 리스트면 무향 처리)
            scent_info["scentGroup"] = list(set(cleaned_scents)) if cleaned_scents else ["무향"]

        # (4) 색상 그룹 (colorGroup)
        valid_color_groups = ['백색/미색', '노랑/주황', '빨강/분홍', '푸른색', '갈색/검정']
        color_info = data.get("colorInfo", {})
        if color_info and "colorGroup" in color_info:
            origin_vals = color_info["colorGroup"]
            if not isinstance(origin_vals, list): origin_vals = [origin_vals]
            
            cleaned_colors = []
            for v in origin_vals:
                if v in valid_color_groups:
                    cleaned_colors.append(v)
                else:
                    # 영어 값 매핑
                    if v == "WHITE" or "백" in v: cleaned_colors.append("백색/미색")
                    elif v in ["YELLOW", "ORANGE"] or "노랑" in v: cleaned_colors.append("노랑/주황")
                    elif v in ["RED", "PINK", "MAGENTA"] or "붉" in v: cleaned_colors.append("빨강/분홍")
                    elif v in ["BLUE", "SKY", "PURPLE", "VIOLET"] or "푸" in v: cleaned_colors.append("푸른색")
                    elif v in ["BROWN", "BLACK"] or "검" in v: cleaned_colors.append("갈색/검정")
                    else: cleaned_colors.append("백색/미색")
            
            color_info["colorGroup"] = list(set(cleaned_colors)) if cleaned_colors else ["백색/미색"]

        # (5) 세부 색상 라벨 (colorLabels)
        valid_labels = ['백색', '연두', '초록', '노랑', '빨강', '분홍', '연보라', '보라', '파랑', '하늘', '살구', '갈색', '검정', '다홍', '주황', '미색']
        if color_info and "colorLabels" in color_info:
             # 라벨은 Gemini가 비교적 잘 맞추지만, 혹시 모르니 필터링
             origin_labels = color_info["colorLabels"]
             if not isinstance(origin_labels, list): origin_labels = [origin_labels]
             # 유효한 것만 남기기
             filtered = [l for l in origin_labels if l in valid_labels]
             # 만약 다 날아갔으면 기본값
             if not filtered and cleaned_colors:
                 # 그룹 보고 대충 하나 찍기
                 if "백색/미색" in cleaned_colors: filtered.append("백색")
                 elif "노랑/주황" in cleaned_colors: filtered.append("노랑")
                 else: filtered.append("초록")
             color_info["colorLabels"] = filtered

        # 4. _id 제거
        if "_id" in data:
            del data["_id"]
            
        print(f"[DEBUG] 정제 완료") 
        return data

    async def get_plant_name_from_image(self, image_data: bytes) -> Optional[dict]:
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
            return await self._generate_json_content([prompt, image])
        except Exception as e:
            print(f"이미지 식별 중 에러: {e}")
            return None

    async def get_plant_name_from_text(self, user_input: str) -> Optional[dict]:
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
        return await self._generate_json_content([prompt])

    async def generate_plant_data_schema(self, name: str, scientific_name: str) -> Optional[dict]:
        # [수정] stories 예시를 '고정'하지 않고 '설명' 형태로 변경하여 Gemini의 창의성 유도
        prompt = f"""
        Generate detailed plant info for '{name}' (Scientific Name: {scientific_name}).
        
        [STRICT INSTRUCTIONS]
        1. Return ONLY JSON.
        2. stories: Generate 2 or more stories. Choose the most appropriate genre for each story.
           - Allowed Genres: HISTORY, MYTH, SCIENCE, EPISODE
        3. season must be one of: SPRING, SUMMER, FALL, WINTER.
        4. Select values ONLY from the lists below for specific fields:
           - horticulture.categoryGroup: ['꽃과 풀', '나무와 조경', '실내 인테리어', '텃밭과 정원']
           - flowerInfo.flowerGroup: ['사랑/고백', '위로/슬픔', '감사/존경', '이별/그리움', '행복/즐거움']
           - scentInfo.scentGroup (List): ['달콤·화사', '싱그러운·시원', '은은·차분', '무향']
           - colorInfo.colorGroup (List): ['백색/미색', '노랑/주황', '빨강/분홍', '푸른색', '갈색/검정']
           - colorInfo.colorLabels (List): ['백색', '연두', '초록', '노랑', '빨강', '분홍', '연보라', '보라', '파랑', '하늘', '살구', '갈색', '검정', '다홍', '주황', '미색']
        
        [JSON Structure]
        {{
             "name": "{name}",
             "scientificName": "{scientific_name}",
             "englishName": "...",
             "isRepresentative": false,
             "taxonomy": {{ "genus": "...", "species": "...", "family": "..." }},
             "horticulture": {{ 
                "category": "...", 
                "categoryGroup": "Pick one from the list above", 
                "usage": [], "management": "...", "preContent": "..." 
             }},
             "habitat": "...",
             "stories": [ 
                 {{
                    "genre": "Select from HISTORY/MYTH/SCIENCE/EPISODE", 
                    "content": "Story content here..."
                 }},
                 {{
                    "genre": "Select from HISTORY/MYTH/SCIENCE/EPISODE", 
                    "content": "Another story content..."
                 }}
             ],
             "season": "SPRING",
             "bloomingMonths": [],
             "searchKeywords": [],
             "popularity_score": 0,
             "colorInfo": {{ "hexCodes": [], "colorLabels": [], "colorGroup": [] }},
             "scentInfo": {{ "scentTags": [], "scentGroup": [] }},
             "flowerInfo": {{ "language": "...", "flowerGroup": "Pick one from the list above" }},
             "images": [],
             "imageUrl": null
        }}
        """
        
        data = await self._generate_json_content([prompt])

        # 정제 로직 실행
        clean_data = self._sanitize_plant_data(data)

        return clean_data
        
    async def generate_recommendation_essay(self, user_situation: str, plant_data: dict) -> str:
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
            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except Exception:
            return "에세이 작성 중 오류가 발생했습니다."

    def _parse_json_fallback(self, text: str) -> dict:
        try:
            if not text: return {}
            text = text.strip()
            if "```" in text:
                text = re.sub(r'```json|```', '', text).strip()
            return json.loads(text)
        except json.JSONDecodeError:
            return {}