# DORMANT (Phase1). track2에서 backend/data/floripedia_v2.json 기준으로 입력 재배선 필요.
"""
식물 이미지를 Firebase Storage에 업로드하는 스크립트.

1. all_plants.json에서 이미지 URL 추출 (images 배열만, imageUrl은 images[0]과 동일하므로 제외)
2. 외부 URL에서 다운로드 → Pillow로 리사이즈(800px) → JPEG 압축(quality 85)
3. Firebase Storage에 plants/{plant_id}/{index}.jpg로 업로드
4. all_plants.json과 MongoDB를 Firebase URL로 업데이트 (imageUrl = images[0])
"""
import json
import os
import sys
import time
import requests
from io import BytesIO
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed

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
PROGRESS_FILE = os.path.join(BACKEND_DIR, "data", "upload_progress.json")
MAX_WIDTH = 800
JPEG_QUALITY = 85
REQUEST_TIMEOUT = 20
MAX_WORKERS = 8  # 동시 다운로드 스레드 (서버 부하 고려)
MAX_RETRIES = 2


def extract_url(image_entry) -> str:
    """이미지 항목에서 URL 추출 (문자열 또는 객체)"""
    if isinstance(image_entry, str):
        return image_entry
    elif isinstance(image_entry, dict):
        return image_entry.get("url", "")
    return ""


def download_and_resize(url: str) -> bytes:
    """URL에서 이미지 다운로드 → 리사이즈 → JPEG 바이트 반환"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": url,  # nihhs.go.kr 등 리퍼러 체크 대비
        "Accept": "image/*,*/*;q=0.8",
    }
    resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
    resp.raise_for_status()

    # 응답이 실제 이미지인지 확인
    content_type = resp.headers.get("Content-Type", "")
    if "html" in content_type.lower():
        raise ValueError(f"HTML 응답 (봇 차단 가능): {content_type}")

    img = Image.open(BytesIO(resp.content))

    # RGBA/P/LA → RGB 변환 (JPEG 저장용)
    if img.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = bg

    if img.mode != "RGB":
        img = img.convert("RGB")

    # 리사이즈 (가로 MAX_WIDTH, 비율 유지)
    if img.width > MAX_WIDTH:
        ratio = MAX_WIDTH / img.width
        new_size = (MAX_WIDTH, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    # JPEG 압축
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


def process_single_image(plant_id: str, img_index: int, url: str) -> dict:
    """이미지 1장 처리: 다운로드 → 리사이즈 → 업로드 (재시도 포함)"""
    storage_path = f"plants/{plant_id}/{img_index}.jpg"

    for attempt in range(MAX_RETRIES + 1):
        try:
            image_bytes = download_and_resize(url)
            firebase_url = upload_to_firebase(image_bytes, storage_path)
            return {
                "plant_id": plant_id,
                "index": img_index,
                "firebase_url": firebase_url,
                "size_kb": len(image_bytes) / 1024,
                "success": True,
            }
        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(1 * (attempt + 1))  # 점진적 대기
                continue
            return {
                "plant_id": plant_id,
                "index": img_index,
                "original_url": url,
                "error": str(e),
                "success": False,
            }


def load_progress() -> dict:
    """이전 진행 상황 로드 (중단 후 재개용)"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(results: dict):
    """진행 상황 저장"""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)


