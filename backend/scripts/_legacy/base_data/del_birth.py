import os
import sys
import json

# --- [1. 시스템 루트 및 경로 설정] ---
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(BACKEND_DIR)

# 파일 경로를 절대 경로로 고정 (터미널 위치 상관없이 동작)
# backend/data/refine.json 경로를 가리킵니다.
INPUT_PATH = os.path.join(BACKEND_DIR, "data", "refined_plants.json")
OUTPUT_PATH = os.path.join(BACKEND_DIR, "data", "cleaned_refine.json")

def clean_plant_data():
    try:
        # 1. 파일 읽기
        print(f"📂 파일 읽기 시도 중: {INPUT_PATH}")
        with open(INPUT_PATH, 'r', encoding='utf-8') as f:
            plant_data = json.load(f)
        
        cleaned_count = 0
        
        # 2. 데이터 순회 및 삭제 로직
        for item in plant_data:
            # birthDate 필드 무조건 삭제
            if 'birthDate' in item:
                del item['birthDate']
            
            # scent_tags가 빈 배열이면 삭제
            if 'scent_tags' in item and isinstance(item['scent_tags'], list) and len(item['scent_tags']) == 0:
                del item['scent_tags']
            
            # scentTags(카멜케이스)도 빈 배열이면 삭제
            if 'scentTags' in item and isinstance(item['scentTags'], list) and len(item['scentTags']) == 0:
                del item['scentTags']
            
            # --- [편파적 인기도 초기값 설정] ---
            # 꽃 이름을 기준으로 점수 부여 (필요시 이름 추가)
            if item.get('name') in ['수선화','과꽃', '국화', '뽕나무', '오동나무', '갯버들',
 '검팽나무', '겨우살이', '동백',  '생강', '석류', '조팝나무', '주목', '진달래',
 '자기나무', '작약', '잔대', '장미', '적송', '전나무', '접시꽃', '제비꽃',
'패랭이꽃', '팽나무', '해바라기', '향나무', '느티나무','코스모스', '클로버',
 '키위', '타임', '튤립', '수수꽃다리','섬초롱꽃',  '분꽃', '붓꽃', 
'선인장', '설악초', '소나무','엉겅퀴', '연꽃', '코스모스', '투구꽃', 
'포인세티아','소국', '억새', '팬지', '히아신스', '프리지아',
'개나리', '데이지', '명자나무', '민들레', '벚나무', '시클라멘', '심비디움', 
'아네모네', '철쭉', '목련', 
'스위트피', '복수초', '산거울', '솜나물', '아잘레아', 
'안스리움', '골담초', '에크메아', '제라늄', '끈끈이주걱', 
 '유채', '네펜데스', '남천', '냉이', '동백나무', '설강화',
'코르딜리네', '디펜바키아', '레몬', '무스카리', '산자고', '스노우드롭',
'카틀레야', '온시디움', '크로커스', '꼬리풀', '꽃마리', '꽈리',
'덴드로비움', '들깨', '리모니움', '메리골드', '초롱꽃', 
'민트', '바베나', '베고니아', '부들', '살비아', '안개꽃', '애기똥풀', 
'매실', '메밀', '모란', '목련',  '민들레',  '참깨', '참나무', '채송화', '천일홍', 
 '목화', '무', '무궁화', '미나리','사과', '산수유',  '매화나무'
'백합', '백일홍', '복숭아', '살구',  '할미꽃', '동자꽃', '금낭화',
'스토크', '아나나스', '아마릴리스','호랑가시나무', '앵초', '박하', '딸기']:
                item['popularity_score'] = 1000
            else:
                item['popularity_score'] = 0
                
            cleaned_count += 1

        # 3. 정제된 파일 저장
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(plant_data, f, ensure_ascii=False, indent=4)
        
        print(f"✅ 성공: {cleaned_count}개의 데이터를 클리닝하여 저장했습니다.")
        print(f"📍 저장 위치: {OUTPUT_PATH}")

    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다. 경로를 확인하세요: {INPUT_PATH}")
    except json.JSONDecodeError:
        print("❌ JSON 파일 형식이 잘못되었습니다.")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    clean_plant_data()