# DORMANT (Phase1). track2에서 backend/data/floripedia_v2.json 기준으로 입력 재배선 필요.
"""
식물 이미지 URL 수집 스크립트
- Pexels → iNaturalist → Wikimedia Commons 순서로 검색
- 각 식물당 최대 3장 URL 수집 (다운로드 없음)
- 체크포인트로 중단 후 이어하기 가능
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import ssl
import io
from pathlib import Path

# Windows 콘솔 인코딩 설정
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── 경로 설정 ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
INPUT_FILE = DATA_DIR / "v2_data_patched.json"
OUTPUT_FILE = DATA_DIR / "v2_data_with_images.json"
CHECKPOINT_FILE = DATA_DIR / "image_checkpoint.json"
FAILED_FILE = DATA_DIR / "failed_images.json"

# ── .env 로드 ──────────────────────────────────────────────
def load_env():
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env()
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")

# ── SSL 컨텍스트 (Windows 호환) ────────────────────────────
ssl_ctx = ssl.create_default_context()

# ── HTTP 유틸 ──────────────────────────────────────────────
def api_get(url: str, headers: dict = None, timeout: int = 20, retries: int = 3) -> dict | None:
    """GET 요청 → JSON 파싱. 429 시 백오프 재시도. 실패 시 None."""
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=headers or {})
        req.add_header("User-Agent", "FloripediaBot/1.0 (image-collector; contact@floripedia.app)")
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = (attempt + 1) * 5  # 5s, 10s, 15s
                print(f"  [429 Rate Limit] {wait}s 대기 후 재시도...")
                time.sleep(wait)
                continue
            print(f"  [HTTP {e.code}] {url[:100]}...")
            return None
        except Exception as e:
            print(f"  [ERROR] {url[:80]}... -> {e}")
            return None
    return None


# ── 1. Pexels 검색 ─────────────────────────────────────────
def search_pexels(scientific_name: str, per_page: int = 10) -> list[dict]:
    """
    Pexels에서 학명으로만 검색.
    한국어 이름으로 검색하면 무관한 일반 꽃 사진이 반환되므로 학명만 사용.
    """
    if not PEXELS_API_KEY or not scientific_name:
        return []

    results = []
    # 1차: 전체 학명
    encoded = urllib.parse.quote(scientific_name)
    url = f"https://api.pexels.com/v1/search?query={encoded}&per_page={per_page}"
    data = api_get(url, headers={"Authorization": PEXELS_API_KEY})
    if data and "photos" in data:
        for photo in data["photos"]:
            results.append({
                "url": photo["src"]["large2x"],
                "thumbnail": photo["src"]["medium"],
                "width": photo["width"],
                "height": photo["height"],
                "source": "Pexels",
                "photographer": photo.get("photographer", "Unknown"),
                "license": "Pexels License (Commercial OK)",
                "sourceUrl": photo["url"],
                "attribution": f"Photo by {photo.get('photographer', 'Unknown')} on Pexels",
            })
    time.sleep(0.2)

    # 결과 없으면 속명(genus)으로 재시도
    if not results:
        genus = scientific_name.split()[0] if " " in scientific_name else ""
        if genus and len(genus) > 2:
            encoded = urllib.parse.quote(f"{genus} flower plant")
            url = f"https://api.pexels.com/v1/search?query={encoded}&per_page={per_page}"
            data = api_get(url, headers={"Authorization": PEXELS_API_KEY})
            if data and "photos" in data:
                for photo in data["photos"]:
                    results.append({
                        "url": photo["src"]["large2x"],
                        "thumbnail": photo["src"]["medium"],
                        "width": photo["width"],
                        "height": photo["height"],
                        "source": "Pexels",
                        "photographer": photo.get("photographer", "Unknown"),
                        "license": "Pexels License (Commercial OK)",
                        "sourceUrl": photo["url"],
                        "attribution": f"Photo by {photo.get('photographer', 'Unknown')} on Pexels",
                    })
            time.sleep(0.2)

    # 중복 제거
    seen = set()
    unique = []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)
    return unique


# ── 2. iNaturalist 검색 ────────────────────────────────────
INAT_ALLOWED_LICENSES = {"cc0", "cc-by", "cc-by-sa"}

def search_inaturalist(scientific_name: str, per_page: int = 15) -> list[dict]:
    """iNaturalist에서 research grade 관찰 사진 검색. 종 정확도가 가장 높음."""
    if not scientific_name:
        return []

    encoded = urllib.parse.quote(scientific_name)
    url = (
        f"https://api.inaturalist.org/v1/observations?"
        f"taxon_name={encoded}"
        f"&quality_grade=research"
        f"&photos=true"
        f"&per_page={per_page}"
        f"&order=desc&order_by=votes"
        f"&photo_license=cc0,cc-by,cc-by-sa"
    )
    data = api_get(url)
    if not data or "results" not in data:
        return []

    results = []
    for obs in data["results"]:
        photos = obs.get("photos", [])
        user = obs.get("user", {})
        for photo in photos[:2]:  # 관찰당 최대 2장
            license_code = (photo.get("license_code") or "").lower()
            if license_code not in INAT_ALLOWED_LICENSES:
                continue
            original_url = photo.get("url", "").replace("square", "original")
            if not original_url:
                continue
            medium_url = photo.get("url", "").replace("square", "medium")
            license_display = {
                "cc0": "CC0 1.0",
                "cc-by": "CC BY 4.0",
                "cc-by-sa": "CC BY-SA 4.0",
            }.get(license_code, license_code.upper())

            photographer = photo.get("attribution", user.get("login", "Unknown"))
            if " " in photographer and "(" in photographer:
                photographer = photographer.split("(")[0].strip()
            if len(photographer) > 60:
                photographer = user.get("login", "Unknown")

            results.append({
                "url": original_url,
                "thumbnail": medium_url,
                "width": 0,
                "height": 0,
                "source": "iNaturalist",
                "photographer": photographer,
                "license": license_display,
                "sourceUrl": f"https://www.inaturalist.org/observations/{obs['id']}",
                "attribution": f"{photographer}, {license_display} (iNaturalist)",
            })
    time.sleep(0.5)
    return results


# ── 3. Wikimedia Commons 검색 ──────────────────────────────
def search_wikimedia(scientific_name: str, per_page: int = 10) -> list[dict]:
    """Wikimedia Commons에서 이미지 검색. fallback 소스."""
    if not scientific_name:
        return []

    encoded = urllib.parse.quote(scientific_name)
    url = (
        f"https://commons.wikimedia.org/w/api.php?"
        f"action=query&format=json"
        f"&generator=search&gsrnamespace=6&gsrsearch={encoded}"
        f"&gsrlimit={per_page}"
        f"&prop=imageinfo&iiprop=url|extmetadata|size|user"
        f"&iiurlwidth=1200"
    )
    data = api_get(url)
    if not data or "query" not in data or "pages" not in data["query"]:
        return []

    results = []
    for page_id, page in data["query"]["pages"].items():
        imageinfo_list = page.get("imageinfo", [])
        if not imageinfo_list:
            continue
        info = imageinfo_list[0]
        meta = info.get("extmetadata", {})

        license_short = meta.get("LicenseShortName", {}).get("value", "").lower().strip()
        license_code = license_short.replace(" ", "-").replace("_", "-")
        # NC 포함 시 제외 (광고 수익 앱이므로)
        if "nc" in license_code:
            continue
        # 허용 라이선스 체크
        allowed = False
        if any(al in license_code for al in ["cc0", "cc-zero", "public-domain", "pd"]):
            allowed = True
        elif "cc-by-sa" in license_code and "nc" not in license_code:
            allowed = True
        elif "cc-by" in license_code and "sa" not in license_code and "nc" not in license_code:
            allowed = True
        if not allowed:
            continue

        image_url = info.get("thumburl") or info.get("url", "")
        original_url = info.get("url", "")
        photographer = meta.get("Artist", {}).get("value", info.get("user", "Unknown"))
        photographer = re.sub(r"<[^>]+>", "", photographer).strip()
        if len(photographer) > 80:
            photographer = info.get("user", "Unknown")

        license_display = license_short.upper() if license_short else "Unknown"
        title = page.get("title", "").replace("File:", "")

        results.append({
            "url": original_url if original_url else image_url,
            "thumbnail": image_url,
            "width": info.get("width", 0),
            "height": info.get("height", 0),
            "source": "Wikimedia Commons",
            "photographer": photographer,
            "license": license_display,
            "sourceUrl": f"https://commons.wikimedia.org/wiki/File:{urllib.parse.quote(title)}",
            "attribution": f"{photographer}, {license_display} (Wikimedia Commons)",
        })

    time.sleep(0.5)
    return results


# ── 이미지 선택 (종 정확도 우선 휴리스틱) ────────────────────
def select_best_images(candidates: list[dict], count: int = 3) -> list[dict]:
    """
    후보 이미지 중 최적 3장 선택.
    우선순위: 종 정확도(iNat research > Wikimedia > Pexels) > 해상도 > 비율
    """
    if len(candidates) <= count:
        return candidates

    def score(img):
        s = 0
        # 종 정확도 점수 (가장 중요)
        if img["source"] == "iNaturalist":
            s += 50  # research grade = 종 정확도 최고
        elif img["source"] == "Wikimedia Commons":
            s += 30  # 학명 카테고리 기반 = 높은 정확도
        elif img["source"] == "Pexels":
            s += 10  # 학명 검색이지만 관련성 불확실

        # 해상도 점수
        w, h = img.get("width", 0), img.get("height", 0)
        if w > 0 and h > 0:
            pixels = w * h
            if pixels > 4_000_000:
                s += 20
            elif pixels > 2_000_000:
                s += 15
            elif pixels > 1_000_000:
                s += 10
            # 좋은 비율 (정방형~세로)
            ratio = h / w if w > 0 else 1
            if 0.7 <= ratio <= 1.5:
                s += 5
        else:
            s += 8  # 크기 미제공 (iNat)
        return s

    candidates.sort(key=score, reverse=True)

    # 소스 다양성: 가능하면 다른 소스에서 선택
    selected = []
    sources_used = set()
    for c in candidates:
        if c["source"] not in sources_used and len(selected) < count:
            selected.append(c)
            sources_used.add(c["source"])
    for c in candidates:
        if len(selected) >= count:
            break
        if c not in selected:
            selected.append(c)
    return selected[:count]


# ── 체크포인트 관리 ────────────────────────────────────────
def load_checkpoint() -> dict:
    if CHECKPOINT_FILE.exists():
        return json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
    return {"completed": {}, "last_index": -1}

def save_checkpoint(cp: dict):
    CHECKPOINT_FILE.write_text(json.dumps(cp, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 메인 처리 ──────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Floripedia 이미지 URL 수집 스크립트 v2")
    print("=" * 60)

    plants = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    print(f"\n총 {len(plants)}건 식물 데이터 로드")

    # 기존 출력 파일 로드
    if OUTPUT_FILE.exists():
        output_plants = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
        output_map = {p["_id"]: p for p in output_plants}
        print(f"기존 출력 파일 로드: {len(output_map)}건")
    else:
        output_map = {}

    # 체크포인트 로드
    checkpoint = load_checkpoint()
    completed_ids = set(checkpoint.get("completed", {}).keys())
    print(f"체크포인트: {len(completed_ids)}건 완료됨\n")

    failed = []
    stats = {"pexels": 0, "inaturalist": 0, "wikimedia": 0, "failed": 0, "skipped": 0}

    for i, plant in enumerate(plants):
        pid = plant["_id"]
        name = plant.get("name", "")
        sci_name = plant.get("scientificName", "")

        if pid in completed_ids:
            stats["skipped"] += 1
            continue

        print(f"[{i+1}/{len(plants)}] {name} ({sci_name})")

        all_candidates = []

        # 1순위: Pexels (학명으로만 검색)
        try:
            pexels_results = search_pexels(sci_name)
            if pexels_results:
                all_candidates.extend(pexels_results)
                print(f"  Pexels: {len(pexels_results)}장")
        except Exception as e:
            print(f"  Pexels error: {e}")

        # 2순위: iNaturalist (종 정확도 최고)
        try:
            inat_results = search_inaturalist(sci_name)
            if inat_results:
                all_candidates.extend(inat_results)
                print(f"  iNaturalist: {len(inat_results)}장")
        except Exception as e:
            print(f"  iNaturalist error: {e}")

        # 3순위: Wikimedia (항상 검색 - fallback 보장)
        try:
            wiki_results = search_wikimedia(sci_name)
            if wiki_results:
                all_candidates.extend(wiki_results)
                print(f"  Wikimedia: {len(wiki_results)}장")
        except Exception as e:
            print(f"  Wikimedia error: {e}")

        # 최적 3장 선택
        if all_candidates:
            selected = select_best_images(all_candidates, count=3)
            images = []
            for img in selected:
                images.append({
                    "url": img["url"],
                    "source": img["source"],
                    "photographer": img["photographer"],
                    "license": img["license"],
                    "sourceUrl": img["sourceUrl"],
                    "attribution": img["attribution"],
                })
                key = img["source"].lower().replace(" ", "").replace("commons", "")
                if "pexels" in key:
                    stats["pexels"] += 1
                elif "naturalist" in key:
                    stats["inaturalist"] += 1
                elif "wiki" in key or "media" in key:
                    stats["wikimedia"] += 1

            plant_copy = dict(plant)
            plant_copy["images"] = images
            plant_copy["imageUrl"] = images[0]["url"] if images else ""
            output_map[pid] = plant_copy

            print(f"  -> {len(images)}장 OK ({', '.join(img['source'] for img in images)})")
        else:
            failed.append({
                "_id": pid,
                "name": name,
                "scientificName": sci_name,
                "reason": "No images found from any source",
            })
            stats["failed"] += 1
            if pid not in output_map:
                output_map[pid] = dict(plant)
            print(f"  -> FAILED (no images)")

        checkpoint["completed"][pid] = True
        checkpoint["last_index"] = i
        completed_ids.add(pid)

        # 20건마다 저장
        if (i + 1) % 20 == 0 or i == len(plants) - 1:
            ordered = [output_map.get(p["_id"], p) for p in plants]
            OUTPUT_FILE.write_text(
                json.dumps(ordered, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            save_checkpoint(checkpoint)
            if failed:
                FAILED_FILE.write_text(
                    json.dumps(failed, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            done = len(completed_ids)
            pct = done * 100 // len(plants)
            print(f"  [checkpoint: {done}/{len(plants)} ({pct}%)]\n")

    # 최종 저장
    ordered = [output_map.get(p["_id"], p) for p in plants]
    OUTPUT_FILE.write_text(json.dumps(ordered, ensure_ascii=False, indent=2), encoding="utf-8")
    save_checkpoint(checkpoint)
    if failed:
        FAILED_FILE.write_text(json.dumps(failed, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 60)
    print("  Collection Report")
    print("=" * 60)
    total = len(plants)
    ok = total - stats["failed"] - stats["skipped"]
    print(f"  Total plants:    {total}")
    print(f"  Skipped:         {stats['skipped']}")
    print(f"  Success:         {ok}")
    print(f"  Failed:          {stats['failed']}")
    print(f"  Pexels images:   {stats['pexels']}")
    print(f"  iNat images:     {stats['inaturalist']}")
    print(f"  Wikimedia imgs:  {stats['wikimedia']}")
    print(f"\n  Output: {OUTPUT_FILE}")
    if failed:
        print(f"  Failed: {FAILED_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
