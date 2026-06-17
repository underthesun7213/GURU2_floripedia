import json
import math
import os
import sys
import numpy as np
import google.generativeai as genai
from time import sleep
from dotenv import load_dotenv
from google.generativeai.types import SafetySettingDict, HarmCategory, HarmBlockThreshold

# [1] 환경 변수 로드 및 경로 설정
load_dotenv() # .env 파일의 내용을 환경 변수로 불러옵니다.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ 오류: .env 파일에 'GEMINI_API_KEY'가 설정되지 않았습니다.")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

INPUT_PATH = os.path.join(BACKEND_DIR, 'data', 'cleaned_refine.json')
OUTPUT_PATH = os.path.join(BACKEND_DIR, 'data', 'categorized_plants.json')

# ==========================================
# [2] 매핑 및 임베딩 기준 정의
# ==========================================

# 컬러 매핑 (5대 그룹)
BASE_COLOR_CODES = {
    "백색": "#FFFFFF", "연두": "#ADFF2F", "초록": "#228B22", "노랑": "#FFD700",
    "빨강": "#E32636", "분홍": "#FFB7C5", "연보라": "#E6E6FA", "보라": "#800080",
    "파랑": "#4169E1", "하늘": "#87CEEB", "살구": "#FFDAB9", "갈색": "#8B4513",
    "검정": "#2F4F4F", "다홍": "#FF4500", "주황": "#FF8C00", "미색": "#FFFDD0"
}

COLOR_GROUP_MAP = {
    "백색": "백색/미색", "미색": "백색/미색", "살구": "백색/미색", 
    "노랑": "노랑/주황", "주황": "노랑/주황", "다홍": "노랑/주황",
    "빨강": "빨강/분홍", "분홍": "빨강/분홍",
    "보라": "푸른색", "연보라": "푸른색", "파랑": "푸른색", "하늘": "푸른색", "연두": "푸른색", "초록": "푸른색",
    "갈색": "갈색/검정", "검정": "갈색/검정"
}

# 식물 분류 매핑 (4대 그룹)
PLANT_GROUP_MAP = {
    "일년초": "꽃과 풀", "숙근초": "꽃과 풀", "구근식물": "꽃과 풀",
    "화목": "나무와 조경", "조경수목": "나무와 조경",
    "관엽식물": "실내 인테리어", "다육식물": "실내 인테리어",
    "식용작물": "텃밭과 정원", "수생식물": "텃밭과 정원"
}

# 향기 매핑 (4대 그룹)
SCENT_GROUP_MAP = {
    "달콤한": "달콤·화사", "고급스러운": "달콤·화사",
    "상큼한": "싱그러운·시원", "싱그러운": "싱그러운·시원",
    "은은한": "은은·차분", "숲속의": "은은·차분", "차분한": "은은·차분",
    "무향": "무향"
}

# 꽃말 임베딩 기준 그룹 (4대 그룹)
FLOWER_GROUPS = [
    {"label": "사랑/고백", "desc": "사랑, 연정, 고백, 애정, 설레는 마음, 연인, 행복, 순결, 정열, 그리워하는 사랑"},
    {"label": "위로/슬픔", "desc": "위로, 슬픔, 평온, 안식, 고독, 치유, 아픔을 달래는, 고요함, 휴식"},
    {"label": "감사/존경", "desc": "감사, 존경, 우정, 신뢰, 믿음, 은혜, 보답, 성실, 변치 않는 마음, 스승"},
    {"label": "이별/그리움", "desc": "이별, 그리움, 기다림, 추억, 신비로운 기억, 떠나간 사람, 다시 만날 날"}
]

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
# ==========================================
# [3] 유틸리티 함수
# ==========================================

def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 3: hex_str = ''.join([c*2 for c in hex_str])
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def get_closest_label(target_hex):
    try:
        target_rgb = hex_to_rgb(target_hex)
        closest_label = None
        min_dist = float('inf')
        for label, ref_hex in BASE_COLOR_CODES.items():
            ref_rgb = hex_to_rgb(ref_hex)
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(target_rgb, ref_rgb)))
            if dist < min_dist:
                min_dist = dist
                closest_label = label
        return closest_label
    except: return None

# ==========================================
# 꽃말 지능형 분류 로직 (T1 최적화)
# ==========================================