def main():
    # 데이터 로드
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        plants = json.load(f)

    print(f"총 {len(plants)}개 식물 로드")

    # 이전 진행 상황 로드
    progress = load_progress()
    if progress:
        done_count = sum(1 for v in progress.values() if v.get("success"))
        print(f"이전 진행 상황 로드: {done_count}건 완료됨 (이어서 진행)")

    # 처리할 이미지 목록 생성 (images 배열만, imageUrl은 images[0] 복사로 해결)
    tasks = []
    for plant in plants:
        pid = plant["_id"]
        images = plant.get("images", [])
        for idx, img in enumerate(images):
            key = f"{pid}_{idx}"
            if key in progress and progress[key].get("success"):
                continue  # 이미 완료된 항목 스킵
            url = extract_url(img)
            if url:
                tasks.append((pid, idx, url))

    print(f"처리할 이미지: {len(tasks)}장 (이미 완료: {len(progress) - len(tasks) if progress else 0}장)")
    print(f"스레드: {MAX_WORKERS}개 병렬, 재시도: {MAX_RETRIES}회")
    print()

    if not tasks:
        print("처리할 이미지가 없습니다.")
    else:
        # 병렬 처리
        results = dict(progress)  # 이전 결과 포함
        success_count = sum(1 for v in results.values() if v.get("success"))
        fail_count = 0
        total_size_kb = sum(v.get("size_kb", 0) for v in results.values() if v.get("success"))
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {}
            for pid, idx, url in tasks:
                future = executor.submit(process_single_image, pid, idx, url)
                futures[future] = (pid, idx)

            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                pid, idx = futures[future]
                key = f"{pid}_{idx}"
                results[key] = result

                if result["success"]:
                    success_count += 1
                    total_size_kb += result.get("size_kb", 0)
                else:
                    fail_count += 1

                # 진행상황 (50장마다) + 중간 저장
                if (i + 1) % 50 == 0 or (i + 1) == len(tasks):
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed if elapsed > 0 else 0
                    eta = (len(tasks) - i - 1) / rate if rate > 0 else 0
                    print(f"  [{i+1}/{len(tasks)}] 성공:{success_count} 실패:{fail_count} "
                          f"({rate:.1f}장/초, 남은시간: {eta:.0f}초)")
                    save_progress(results)

        elapsed_total = time.time() - start_time
        print(f"\n=== 업로드 완료 ===")
        print(f"성공: {success_count}, 실패: {fail_count}")
        print(f"총 용량: {total_size_kb/1024:.1f}MB")
        print(f"소요 시간: {elapsed_total:.0f}초")

        # 실패 목록 출력
        if fail_count > 0:
            print(f"\n=== 실패 목록 (최대 20개) ===")
            fail_items = [r for r in results.values() if not r.get("success")]
            for item in fail_items[:20]:
                print(f"  ID:{item['plant_id']}[{item['index']}] - {item.get('error','')[:80]}")

        progress = results

    # all_plants.json 업데이트
    print("\nall_plants.json 업데이트 중...")
    for plant in plants:
        pid = plant["_id"]
        images = plant.get("images", [])
        new_images = []
        for idx in range(len(images)):
            key = f"{pid}_{idx}"
            if key in progress and progress[key].get("success"):
                new_images.append(progress[key]["firebase_url"])
            else:
                # 실패한 경우 원본 URL 유지
                new_images.append(extract_url(images[idx]))
        plant["images"] = new_images

        # imageUrl = images[0] (동일하므로 복사)
        if new_images:
            plant["imageUrl"] = new_images[0]

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(plants, f, ensure_ascii=False, indent=2)

    print(f"all_plants.json 저장 완료")

    # MongoDB 업데이트
    print("\nMongoDB 업데이트 중...")
    try:
        from pymongo import MongoClient
        MONGO_URL = os.getenv("MONGO_URI")
        DB_NAME = os.getenv("MONGODB_DB_NAME", "floripedia")
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000, tlsInsecure=True)
        db = client[DB_NAME]
        collection = db["plants"]

        updated = 0
        for plant in plants:
            result = collection.update_one(
                {"_id": plant["_id"]},
                {"$set": {"images": plant["images"], "imageUrl": plant["imageUrl"]}}
            )
            if result.modified_count > 0:
                updated += 1

        print(f"MongoDB 업데이트: {updated}건")
    except Exception as e:
        print(f"MongoDB 업데이트 실패: {e}")
        print("all_plants.json은 이미 업데이트됨. upload_to_mongodb.py로 별도 업로드 가능.")

    # 진행 파일 정리
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        print("진행 파일 삭제")

    print("\n✅ 전체 완료!")


if __name__ == "__main__":
    main()
