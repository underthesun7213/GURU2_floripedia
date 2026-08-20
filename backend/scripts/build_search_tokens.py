# -*- coding: utf-8 -*-
"""
검색 substring 오매칭 완화용 searchTokens 사전 계산 (2026-08-20).

배경: 키워드 검색이 꽃말·searchKeywords에 substring regex라 "향" 검색에
"하늘을 향한 마음"(향하다=동사), "그리운 고향"(단어 중간), "운향과"(과명)처럼
향기와 무관한 결과가 걸렸다. 형태소 분석기는 EC2 런타임에 올리기엔 무거워서,
여기(개발머신)서 kiwipiepy로 식물별 검색 토큰을 미리 계산해 searchTokens
필드로 저장하고, 서버는 토큰 prefix 매칭만 한다.

토큰 규칙 (꽃말 + searchKeywords 각 구문 대상):
  - 형태소 중 명사류(NNG/NNP/NR)·어근(XR)·외래어(SL)만, 2글자 이상
    ("향한"은 동사라 탈락, "고향"은 향-prefix가 아니라 미매칭.
     "운향과"→[운,향] 같은 1글자 오분절이 "향" 검색에 걸리는 것도 길이로 차단)
  - 원문 구문 전체(소문자)도 토큰에 포함 — "운향과" 직접 검색이나
    "강한 향기" 같은 다어절 prefix 검색 보존
  - 이름(name)은 substring 매칭을 유지하므로 대상 아님

  py scripts/build_search_tokens.py                # DRY-RUN (기본 '향' 검증 리포트 포함)
  py scripts/build_search_tokens.py --check 사랑    # 다른 키워드로 검증
  py scripts/build_search_tokens.py --commit       # DB + v2.json 반영
"""
import sys, os, io, json, argparse
sys.path.insert(0, ".")
import certifi
from pymongo import MongoClient, UpdateOne
from app.core.config import settings

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
V2 = os.path.join(DATA, "floripedia_v2.json")

KEEP_TAGS = {"NNG", "NNP", "NR", "XR", "SL"}
MIN_LEN = 2


def build_tokens(kiwi, language, keywords):
    toks = set()
    sources = [language or ""] + [k for k in (keywords or []) if k]
    for src in sources:
        s = src.strip()
        if not s:
            continue
        toks.add(s.lower())
        for t in kiwi.tokenize(s):
            if t.tag in KEEP_TAGS and len(t.form) >= MIN_LEN:
                toks.add(t.form.lower())
        # 1글자 명사는 오분절 노이즈("운향과"→운/향)가 많아 위에서 길이로 걸렀지만,
        # 단어 끝 접미로 쓰인 경우("초콜릿향"·"만리향"의 香)는 단독 검색("향") 대상이라 살린다.
        for w in s.split():
            for t in kiwi.tokenize(w):
                if t.tag in KEEP_TAGS and len(t.form) == 1 and t.start + 1 == len(w):
                    toks.add(t.form.lower())
    return sorted(toks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--check", default="향", help="검증 리포트용 검색 키워드")
    args = ap.parse_args()
    dry = not args.commit
    print(f"=== searchTokens 빌드 ({'DRY-RUN' if dry else 'COMMIT'}) ===")

    try:
        from kiwipiepy import Kiwi
    except ImportError:
        raise SystemExit("ERROR: kiwipiepy 미설치 — `pip install kiwipiepy` (개발머신 전용, 서버 requirements 아님)")
    kiwi = Kiwi()

    c = MongoClient(settings.MONGO_URI, tlsCAFile=certifi.where())
    db = c[settings.MONGODB_DB_NAME]
    docs = list(db.plants.find({}, {"_id": 1, "name": 1, "flowerInfo": 1, "searchKeywords": 1, "searchTokens": 1}))

    plan = []  # (_id, name, tokens)
    for d in docs:
        lang = (d.get("flowerInfo") or {}).get("language") or ""
        tokens = build_tokens(kiwi, lang, d.get("searchKeywords"))
        if tokens != d.get("searchTokens"):
            plan.append((d["_id"], d["name"], tokens))
    print(f"갱신 대상 {len(plan)}종 / 전체 {len(docs)}종")
    print("\n샘플 5:")
    for pid, name, tokens in plan[:5]:
        print(f"  [{name}] {tokens}")

    # 검증: 기존 substring 매칭 vs 새 토큰 prefix 매칭 비교 (이름 매칭 제외한 순수 꽃말/키워드 기준)
    kw = args.check.lower()
    token_map = {pid: t for pid, _, t in plan}
    dropped, kept = [], []
    for d in docs:
        lang = ((d.get("flowerInfo") or {}).get("language") or "").lower()
        sks = [k.lower() for k in (d.get("searchKeywords") or [])]
        old = kw in lang or any(kw in k for k in sks)
        tokens = token_map.get(d["_id"], d.get("searchTokens") or [])
        new = any(t.startswith(kw) for t in tokens)
        if old and not new:
            dropped.append((d["name"], lang, sks))
        elif old and new:
            kept.append(d["name"])
    print(f"\n[검증] 키워드 '{kw}': 꽃말/키워드 매칭 기존 {len(dropped) + len(kept)}종 → 유지 {len(kept)}종, 제외 {len(dropped)}종")
    for name, lang, sks in dropped:
        print(f"  제외: {name} (꽃말='{lang}', keywords={sks})")

    if dry:
        print("\nDRY-RUN — 변경 없음. --commit 으로 반영.")
        c.close()
        return

    # DB 반영
    if plan:
        res = db.plants.bulk_write(
            [UpdateOne({"_id": pid}, {"$set": {"searchTokens": tokens}}) for pid, _, tokens in plan],
            ordered=False,
        )
        print(f"\n[DB] {res.modified_count}종 searchTokens 갱신")

    # v2.json 동기화 (시드 원본에도 반영해 재시딩 시 유지)
    if os.path.exists(V2):
        data = json.load(io.open(V2, encoding="utf-8"))
        n2 = 0
        for p in data:
            lang = (p.get("flowerInfo") or {}).get("language") or ""
            tokens = build_tokens(kiwi, lang, p.get("searchKeywords"))
            if p.get("searchTokens") != tokens:
                p["searchTokens"] = tokens
                n2 += 1
        json.dump(data, io.open(V2, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"[v2] {n2}종 동기화")
    c.close()
    print("\n=== 완료 ===")


if __name__ == "__main__":
    main()
