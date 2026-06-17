import json
import asyncio
import os
import sys
import google.generativeai as genai
from dotenv import load_dotenv
from google.generativeai.types import SafetySettingDict, HarmCategory, HarmBlockThreshold

# 1. 경로 설정 및 모델 임포트
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(BACKEND_DIR)
try:
    from app.schemas.plant import Plant, Taxonomy, Horticulture, Story, StoryGenre, Season
    print("✅ 데이터 모델 로드 성공")
except ImportError as e:
    print(f"❌ 임포트 실패: {e}")
    sys.exit(1)

load_dotenv()
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

# --- 도우미 함수들 (메인 함수보다 위에 정의해야 안전합니다) ---

def get_season(month: int) -> Season:
    if month in [3, 4, 5]: return Season.SPRING
    if month in [6, 7, 8]: return Season.SUMMER
    if month in [9, 10, 11]: return Season.FALL
    return Season.WINTER

async def fetch_fact_based_data(name: str, flower_lang: str, f_content: str):
    """Gemini API 호출 - 식물학자 모드 프롬프트로 안전 필터 우회 및 데이터 정제"""
    
    # 1. 필터 우회를 위한 학술적 프롬프트 (English System Instruction 활용)
    prompt = f"""
    SYSTEM: You are a professional botanist and encyclopedia editor. 
    TASK: Provide objective botanical data for the species '{name}'.
    
    INPUT DATA:
    - Common Name: {name}
    - Meaning: {flower_lang}
    - Description: {f_content}
    
    REQUIRED OUTPUT (JSON ONLY):
    {{
        "fContent_genre": "Categorize description into [MYTH, SCIENCE, HISTORY, ART, EPISODE]",
        "augmented_stories": [
            {{ "genre": "genre name", "content": "strictly factual botanical or historical story" }},
            {{ "genre": "genre name", "content": "strictly factual botanical or historical story" }}
        ],
        "hexCodes": ["#XXXXXX", "#XXXXXX"],
        "keywords": ["keyword1", "keyword2", "keyword3"]
    }}

    STRICT RULE: Do not include any sensitive, emotional, or dangerous narratives. Focus only on botanical facts.
    """

    try:
        # response_mime_type을 사용하여 JSON 출력을 강제함
        response = model.generate_content(
            prompt, 
            generation_config={"response_mime_type": "application/json"}
        )
        
        res_text = response.text.strip()
        
        # 마크다운 태그 제거 로직
        if res_text.startswith("```"):
            res_text = res_text.split("```")[1].replace("json", "").strip()
            
        data = json.loads(res_text)

        # [방어 로직 1] AI가 객체({})가 아닌 리스트([{}])로 응답했을 경우 처리 (유자나무 에러 방지)
        if isinstance(data, list):
            data = data[0]

        # [방어 로직 2] 키 이름 대소문자 및 누락 체크
        if 'fContent_genre' not in data:
            data['fContent_genre'] = data.get('fcontent_genre') or data.get('genre') or "EPISODE"
            
        # [방어 로직 3] hexCodes가 리스트가 아닌 단일 문자열로 올 경우 처리
        if 'hexCodes' in data and isinstance(data['hexCodes'], str):
            data['hexCodes'] = [data['hexCodes']]
        elif 'hexCodes' not in data:
            data['hexCodes'] = ["#4CAF50"]

        return data

    except Exception as e:
        # 안전 필터에 걸렸을 때 발생하는 finish_reason: 1 에러 등을 여기서 캐치
        print(f"⚠️ {name} AI 처리 실패: {e}")
        return None

# --- 메인 가공 함수 ---

