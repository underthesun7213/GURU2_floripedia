import requests
import xmltodict
import json
import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
API_KEY = os.getenv("DATA_API_KEY")
BASE_URL = "https://apis.data.go.kr/1390804/NihhsTodayFlowerInfo01/selectTodayFlower01"

def fetch_detailed_flowers():
    if not API_KEY:
        print("❌ DATA_API_KEY가 없습니다.")
        sys.exit(1)

    data_dir = os.path.join(BACKEND_DIR, 'data')
    os.makedirs(data_dir, exist_ok=True)
    all_flowers = []
    
    # 366일 (윤년 포함)
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    print("🌸 [데이터 확인 완료] 366일 전수 수집을 시작합니다...")

    for month in range(1, 13):
        for day in range(1, month_days[month] + 1):
            # 문자열이 아닌 숫자 그대로 전달해도 되는 구조이므로 안전하게 조립
            full_url = f"{BASE_URL}?serviceKey={API_KEY}&fMonth={month}&fDay={day}"

            try:
                response = requests.get(full_url, timeout=15)
                
                if response.status_code == 200:
                    # XML -> Dict 변환
                    dict_data = xmltodict.parse(response.content)
                    
                    try:
                        # 💡 보내주신 로그의 실제 계층 구조 적용
                        # document -> root -> result
                        flower_data = dict_data['document']['root']['result']
                        
                        # 나중에 정렬/조회를 위해 날짜 정보 명시적 추가
                        flower_data['month'] = month
                        flower_data['day'] = day
                        
                        all_flowers.append(flower_data)
                        print(f"✅ {month:02d}-{day:02d} 수집 성공: {flower_data.get('flowNm')}")
                    
                    except KeyError:
                        # 구조가 평소와 다를 경우 원인 파악 후 종료
                        print(f"\n❌ {month}-{day} 데이터 추출 실패. 응답 구조를 확인하세요.")
                        print(f"🧐 응답 원문: {dict_data}")
                        sys.exit(1)
                else:
                    print(f"\n❌ HTTP 에러: {response.status_code}")
                    sys.exit(1)

            except Exception as e:
                print(f"\n⚠️ 오류 발생: {e}")
                sys.exit(1)
            
            time.sleep(0.1) # 서버 보호

    # 최종 저장
    with open(os.path.join(data_dir, 'flowers_detail.json'), 'w', encoding='utf-8') as f:
        json.dump(all_flowers, f, ensure_ascii=False, indent=2)

    print(f"\n✨ 완료! 총 {len(all_flowers)}개의 상세 데이터를 저장했습니다.")

if __name__ == "__main__":
    fetch_detailed_flowers()