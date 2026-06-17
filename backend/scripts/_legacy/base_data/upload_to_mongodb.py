import json
import os
import argparse
from pymongo import MongoClient
from dotenv import load_dotenv
import sys
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(BACKEND_DIR)

# .env 파일을 명시적으로 로드 (경로 재확인)
load_dotenv()

# 업로드할 데이터 파일 (BACKEND_DIR 기준 상대경로)
DATA_FILE = 'data/all_plants.json'

def upload_to_db(reset: bool = False, skip_confirm: bool = False):
    # 1. 환경 변수에서 직접 가져오기 (없으면 에러 발생시켜서 원인 파악)
    MONGO_URL = os.getenv("MONGO_URI")
    DB_NAME = os.getenv("MONGODB_DB_NAME")

    if not MONGO_URL:
        print("❌ 에러: .env 파일에 MONGODB_URL이 설정되지 않았습니다.")
        return

    print(f"📡 연결 시도 중: {MONGO_URL[:20]}...") # 보안을 위해 앞부분만 출력

    try:
        # 아틀라스 연결 최적화 옵션 추가
        client = MongoClient(
            MONGO_URL,
            serverSelectionTimeoutMS=5000, # 5초 안에 연결 안 되면 실패 처리
            tlsInsecure=True # 인증서 관련 에러 방지 (필요 시)
        )

        db = client[DB_NAME]
        collection = db["plants"]

        # 연결 테스트 (실제 DB에 반응이 있는지 확인)
        client.admin.command('ping')
        print("✅ MongoDB Atlas 연결 성공!")

        # 현재 DB 상태 확인
        existing_count = collection.count_documents({})
        print(f"📊 현재 DB에 {existing_count}건 존재")

        # 2. 정제된 파일 로드
        file_path = os.path.join(BACKEND_DIR, DATA_FILE)

        with open(file_path, 'r', encoding='utf-8') as f:
            final_data = json.load(f)

        # 3. 데이터 삽입
        mode = "초기화 후 업로드" if reset else "추가 업로드"
        if not skip_confirm:
            confirm = input(f"⚠️ {DB_NAME}.plants 컬렉션에 {len(final_data)}건을 {mode}할까요? (y/n): ")
            if confirm.lower() != 'y':
                print("🚫 작업을 취소했습니다.")
                return
        else:
            print(f"⚠️ {DB_NAME}.plants 컬렉션에 {len(final_data)}건을 {mode}합니다. (--yes)")
        if True:
            if reset:
                collection.delete_many({})
                print("🗑️ 기존 데이터를 삭제했습니다.")

            # 일괄 삽입
            result = collection.insert_many(final_data)
            print(f"✅ 성공: {len(result.inserted_ids)}건 업로드 완료")
            
            # 인덱스 설정
            # 1. 고유 인덱스 (이름 중복 방지)
            collection.create_index("name", unique=True)
            collection.create_index("scientificName")

            # 2. 검색용 인덱스
            collection.create_index("searchKeywords")

            # 3. 카테고리/그룹 필터링용 인덱스 (가장 많이 사용될 필드)
            collection.create_index("horticulture.categoryGroup")
            collection.create_index("colorInfo.colorGroup")
            collection.create_index("scentInfo.scentGroup")

            # 4. 인기순 정렬용 인덱스
            collection.create_index([("popularity_score", -1)])
            print("🔍 인덱스 설정 완료.")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        print("\n💡 체크리스트:")
        print("1. .env의 MONGODB_URL 주소가 'mongodb+srv://...' 형태인지 확인")
        print("2. MongoDB Atlas -> Network Access에서 현재 IP가 허용(Allow)되었는지 확인")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MongoDB 식물 데이터 업로드")
    parser.add_argument("--reset", action="store_true", help="기존 데이터를 삭제 후 업로드")
    parser.add_argument("--yes", "-y", action="store_true", help="확인 프롬프트 생략")
    args = parser.parse_args()
    upload_to_db(reset=args.reset, skip_confirm=args.yes)