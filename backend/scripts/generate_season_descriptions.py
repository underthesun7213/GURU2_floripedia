# -*- coding: utf-8 -*-
"""
seasonDescription 없는 종에 대해 Gemini로 생성해 DB + floripedia_v2.json 동시 반영.

배경: 2026-07 생성분(1060종)이 DB에만 기록되고 v2.json에 동기화되지 않아,
이후 재시딩에서 전량 유실됨. 재생성하며 이번에는 v2.json에도 함께 기록한다.

  py scripts/generate_season_descriptions.py --count       # 대상 규모만
  py scripts/generate_season_descriptions.py --pilot 5     # 미리보기(저장 X)
  py scripts/generate_season_descriptions.py --commit      # 실제 반영(배치마다 DB+v2 저장)
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, ".")
import certifi
from pymongo import MongoClient, UpdateOne
from google import genai

from app.core.config import settings

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
V2 = os.path.join(DATA, "floripedia_v2.json")

SEASON_KO = {"SPRING": "봄", "SUMMER": "여름", "FALL": "가을", "WINTER": "겨울"}

PROMPT = (
    "식물 도감 앱의 상세 화면에서 '개화(관상) 시기' 섹션에 들어갈 설명을 작성해 주세요.\n"
    "식물: {name} ({sci})\n"
    "대표 계절: {season} / 개화·관상 월: {months}\n"
    "참고(서식·특징): {hint}\n\n"
    "규칙:\n"
    "- 정확히 2문장, 정중한 '~습니다체'.\n"
    "- 첫 문장은 개화(또는 관상 최성기) 시기를 자연스럽게 풀어 쓰고, "
    "둘째 문장은 그 계절의 실제 풍경이나 관찰 포인트를 담으세요.\n"
    "- 주어진 월 범위와 모순되는 내용 금지. 새로운 사실을 지어내지 마세요.\n"
    "- 결과는 본문만 출력하세요(따옴표·머리말 없이).\n"
)


def build_prompt(p):
    months = p.get("bloomingMonths") or []
    months_str = ", ".join(f"{m}월" for m in months) if months else "정보 없음"
    hint = (p.get("habitat") or "")[:120] or (p.get("horticulture", {}).get("preContent") or "")[:120]
    return PROMPT.format(
        name=p["name"], sci=p.get("scientificName", ""),
        season=SEASON_KO.get(p.get("season", ""), p.get("season", "")),
        months=months_str, hint=hint,
    )


def generate(client, model, p, retries=3):
    last = None
    for _ in range(retries):
        try:
            r = client.models.generate_content(model=model, contents=[build_prompt(p)])
            t = (r.text or "").strip().strip('"').strip()
            # 최소 품질 가드: 습니다체 2문장 안팎, 과도한 길이 차단
            if t and 20 <= len(t) <= 400 and "니다" in t:
                return t
            last = f"형식 미달: {t[:50]!r}"
        except Exception as e:
            last = e
            time.sleep(2)
    print(f"   [WARN] {p['_id']} {p['name']} 생성 실패: {last}")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", action="store_true")
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--model", default=settings.GEMINI_BASIC_MODEL)
    args = ap.parse_args()

    c = MongoClient(settings.MONGO_URI, tlsCAFile=certifi.where())
    db = c[settings.MONGODB_DB_NAME]

    targets = list(db.plants.find(
        {"$or": [{"seasonDescription": {"$exists": False}},
                 {"seasonDescription": {"$in": ["", None]}}]},
        {"_id": 1, "name": 1, "scientificName": 1, "season": 1,
         "bloomingMonths": 1, "habitat": 1, "horticulture.preContent": 1},
    ))
    print(f"대상: {len(targets)}종 (seasonDescription 없음)")
    if args.count:
        return

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    if args.pilot:
        for p in targets[: args.pilot]:
            t = generate(client, args.model, p)
            print(f"\n[{p['_id']}] {p['name']}\n  -> {t}")
        print("\n(pilot 모드 — 저장 안 함)")
        return

    if not args.commit:
        print("--commit 으로 실제 반영 (--pilot N 으로 미리보기)")
        return

    if args.limit:
        targets = targets[: args.limit]

    v2 = json.load(open(V2, encoding="utf-8"))
    v2_map = {e["_id"]: e for e in v2}

    done, failed = 0, []
    ops = []
    for i, p in enumerate(targets, 1):
        t = generate(client, args.model, p)
        if not t:
            failed.append(p["_id"])
            continue
        ops.append(UpdateOne({"_id": p["_id"]}, {"$set": {"seasonDescription": t}}))
        if p["_id"] in v2_map:
            v2_map[p["_id"]]["seasonDescription"] = t
        done += 1
        # 50건마다 중간 저장 (중단돼도 진행분 보존)
        if ops and (i % 50 == 0 or i == len(targets)):
            db.plants.bulk_write(ops, ordered=False)
            ops = []
            json.dump(v2, open(V2, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"[{i}/{len(targets)}] 누적 {done}건 저장 (DB+v2)")

    print(f"\n완료: {done}건 생성 | 실패 {len(failed)}건: {failed[:10]}")


if __name__ == "__main__":
    main()