def classify_flower_languages_batch(languages):
    if not languages: return []
    
    prompt = f"""
    당신은 인문학적 식물 도감의 꽃말 큐레이터입니다. 
    다음 꽃말들을 5대 감성 그룹 중 하나로 정확히 분류하여 JSON 배열로 응답하세요.

    [감성 그룹 및 분류 기준]
    1. 사랑/고백: 애정, 구애, 열정, 순결, 자기애, 자만심, 자존심
    2. 위로/슬픔: 치유, 안식, 연민, 고통, 평온, 아픔을 달래는 마음
    3. 감사/존경: 신뢰, 우정, 성실, 명예, 고귀, 보답, 스승, 숭고
    4. 이별/그리움: 기다림, 추억, 고독, 변심, 변덕쟁이, 다시 만날 날, 덧없는 사랑
    5. 행복/즐거움: 행운, 기쁨, 희망, 번영, 승리, 즐거운 마음

    입력 리스트: {languages}

    결과 형식: ["그룹명1", "그룹명2", ...] (오직 JSON 배열만 출력할 것)
    """
    
    try:
        # T1은 응답 속도도 빠르므로 바로 생성
        response = model.generate_content(prompt)
        res_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(res_text)
    except Exception as e:
        print(f"⚠️ API 오류: {e}")
        return ["기타"] * len(languages)


# ==========================================
# [4] 메인 실행부
# ==========================================

def main():
    if not os.path.exists(INPUT_PATH):
        print("❌ 입력 파일을 찾을 수 없습니다.")
        return

    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    unique_data = []
    seen_names = set()

    print(f"🔄 1단계: 기본 정보 가공 및 중복 제거 ({len(data)}건)...")

    # [단계 1] 중복 제거 및 기본 매핑 (API 호출 없음)
    for item in data:
        if item["name"] in seen_names: continue
        seen_names.add(item["name"])

        # horticulture 그룹화
        ori_cat = item.get("horticulture", {}).get("category")
        item["horticulture"] = {
            "category": ori_cat,
            "categoryGroup": PLANT_GROUP_MAP.get(ori_cat, "기타"),
            "usage": item.get("horticulture", {}).get("usage", []),
            "management": item.get("horticulture", {}).get("management", ""),
            "preContent": item.get("horticulture", {}).get("preContent") or item.get("horticulture", {}).get("pre_content", "")
        }

        # colorInfo 가공
        matched_labels = {get_closest_label(h) for h in item.get("hexCode", []) if get_closest_label(h)}
        groups = {COLOR_GROUP_MAP.get(l, "기타") for l in matched_labels}
        item["colorInfo"] = {
            "hexCodes": [BASE_COLOR_CODES[l] for l in matched_labels],
            "colorLabels": list(matched_labels),
            "colorGroup": list(groups) if groups else ["기타"]
        }
        if "hexCode" in item: del item["hexCode"]

        # scentInfo 가공
        tags = item.get("scent_tags", [])
        item["scentInfo"] = {
            "scentTags": tags,
            "scentGroup": list({SCENT_GROUP_MAP.get(t, "무향") for t in tags}) or ["무향"]
        }
        if "scent_tags" in item: del item["scent_tags"]
        
        unique_data.append(item)

    # [단계 2] 꽃말 배치 처리 (API 호출)
    print(f"🚀 2단계: 꽃말 지능형 분류 시작 (총 {len(unique_data)}건, 50개씩 배치)...")
    
    batch_size = 50
    for i in range(0, len(unique_data), batch_size):
        batch = unique_data[i : i + batch_size]
        # 'flowerLanguage'가 없을 경우를 대비해 처리
        languages = [item.get("flowerLanguage", "기타") for item in batch]
        
        classified_groups = classify_flower_languages_batch(languages)
        
        for j, item in enumerate(batch):
            group = classified_groups[j] if j < len(classified_groups) else "기타"
            item["flowerInfo"] = {
                "language": languages[j],
                "flowerGroup": group
            }
            if "flowerLanguage" in item: del item["flowerLanguage"]
        
        print(f" ✅ 처리 중... ({min(i + batch_size, len(unique_data))}/{len(unique_data)})")
        sleep(0.5) # 안전을 위한 딜레이

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(unique_data, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 가공 완료! 파일 저장됨: {OUTPUT_PATH}")

    

if __name__ == "__main__":
    main()