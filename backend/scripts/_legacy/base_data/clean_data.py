import json
import re
import os
import sys

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(BACKEND_DIR)


def clean_html(text):
    """HTML 태그 및 특수 엔티티 제거"""
    if not text: return ""
    # <p>, <br> 등 모든 태그 제거 및 특수문자 정제
    clean = re.compile('<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
    return re.sub(clean, '', text).strip()

def process_and_save():
    input_file = os.path.join(BACKEND_DIR, 'data/enriched_plants_3_flash.json')
    output_file = os.path.join(BACKEND_DIR, 'data/cleaned_plants.json')

    if not os.path.exists(input_file):
        print(f"❌ 원본 파일이 없습니다: {input_file}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        plants = json.load(f)

    print(f"🧹 {len(plants)}개의 데이터 정제 및 정렬 시작...")

    for p in plants:
        # [1] 중복 키워드 제거
        if "searchKeywords" in p:
            seen = set()
            p["searchKeywords"] = [x for x in p["searchKeywords"] if not (x in seen or seen.add(x))]

        # [2] HTML 태그 정제 (설명, 관리법 등 모든 텍스트 필드)
        if "stories" in p:
            for s in p["stories"]:
                s["content"] = clean_html(s.get("content", ""))
        
        if "horticulture" in p:
            p["horticulture"]["management"] = clean_html(p["horticulture"].get("management", ""))
        p["habitat"] = clean_html(p.get("habitat", ""))

    # [3] ID 순으로 정렬 (1번부터 366번까지)
    plants.sort(key=lambda x: int(x["_id"]))

    # 결과 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(plants, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 정제 완료! '{output_file}' 파일을 확인해 보세요.")
    print(f"💡 문체나 데이터가 마음에 든다면 'upload_to_mongodb.py'를 실행하세요.")

if __name__ == "__main__":
    process_and_save()