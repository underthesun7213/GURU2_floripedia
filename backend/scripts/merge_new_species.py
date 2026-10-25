"""
신규 종 배치(batch_*.json) 병합 + 검증.

- data/new_species/batch_*.json 을 모두 읽어 스키마·enum·규칙 검증
- 통과 시 data/new_species/merged.json 생성 (_id 미부여 상태)
- 기존 floripedia_v2.json 과 이름/학명 중복 최종 확인

사용:
    python scripts/merge_new_species.py            # 검증 리포트만
    python scripts/merge_new_species.py --commit   # merged.json 생성
"""
import argparse
import glob
import json
import os
import sys

BASE = os.path.join(os.path.dirname(__file__), "..", "data")
NEW_DIR = os.path.join(BASE, "new_species")
V2 = os.path.join(BASE, "floripedia_v2.json")

SEASONS = {"SPRING", "SUMMER", "FALL", "WINTER"}
GENRES = {"MYTH", "SCIENCE", "HISTORY", "ART", "EPISODE"}
COLOR_GROUPS = {"백색/미색", "노랑/주황", "빨강/분홍", "푸른색", "초록/연두", "갈색/검정"}
SCENT_GROUPS = {"은은·차분", "싱그러운·시원", "달콤·화사", "무향"}
FLOWER_GROUPS = {"사랑/고백", "위로/슬픔", "감사/존경", "이별/그리움", "행복/즐거움"}
CATEGORY_GROUPS = {"나무와 조경", "꽃과 풀", "텃밭과 정원", "실내 인테리어"}
FORBIDDEN = {"_id", "images", "imageUrl", "imageCredits", "searchTokens", "view_count"}
REQUIRED = {"name", "scientificName", "isRepresentative", "taxonomy", "horticulture",
            "habitat", "stories", "season", "bloomingMonths", "seasonDescription",
            "searchKeywords", "popularity_score", "colorInfo", "scentInfo", "flowerInfo"}


def check(p, errors):
    name = p.get("name", "<이름없음>")

    def err(msg):
        errors.append(f"{name}: {msg}")

    missing = REQUIRED - set(p.keys())
    if missing:
        err(f"필수 필드 누락 {sorted(missing)}")
    bad = FORBIDDEN & set(p.keys())
    if bad:
        err(f"금지 필드 포함 {sorted(bad)}")

    if p.get("season") not in SEASONS:
        err(f"season 오류: {p.get('season')}")
    months = p.get("bloomingMonths", [])
    if not months or not all(isinstance(m, int) and 1 <= m <= 12 for m in months):
        err(f"bloomingMonths 오류: {months}")

    stories = p.get("stories", [])
    if len(stories) != 4:
        err(f"stories {len(stories)}개 (4개 필요)")
    else:
        if stories[-1].get("genre") != "SCIENCE":
            err("마지막 스토리가 SCIENCE 아님")
        for s in stories:
            if s.get("genre") not in GENRES:
                err(f"장르 오류: {s.get('genre')}")
            if not s.get("content"):
                err("스토리 내용 없음")

    ci = p.get("colorInfo", {})
    if not set(ci.get("colorGroup", [])) <= COLOR_GROUPS or not ci.get("colorGroup"):
        err(f"colorGroup 오류: {ci.get('colorGroup')}")
    if not ci.get("colorLabels") or not ci.get("hexCodes"):
        err("colorLabels/hexCodes 누락")
    si = p.get("scentInfo", {})
    if not set(si.get("scentGroup", [])) <= SCENT_GROUPS or not si.get("scentGroup"):
        err(f"scentGroup 오류: {si.get('scentGroup')}")
    fi = p.get("flowerInfo", {})
    if fi.get("flowerGroup") not in FLOWER_GROUPS:
        err(f"flowerGroup 오류: {fi.get('flowerGroup')}")
    if not fi.get("language"):
        err("꽃말 없음")

    h = p.get("horticulture", {})
    if h.get("categoryGroup") not in CATEGORY_GROUPS:
        err(f"categoryGroup 오류: {h.get('categoryGroup')}")
    if not h.get("preContent"):
        err("preContent 없음")
    elif len(h["preContent"]) > 110:
        err(f"preContent {len(h['preContent'])}자 (110자 초과)")

    tax = p.get("taxonomy", {})
    sci_words = p.get("scientificName", "").split()
    if sci_words and tax.get("genus") != sci_words[0]:
        err(f"taxonomy.genus({tax.get('genus')}) ≠ 학명 속({sci_words[0]})")
    if not tax.get("family", "").endswith("과"):
        err(f"family 형식 확인 필요: {tax.get('family')}")

    if not (5 <= len(p.get("searchKeywords", [])) <= 10):
        err(f"searchKeywords {len(p.get('searchKeywords', []))}개 (5~10개 권장)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    plants, errors, rejected = [], [], []
    for f in sorted(glob.glob(os.path.join(NEW_DIR, "batch_*.json"))):
        data = json.load(open(f, encoding="utf-8"))
        for item in data:
            if isinstance(item, dict) and "name" in item:
                plants.append((os.path.basename(f), item))
            else:
                rejected.append((os.path.basename(f), item))

    # 배치 간 이름 중복
    seen = {}
    for src, p in plants:
        if p["name"] in seen:
            errors.append(f"{p['name']}: 배치 간 중복 ({seen[p['name']]} vs {src})")
        seen[p["name"]] = src

    # 기존 v2와 최종 중복 확인 (이름 + 속·종)
    v2 = json.load(open(V2, encoding="utf-8"))
    v2_names = {e["name"] for e in v2}
    v2_sci = set()
    for e in v2:
        w = (e.get("scientificName") or "").lower().split()
        if len(w) >= 2:
            v2_sci.add((w[0], w[1]))
    for src, p in plants:
        if p["name"] in v2_names:
            errors.append(f"{p['name']}: 기존 v2에 동일 이름 존재")
        w = p["scientificName"].lower().split()
        if len(w) >= 2 and (w[0], w[1].strip("'")) in v2_sci:
            errors.append(f"{p['name']}: 기존 v2에 동일 학명 존재 ({p['scientificName']})")

    # 개별 검증 + 숙근버베나 별칭 보정
    for src, p in plants:
        if p["name"] == "숙근버베나" and "버들마편초" not in p.get("searchKeywords", []):
            p["searchKeywords"].append("버들마편초")
        check(p, errors)

    print(f"배치 파일 종 수: {len(plants)} | _rejected 항목: {len(rejected)}")
    if errors:
        print(f"\n검증 실패 {len(errors)}건:")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    print("검증 전부 통과")

    if args.commit:
        out = os.path.join(NEW_DIR, "merged.json")
        json.dump([p for _, p in plants], open(out, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"저장: {out} ({len(plants)}종)")


if __name__ == "__main__":
    main()