async def build_enriched_data():
    input_file = os.path.join(BACKEND_DIR, 'data/flowers_detail.json')
    output_file = os.path.join(BACKEND_DIR, 'data/enriched_plants_3_flash.json')
    
    if not os.path.exists(input_file):
        print(f"❌ 입력 파일이 없습니다: {input_file}")
        sys.exit(1)

    with open(input_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    # 이어하기 로직: 기존 파일이 있으면 불러오기
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            try:
                enriched_results = json.load(f)
            except:
                enriched_results = []
    else:
        enriched_results = []

    processed_ids = {str(item.get("_id")) for item in enriched_results}
    failed_items = [] # 실패 기록용

    print(f"🪴 총 {len(raw_data)}개 중 {len(processed_ids)}개 완료됨. 남은 작업 시작...")

    for i, p in enumerate(raw_data):
        data_no = str(p.get("dataNo"))
        name = p.get("flowNm", "Unknown")

        if data_no in processed_ids:
            continue
            
        # AI 호출 (정의된 함수 사용)
        ai_res = await fetch_fact_based_data(name, p.get("flowLang", ""), p.get("fContent", ""))
        
        # [안전장치] 첫 번째 데이터 실패 시 즉시 종료 (설정 오류 확인)
        if ai_res is None and len(enriched_results) == 0:
            print(f"🛑 첫 번째 데이터({name}) 처리 실패. API 키나 설정을 확인하세요.")
            sys.exit(1)
        
        # 중간 실패 시 기록 후 건너뛰기
        if ai_res is None:
            print(f"⏩ {name} AI 응답 실패. 건너뜁니다.")
            failed_items.append(f"{name} (AI Error)")
            continue

        try:
            # Pydantic 모델에 맞게 데이터 구성
            stories = [Story(genre=ai_res['fContent_genre'], content=p.get("fContent", ""))]
            for s in ai_res.get('augmented_stories', []):
                stories.append(Story(genre=s['genre'], content=s['content']))

            sci_parts = p.get("fSctNm", "").split()
            plant_obj = Plant(
                _id=data_no,
                name=name,
                scientificName=p.get("fSctNm", ""),
                isRepresentative=True,
                taxonomy=Taxonomy(
                    genus=sci_parts[0] if sci_parts else "Unknown",
                    species=" ".join(sci_parts[1:]) if len(sci_parts) > 1 else "sp.",
                    family=p.get("fType", "").split()[0] if p.get("fType") else "미분류"
                ),
                horticulture=Horticulture(
                    category=p.get("fType", ""),
                    usage=[u.strip() for u in p.get("fUse", "").split(',')] if p.get("fUse") else [],
                    management=p.get("fGrow", "")
                ),
                habitat=p.get("fGrow", ""),
                flowerLanguage=p.get("flowLang", ""),
                stories=stories,
                birthDate=[f"{int(p.get('fMonth', 1)):02d}-{int(p.get('fDay', 1)):02d}"],
                imageUrl=p.get("imgUrl1", ""),
                hexCode=ai_res.get('hexCodes', ["#4CAF50"]),
                season=get_season(int(p.get("fMonth", 1))),
                bloomingMonths=[int(p.get("fMonth", 1))],
                scentTags=[p.get("fScent")] if p.get("fScent") else [],
                searchKeywords=ai_res.get('keywords', []) + [name]
            )
            
            # 리스트 추가 및 즉시 파일 저장
            enriched_results.append(plant_obj.model_dump(by_alias=True))
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(enriched_results, f, ensure_ascii=False, indent=2)
                
            print(f"[{len(enriched_results)}/{len(raw_data)}] ✅ {name} 저장 완료")
            
        except Exception as e:
            print(f"⚠️ {name} 매핑 에러: {e}")
            failed_items.append(f"{name} (Mapping Error: {e})")
            if len(enriched_results) == 0: sys.exit(1)
            continue

        # RPM 준수
        await asyncio.sleep(0.1)

    # 최종 결과 보고
    print("\n" + "="*50)
    print(f"🏁 작업 종료: 성공 {len(enriched_results)}개 / 실패 {len(failed_items)}개")
    if failed_items:
        print("\n[실패 목록]")
        for item in failed_items:
            print(f"- {item}")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(build_enriched_data())