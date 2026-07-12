# track2. floripedia_v2.json(_id>1500)의 이미지 커버리지 갭 복구.
"""
2부(_id>1500) 이미지 문제 종 복구 스크립트.

대상: imageUrl이 비었거나(수집 미완) http:// 원본 링크(미러링 미완, 대개 죽음)인 종.
      → 전부 v2 2부(_id>1500). 1부(≤1500)는 이미 Firebase 미러링 완료라 대상 아님.

동작:
  --dry-run (기본): iNaturalist + Wikimedia에서 학명으로 이미지 후보 검색만.
      종별 찾음/못찾음 + 선정 URL을 report로 출력. Firebase/DB/파일 변경 없음.
  --commit: 선정 이미지 다운로드 → 800px 리사이즈 → Firebase 업로드 →
      floripedia_v2.json + MongoDB의 images/imageUrl 갱신.

iNat/Wikimedia는 API 키 불필요. Pexels는 키 없으면 자동 skip.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
import ssl
from io import BytesIO
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BACKEND_DIR / "data" / "floripedia_v2.json"
REPORT_FILE = BACKEND_DIR / "data" / "fix_missing_images_report.json"
FIREBASE_CRED_PATH = BACKEND_DIR / "app" / "core" / "firebase-key.json"

MAX_WIDTH = 800
JPEG_QUALITY = 85
REQUEST_TIMEOUT = 20

ssl_ctx = ssl.create_default_context()


def load_env():
    env = {}
    for line in (BACKEND_DIR / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def api_get(url, headers=None, timeout=20, retries=3):
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=headers or {})
        req.add_header("User-Agent", "FloripediaBot/1.0 (image-collector; contact@floripedia.app)")
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep((attempt + 1) * 5)
                continue
            return None
        except Exception:
            return None
    return None


# ── iNaturalist (종 정확도 최고) ──
INAT_ALLOWED = {"cc0", "cc-by", "cc-by-sa"}

def search_inaturalist(sci, per_page=15):
    if not sci:
        return []
    enc = urllib.parse.quote(sci)
    url = (f"https://api.inaturalist.org/v1/observations?taxon_name={enc}"
           f"&quality_grade=research&photos=true&per_page={per_page}"
           f"&order=desc&order_by=votes&photo_license=cc0,cc-by,cc-by-sa")
    data = api_get(url)
    if not data or "results" not in data:
        return []
    out = []
    for obs in data["results"]:
        for photo in obs.get("photos", [])[:2]:
            lic = (photo.get("license_code") or "").lower()
            if lic not in INAT_ALLOWED:
                continue
            orig = photo.get("url", "").replace("square", "original")
            if not orig:
                continue
            disp = {"cc0": "CC0 1.0", "cc-by": "CC BY 4.0", "cc-by-sa": "CC BY-SA 4.0"}.get(lic, lic.upper())
            user = obs.get("user", {})
            who = photo.get("attribution", user.get("login", "Unknown"))
            if " " in who and "(" in who:
                who = who.split("(")[0].strip()
            if len(who) > 60:
                who = user.get("login", "Unknown")
            out.append({"url": orig, "source": "iNaturalist", "photographer": who,
                        "license": disp, "sourceUrl": f"https://www.inaturalist.org/observations/{obs['id']}",
                        "attribution": f"{who}, {disp} (iNaturalist)", "width": 0, "height": 0})
    time.sleep(0.5)
    return out


# ── Wikimedia Commons (fallback) ──
def search_wikimedia(sci, per_page=10):
    if not sci:
        return []
    enc = urllib.parse.quote(sci)
    url = (f"https://commons.wikimedia.org/w/api.php?action=query&format=json"
           f"&generator=search&gsrnamespace=6&gsrsearch={enc}&gsrlimit={per_page}"
           f"&prop=imageinfo&iiprop=url|extmetadata|size|user|mime&iiurlwidth=1200")
    data = api_get(url)
    if not data or "query" not in data or "pages" not in data["query"]:
        return []
    IMG_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp")
    out = []
    for _, page in data["query"]["pages"].items():
        ii = page.get("imageinfo", [])
        if not ii:
            continue
        info = ii[0]
        # 이미지 파일만 (PDF/SVG/TIF/DjVu 등 문서 제외)
        mime = (info.get("mime") or "").lower()
        title_l = page.get("title", "").lower()
        if not mime.startswith("image/") or mime in ("image/svg+xml", "image/tiff"):
            if not title_l.endswith(IMG_EXT):
                continue
        meta = info.get("extmetadata", {})
        lic_short = meta.get("LicenseShortName", {}).get("value", "").lower().strip()
        code = lic_short.replace(" ", "-").replace("_", "-")
        if "nc" in code:
            continue
        allowed = (any(a in code for a in ["cc0", "cc-zero", "public-domain", "pd"])
                   or ("cc-by-sa" in code and "nc" not in code)
                   or ("cc-by" in code and "sa" not in code and "nc" not in code))
        if not allowed:
            continue
        orig = info.get("url", "")
        who = meta.get("Artist", {}).get("value", info.get("user", "Unknown"))
        who = re.sub(r"<[^>]+>", "", who).strip()
        if len(who) > 80:
            who = info.get("user", "Unknown")
        disp = lic_short.upper() if lic_short else "Unknown"
        title = page.get("title", "").replace("File:", "")
        out.append({"url": orig or info.get("thumburl", ""), "source": "Wikimedia Commons",
                    "photographer": who, "license": disp,
                    "sourceUrl": f"https://commons.wikimedia.org/wiki/File:{urllib.parse.quote(title)}",
                    "attribution": f"{who}, {disp} (Wikimedia Commons)",
                    "width": info.get("width", 0), "height": info.get("height", 0)})
    time.sleep(0.5)
    return out


# ── GBIF Occurrence media (한국 표본 사진 다수, 무키) ──
def search_gbif(sci, limit=20):
    if not sci:
        return []
    enc = urllib.parse.quote(sci)
    url = (f"https://api.gbif.org/v1/occurrence/search?scientificName={enc}"
           f"&mediaType=StillImage&limit={limit}")
    data = api_get(url)
    if not data or "results" not in data:
        return []
    out = []
    IMG_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp")
    for occ in data["results"]:
        occ_lic = (occ.get("license") or "").lower()
        for m in occ.get("media", []):
            if (m.get("type") or "").lower() not in ("stillimage", ""):
                continue
            ident = m.get("identifier", "")
            if not ident or not ident.startswith("http"):
                continue
            # 직접 이미지 URL만 (HTML 랜딩페이지 제외): format이 image/* 이거나 확장자가 이미지
            fmt = (m.get("format") or "").lower()
            if not (fmt.startswith("image/") or ident.lower().split("?")[0].endswith(IMG_EXT)):
                continue
            lic = (m.get("license") or occ_lic or "").lower()
            # NC/ND 제외 (광고 수익 앱), CC 또는 PD만 허용
            if "nc" in lic or "-nd" in lic:
                continue
            if not any(a in lic for a in ["creativecommons", "cc0", "publicdomain", "cc_by", "cc-by"]):
                continue
            who = m.get("creator") or m.get("rightsHolder") or "Unknown"
            disp = "CC0" if ("cc0" in lic or "publicdomain" in lic) else \
                   ("CC BY-SA" if "by-sa" in lic else "CC BY")
            out.append({"url": ident, "source": "GBIF", "photographer": who,
                        "license": disp,
                        "sourceUrl": f"https://www.gbif.org/occurrence/{occ.get('key','')}",
                        "attribution": f"{who}, {disp} (GBIF)", "width": 0, "height": 0})
            break  # 관찰당 1장
    time.sleep(0.3)
    return out


def collect_for(sci):
    """iNat → GBIF → Wikimedia 순으로 후보 수집."""
    cands = search_inaturalist(sci)
    if not cands:
        cands = search_gbif(sci)
    if not cands:
        cands = search_wikimedia(sci)
    return cands


def is_target(p):
    u = p.get("imageUrl")
    return (not u) or u.startswith("http://")


# ── 커밋(A2): 다운로드→리사이즈→Firebase 업로드→DB/파일 갱신 ──
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def download_and_resize(url):
    """이미지 다운로드 → RGB 변환 → 800px 리사이즈 → JPEG 바이트. 실패 시 예외."""
    import requests
    from io import BytesIO
    from PIL import Image
    headers = {"User-Agent": BROWSER_UA, "Referer": url, "Accept": "image/*,*/*;q=0.8"}
    last = None
    for attempt in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=25, allow_redirects=True)
            r.raise_for_status()
            ct = r.headers.get("Content-Type", "").lower()
            if "html" in ct or "image" not in ct:
                raise ValueError(f"이미지 아님 (Content-Type={ct})")
            img = Image.open(BytesIO(r.content))
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
                img = img.resize((MAX_WIDTH, int(img.height * ratio)), Image.LANCZOS)
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            return buf.getvalue()
        except Exception as e:
            last = e
            if attempt < 2:
                time.sleep(1 * (attempt + 1))
    raise last


def run_commit(plants, limit):
    """리포트의 chosen_url을 Firebase로 미러링하고 floripedia_v2.json + MongoDB 갱신."""
    import firebase_admin
    from firebase_admin import credentials, storage
    from pymongo import MongoClient

    env = load_env()
    if not firebase_admin._apps:
        cred = credentials.Certificate(str(FIREBASE_CRED_PATH))
        bucket_name = env.get("FIREBASE_STORAGE_BUCKET", "floripedia-c0bf0.firebasestorage.app")
        firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})
    bucket = storage.bucket()

    report = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
    todo = [r for r in report if r.get("chosen_url")]
    if limit:
        todo = todo[:limit]
    print(f"[COMMIT] 대상: {len(todo)}종 (Firebase 미러링 + DB/파일 갱신)\n")

    pmap = {p["_id"]: p for p in plants}
    client = MongoClient(env["MONGO_URI"])
    col = client[env.get("MONGODB_DB_NAME", "floripedia")]["plants"]

    committed, failed = [], []
    for i, r in enumerate(todo):
        pid = r["_id"]
        try:
            data = download_and_resize(r["chosen_url"])
            blob = bucket.blob(f"plants/{pid}/0.jpg")
            blob.upload_from_string(data, content_type="image/jpeg")
            blob.make_public()
            fb = blob.public_url
            p = pmap.get(pid)
            if p is not None:
                p["imageUrl"] = fb
                p["images"] = [fb]
            col.update_one({"_id": pid}, {"$set": {"imageUrl": fb, "images": [fb]}})
            committed.append(pid)
            print(f"[{i+1}/{len(todo)}] {pid} {r['name']} ✓ {len(data)//1024}KB [{r.get('source')}]")
        except Exception as e:
            failed.append({"_id": pid, "name": r["name"],
                           "source": r.get("source"), "error": str(e)[:70]})
            print(f"[{i+1}/{len(todo)}] {pid} {r['name']} ✗ {str(e)[:55]}")

    # floripedia_v2.json 저장 (성공분 반영)
    DATA_FILE.write_text(json.dumps(plants, ensure_ascii=False, indent=2), encoding="utf-8")
    client.close()

    result = {"committed": committed, "failed": failed}
    (DATA_FILE.parent / "commit_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== 커밋 완료: 성공 {len(committed)} / 실패 {len(failed)} ===")
    for f in failed:
        print(f"  ✗ {f['_id']} {f['name']} [{f['source']}] {f['error']}")
    print(f"floripedia_v2.json 갱신됨, 결과: commit_result.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true", help="실제 Firebase 업로드 + DB/파일 갱신")
    ap.add_argument("--limit", type=int, default=0, help="처리 종 수 제한 (0=전체)")
    ap.add_argument("--misses-only", action="store_true",
                    help="이전 리포트에서 chosen_url이 없는 종만 재처리 후 리포트 병합")
    args = ap.parse_args()
    dry = not args.commit

    plants = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    # COMMIT 모드: 수집 없이 리포트의 확정 URL을 미러링
    if args.commit:
        run_commit(plants, args.limit)
        return

    targets = [p for p in plants if is_target(p)]

    prev_report = {}
    if args.misses_only and REPORT_FILE.exists():
        prev = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
        prev_report = {r["_id"]: r for r in prev}
        miss_ids = {r["_id"] for r in prev if not r.get("chosen_url")}
        targets = [p for p in targets if p["_id"] in miss_ids]
        print(f"[misses-only] 이전 리포트의 미발견 {len(targets)}종만 재처리\n")

    if args.limit:
        targets = targets[:args.limit]
    print(f"대상 종: {len(targets)} (모드: {'DRY-RUN' if dry else 'COMMIT'})\n")

    fb_bucket = None
    if not dry:
        import firebase_admin
        from firebase_admin import credentials, storage
        if not firebase_admin._apps:
            cred = credentials.Certificate(str(FIREBASE_CRED_PATH))
            env = load_env()
            bucket_name = env.get("FIREBASE_STORAGE_BUCKET", "floripedia-c0bf0.firebasestorage.app")
            firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})
        fb_bucket = storage.bucket()

    report = []
    found = miss = 0
    for i, p in enumerate(targets):
        pid, name, sci = p["_id"], p.get("name", ""), p.get("scientificName", "")
        cands = collect_for(sci)
        if cands:
            best = cands[0]
            found += 1
            status = "FOUND"
            report.append({"_id": pid, "name": name, "scientificName": sci,
                           "chosen_url": best["url"], "source": best["source"],
                           "license": best["license"], "n_candidates": len(cands)})
        else:
            miss += 1
            status = "MISS"
            report.append({"_id": pid, "name": name, "scientificName": sci,
                           "chosen_url": None, "n_candidates": 0})
        print(f"[{i+1}/{len(targets)}] {pid} {name} ({sci}) -> {status}"
              + (f" [{cands[0]['source']}]" if cands else ""))

    if args.misses_only and prev_report:
        for r in report:
            prev_report[r["_id"]] = r  # 재처리 결과로 덮어쓰기
        merged = list(prev_report.values())
        REPORT_FILE.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        tot_found = sum(1 for r in merged if r.get("chosen_url"))
        print(f"\n=== 병합 리포트 ===\n이번 재처리: 찾음 {found} / 못찾음 {miss} (총 {len(targets)})")
        print(f"전체 누적: 찾음 {tot_found} / 못찾음 {len(merged)-tot_found} (총 {len(merged)})")
        print(f"리포트 저장: {REPORT_FILE}")
        if dry:
            print("\nDRY-RUN 모드 — 변경 없음.")
        return

    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== 리포트 ===\n찾음: {found}  못찾음: {miss}  (총 {len(targets)})")
    print(f"리포트 저장: {REPORT_FILE}")
    if dry:
        print("\nDRY-RUN 모드 — 아무것도 변경하지 않음. --commit 으로 실제 반영.")


if __name__ == "__main__":
    main()
