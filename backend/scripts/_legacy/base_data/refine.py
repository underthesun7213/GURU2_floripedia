import os
import sys
import json
import asyncio
from typing import List
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- [시스템 루트 설정] ---
# 현재 파일의 부모의 부모 디렉토리(backend/)를 파이썬 경로에 추가
# 이를 통해 'from app.schemas...' 같은 절대 경로 임포트가 가능해집니다.
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(BACKEND_DIR)

# --- [환경 변수 로드] ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ 에러: .env 파일에 GEMINI_API_KEY가 설정되지 않았습니다.")
    sys.exit(1)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# 안전 설정을 모두 끄기 (식물 데이터 가공용)
safety_settings = [
    {"category": HarmCategory.HARM_CATEGORY_HARASSMENT, "threshold": HarmBlockThreshold.BLOCK_NONE},
    {"category": HarmCategory.HARM_CATEGORY_HATE_SPEECH, "threshold": HarmBlockThreshold.BLOCK_NONE},
    {"category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, "threshold": HarmBlockThreshold.BLOCK_NONE},
    {"category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, "threshold": HarmBlockThreshold.BLOCK_NONE},
]

# 모델 선언 시 설정 적용
model = genai.GenerativeModel(
    model_name='gemini-3-flash-preview',
    safety_settings=safety_settings
)
# --- [카테고리 및 향기 정의] ---
CATEGORIES = ["일년초", "숙근초", "구근식물", "관엽식물", "화목", "조경수목", "다육식물", "식용작물", "수생식물"]
SCENT_KEYWORDS = ["달콤한", "은은한", "싱그러운", "상큼한", "고급스러운", "숲속의", "차분한", "무향"]

# --- [Gemini 호출 로직] ---
async def get_refined_category(description: str) -> str:
    prompt = f"""
    너는 20년 경력의 원예학자야. 아래 식물 설명을 읽고 제공된 카테고리 중 하나만 골라줘.
    기준: {", ".join(CATEGORIES)}
    설명: {description}
    주의: 나무의 경우 꽃이 화려하면 '화목', 수형 중심이면 '조경수목'으로 분류해. 단어만 대답해.
    """
    try:
        response = model.generate_content(prompt)
        res_text = response.text.strip()
        return res_text if res_text in CATEGORIES else "기타"
    except Exception as e:
        print(f"Category Error: {e}")
        return "기타"

async def get_scent_tags(name: str, description: str) -> List[str]:
    prompt = f"""
    식물 '{name}'의 특성을 고려해 아래 향기 리스트에서 1~3개를 골라 JSON 리스트 형식으로만 대답해.
    키워드: {", ".join(SCENT_KEYWORDS)}
    설명: {description}
    출력 예시: ["은은한", "달콤한"]
    """
    try:
        response = model.generate_content(prompt)
        # 마크다운 태그 제거 로직
        cleaned = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except Exception as e:
        print(f"Scent Error for {name}: {e}")
        return ["은은한"]

# --- [메인 실행 로직] ---
async def main():
    input_path = os.path.join(BACKEND_DIR, "data", "cleaned_plants.json")
    output_path = os.path.join(BACKEND_DIR, "data", "refined_plants.json")

    with open(input_path, "r", encoding="utf-8") as f:
        plants = json.load(f)

    refined_data = []
    print(f"🚀 총 {len(plants)}개 데이터 정제 시작 (루트: {BACKEND_DIR})")

    for index, plant in enumerate(plants):
        name = plant.get("name", "Unknown")
        original_cat = plant.get("horticulture", {}).get("category", "")

        # 1. 기존 내용 백업 및 필드 정리
        plant["horticulture"]["pre_content"] = original_cat
        
        # 2. Gemini 정제 (카테고리 & 향기)
        plant["horticulture"]["category"] = await get_refined_category(original_cat)
        plant["scent_tags"] = await get_scent_tags(name, original_cat)

        refined_data.append(plant)
        print(f"[{index+1}/{len(plants)}] {name} 완료: {plant['horticulture']['category']}")
        
        # API 레이트 리밋 방지
        await asyncio.sleep(0.5)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(refined_data, f, ensure_ascii=False, indent=4)
    
    print(f"\n✅ 완료! 결과물: {output_path}")

if __name__ == "__main__":
    asyncio.run(main())