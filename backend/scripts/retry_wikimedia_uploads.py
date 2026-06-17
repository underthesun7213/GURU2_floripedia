# DORMANT (Phase1). track2에서 backend/data/floripedia_v2.json 기준으로 입력 재배선 필요.
"""
Wikimedia 실패 이미지 재시도 스크립트.

all_plants.json에서 Firebase URL이 아닌 이미지(=실패분)를 찾아
1장씩 천천히 다운로드 → 리사이즈 → Firebase Storage 업로드.
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

DATA_FILE = os.path.join(BACKEND_DIR, "data", "all_plants.json")
PROGRESS_FILE = os.path.join(BACKEND_DIR, "data", "retry_progress.json")
MAX_WIDTH = 800
JPEG_QUALITY = 85
REQUEST_TIMEOUT = 30
DELAY_BETWEEN = 2  # Wikimedia 429 방지용 대기(초)
MAX_RETRIES = 3


def download_and_resize(url: str) -> bytes:
    """URL에서 이미지 다운로드 → 리사이즈 → JPEG 바이트 반환"""
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
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False)


def main():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        plants = json.load(f)

    # 실패분(non-Firebase URL) 수집
    tasks = []
    for plant in plants:
        pid = plant["_id"]
        for idx, img in enumerate(plant.get("images", [])):
            url = img if isinstance(img, str) else (img.get("url", "") if isinstance(img, dict) else "")
            if url and "firebase" not in url.lower():
                tasks.append((pid, idx, url))

    progress = load_progress()
    # 이미 재시도 성공한 것 제외
    remaining = [(pid, idx, url) for pid, idx, url in tasks
                 if f"{pid}_{idx}" not in progress or not progress[f"{pid}_{idx}"].get("success")]

    print(f"총 실패분: {len(tasks)}장, 이미 재시도 성공: {len(tasks) - len(remaining)}장")
    print(f"남은 작업: {len(remaining)}장 (1장당 ~{DELAY_BETWEEN}초 대기)")
    est_minutes = len(remaining) * (DELAY_BETWEEN + 3) / 60
    print(f"예상 소요: ~{est_minutes:.0f}분")
    print()

    if not remaining:
        print("처리할 이미지가 없습니다.")
        return

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
                    "size_kb": len(image_bytes) / 1024,
                    "success": True,
                }
                success += 1
                total_kb += len(image_bytes) / 1024
                break
            except Exception as e:
                if attempt < MAX_RETRIES:
                    wait = DELAY_BETWEEN * (attempt + 2)  # 점진적 대기: 4, 6, 8초
                    time.sleep(wait)
                    continue
                progress[key] = {
                    "original_url": url,
                    "error": str(e),
                    "success": False,
                }
                fail += 1

        # 진행 출력 + 저장
        if (i + 1) % 10 == 0 or (i + 1) == len(remaining):
            elapsed = time.time() - start
            rate = (i + 1) / elapsed * 60 if elapsed > 0 else 0
            print(f"  [{i+1}/{len(remaining)}] 성공:{success} 실패:{fail} ({rate:.0f}장/분)")
            save_progress(progress)

        # Wikimedia 429 방지 대기
        time.sleep(DELAY_BETWEEN)

    elapsed_total = time.time() - start
    print(f"\n=== 재시도 완료 ===")
    print(f"성공: {success}, 실패: {fail}")
    print(f"총 용량: {total_kb/1024:.1f}MB, 소요: {elapsed_total/60:.1f}분")

    if fail > 0:
        print(f"\n=== 여전히 실패 ({fail}장) ===")
        fails = [v for v in progress.values() if not v.get("success")]
        for item in fails[:20]:
            print(f"  {item.get('original_url', '?')[:80]} - {item.get('error', '')[:60]}")

    # all_plants.json 업데이트
    print("\nall_plants.json 업데이트 중...")
    updated_count = 0
    for plant in plants:
        pid = plant["_id"]
        images = plant.get("images", [])
        changed = False
        for idx in range(len(images)):
            key = f"{pid}_{idx}"
            if key in progress and progress[key].get("success"):
                images[idx] = progress[key]["firebase_url"]
                changed = True
        if changed:
            plant["images"] = images
            if images:
                plant["imageUrl"] = images[0]
            updated_count += 1

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(plants, f, ensure_ascii=False, indent=2)
    print(f"all_plants.json 업데이트: {updated_count}개 식물")

    # MongoDB 업데이트
    print("\nMongoDB 업데이트 중...")
    try:
        from pymongo import MongoClient
        MONGO_URL = os.getenv("MONGO_URI")
        DB_NAME = os.getenv("MONGODB_DB_NAME", "floripedia")
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000, tlsInsecure=True)
        db = client[DB_NAME]
        collection = db["plants"]

        mongo_updated = 0
        for plant in plants:
            pid = plant["_id"]
            key_prefix = f"{pid}_"
            if any(k.startswith(key_prefix) and v.get("success") for k, v in progress.items()):
                result = collection.update_one(
                    {"_id": pid},
                    {"$set": {"images": plant["images"], "imageUrl": plant["imageUrl"]}}
                )
                if result.modified_count > 0:
                    mongo_updated += 1
        print(f"MongoDB 업데이트: {mongo_updated}건")
    except Exception as e:
        print(f"MongoDB 업데이트 실패: {e}")

    # 진행 파일 정리 (전부 성공 시)
    if fail == 0 and os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        print("진행 파일 삭제")

    print("\n완료!")


if __name__ == "__main__":
    main()
