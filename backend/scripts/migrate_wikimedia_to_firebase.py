# DORMANT (Phase1). track2에서 backend/data/floripedia_v2.json 기준으로 입력 재배선 필요.
"""
Wikimedia → Firebase Storage 이미지 마이그레이션 스크립트.

MongoDB에서 imageUrl이 Wikimedia인 식물(195개)을 찾아
이미지를 다운로드 → 리사이즈 → Firebase Storage 업로드 → MongoDB URL 갱신.
Wikimedia 429 방지를 위해 요청 간 2초 대기.
"""
import json
import os
import sys
import time
import requests
from io import BytesIO
from PIL import Image

# 프로젝트 루트 설정
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BACKEND_DIR)

# Firebase 초기화
import firebase_admin
from firebase_admin import credentials, storage
from dotenv import load_dotenv

load_dotenv(os.path.join(BACKEND_DIR, ".env"))

FIREBASE_CRED_PATH = os.path.join(BACKEND_DIR, "app", "core", "firebase-key.json")
FIREBASE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET", "floripedia-c0bf0.firebasestorage.app")

if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
    firebase_admin.initialize_app(cred, {"storageBucket": FIREBASE_BUCKET})

# MongoDB 연결
from pymongo import MongoClient

MONGO_URL = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGODB_DB_NAME", "floripedia")

# 설정
PROGRESS_FILE = os.path.join(BACKEND_DIR, "data", "wikimedia_migration_progress.json")
MAX_WIDTH = 800
JPEG_QUALITY = 85
REQUEST_TIMEOUT = 30
DELAY_BETWEEN = 2
MAX_RETRIES = 3


def download_and_resize(url: str) -> bytes:
    """URL에서 이미지 다운로드 -> 리사이즈 -> JPEG 바이트 반환"""
    headers = {
        "User-Agent": "FloripediaBot/1.0 (educational plant encyclopedia; contact: floripedia@example.com)",
        "Accept": "image/*,*/*;q=0.8",
    }
    resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "")
    if "html" in content_type.lower():
        raise ValueError(f"HTML 응답 (봇 차단 가능): {content_type}")

    img = Image.open(BytesIO(resp.content))

    if img.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = bg

    if img.mode != "RGB":
        img = img.convert("RGB")

    if img.width > MAX_WIDTH:
        ratio = MAX_WIDTH / img.width
        new_size = (MAX_WIDTH, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buf.getvalue()


def upload_to_firebase(image_bytes: bytes, storage_path: str) -> str:
    """Firebase Storage에 업로드하고 공개 URL 반환"""
    bucket = storage.bucket()
    blob = bucket.blob(storage_path)
    blob.upload_from_string(image_bytes, content_type="image/jpeg")
    blob.make_public()
    return blob.public_url


def load_progress() -> dict:
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(progress: dict):
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False)


def main():
    # 1. MongoDB에서 Wikimedia URL 식물 조회
    print("MongoDB 연결 중...")
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=10000, tlsInsecure=True)
    db = client[DB_NAME]
    collection = db["plants"]

    query = {"imageUrl": {"$regex": "wikimedia", "$options": "i"}}
    affected_plants = list(collection.find(query))
    print(f"Wikimedia 이미지 식물: {len(affected_plants)}개")

    # 2. 작업 목록 생성 (plant_id, index, url)
    tasks = []
    for plant in affected_plants:
        pid = plant["_id"]
        for idx, img_url in enumerate(plant.get("images", [])):
            url = img_url if isinstance(img_url, str) else ""
            if url and "wikimedia" in url.lower():
                tasks.append((pid, idx, url))

    # 3. 이미 완료된 것 제외
    progress = load_progress()
    remaining = [
        (pid, idx, url)
        for pid, idx, url in tasks
        if not progress.get(f"{pid}_{idx}", {}).get("success")
    ]

    total_images = len(tasks)
    already_done = total_images - len(remaining)
    print(f"총 이미지: {total_images}장, 완료: {already_done}장, 남은 작업: {len(remaining)}장")
    est_minutes = len(remaining) * (DELAY_BETWEEN + 3) / 60
    print(f"예상 소요: ~{est_minutes:.0f}분\n")

    if not remaining:
        print("처리할 이미지가 없습니다.")
        # MongoDB 업데이트만 수행
        update_mongodb(collection, affected_plants, progress)
        client.close()
        return

    # 4. 다운로드 → 업로드 루프
    success = 0
    fail = 0
    total_kb = 0
    start = time.time()

    for i, (pid, idx, url) in enumerate(remaining):
        key = f"{pid}_{idx}"
        storage_path = f"plants/{pid}/{idx}.jpg"

        for attempt in range(MAX_RETRIES + 1):
            try:
                image_bytes = download_and_resize(url)
                firebase_url = upload_to_firebase(image_bytes, storage_path)
                progress[key] = {
                    "firebase_url": firebase_url,
                    "size_kb": round(len(image_bytes) / 1024, 1),
                    "success": True,
                }
                success += 1
                total_kb += len(image_bytes) / 1024
                break
            except Exception as e:
                if attempt < MAX_RETRIES:
                    wait = DELAY_BETWEEN * (attempt + 2)
                    print(f"    재시도 {attempt+1}/{MAX_RETRIES} ({wait}초 대기): {e}")
                    time.sleep(wait)
                    continue
                progress[key] = {
                    "original_url": url,
                    "error": str(e),
                    "success": False,
                }
                fail += 1
                print(f"    실패: {pid}/{idx} - {e}")

        # 진행 출력 + 저장
        if (i + 1) % 10 == 0 or (i + 1) == len(remaining):
            elapsed = time.time() - start
            rate = (i + 1) / elapsed * 60 if elapsed > 0 else 0
            print(f"  [{i+1}/{len(remaining)}] 성공:{success} 실패:{fail} ({rate:.0f}장/분)")
            save_progress(progress)

        time.sleep(DELAY_BETWEEN)

    elapsed_total = time.time() - start
    print(f"\n=== 다운로드/업로드 완료 ===")
    print(f"성공: {success}, 실패: {fail}")
    print(f"총 용량: {total_kb/1024:.1f}MB, 소요: {elapsed_total/60:.1f}분")

    if fail > 0:
        print(f"\n=== 실패 목록 ({fail}장) ===")
        fails = {k: v for k, v in progress.items() if not v.get("success")}
        for key, item in list(fails.items())[:20]:
            print(f"  {key}: {item.get('original_url', '?')[:80]} - {item.get('error', '')[:60]}")

    # 5. MongoDB 업데이트
    update_mongodb(collection, affected_plants, progress)

    # 6. 정리
    if fail == 0 and os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        print("진행 파일 삭제")

    client.close()
    print("\n완료!")


def update_mongodb(collection, affected_plants, progress):
    """성공한 이미지의 Firebase URL로 MongoDB 업데이트"""
    print("\nMongoDB 업데이트 중...")
    updated = 0

    for plant in affected_plants:
        pid = plant["_id"]
        images = plant.get("images", [])
        new_images = []
        changed = False

        for idx, img_url in enumerate(images):
            key = f"{pid}_{idx}"
            if progress.get(key, {}).get("success"):
                new_images.append(progress[key]["firebase_url"])
                changed = True
            else:
                new_images.append(img_url)

        if changed:
            new_image_url = new_images[0] if new_images else plant.get("imageUrl", "")
            result = collection.update_one(
                {"_id": pid},
                {"$set": {"images": new_images, "imageUrl": new_image_url}},
            )
            if result.modified_count > 0:
                updated += 1

    print(f"MongoDB 업데이트: {updated}개 식물")


if __name__ == "__main__":
    main()
