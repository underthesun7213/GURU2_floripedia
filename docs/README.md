# Floripedia Phase 2 Stories 생성 — Claude Code 인계 패키지

> v2 신규 640종(_id 1501~)에 stories·colorInfo·scentInfo·flowerInfo·preContent 채우기
> 기존 v1 1부 366종의 톤·구조에 맞춰서

---

## 현재 위치 (Floripedia repo 이식 후)

이 작업 패키지는 Floripedia 프로젝트로 이식되었습니다.

- 마스터 데이터: `backend/data/floripedia_v2.json`
- 작업 영역: `backend/pipeline/stories/` (PROMPT_TEMPLATE.md, sample_v1_reference.json, genre_examples.md, chunks.json, _content.py, _meta_*.txt)
- 검증 스크립트: `backend/pipeline/scripts/validate.py`
- 임시 스크립트: `backend/pipeline/_scratch/`

## 시작 방법

Claude Code 실행 후 다음 한 줄로 시작:

```
backend/pipeline/stories/PROMPT_TEMPLATE.md 읽고, backend/pipeline/stories/sample_v1_reference.json의 톤을 참고해서 backend/data/floripedia_v2.json의 _id 1501~1510 (10종) stories를 채워줘. 결과를 보여주면 검토할게.
```

10종 잘 나오면 50종씩 청크로 확장. 한 번에 50~100종씩 처리 권장 (Max 5x 한도 5시간 윈도우 고려).

검증:
```
python backend/pipeline/scripts/validate.py
```

---

## 핵심 원칙

### 1. 1부 톤 답습
v1 1부 366종은 인문학 도감 톤의 **정답지**. 이걸 톤 레퍼런스로 따라가기.

- 말투: **존댓말**(~습니다, ~됩니다)이 기본. 단 EPISODE 장르는 **반말 에세이체**도 허용 (개인 경험 반영)
- 길이: 평균 **120~130자**, 최대 200자, 최소 80자
- 종당 **3~4개 stories** (3개가 218종, 4개가 144종 — 3개를 기본으로)

### 2. 5개 장르 균형
v1 1부 분포 비율:
- **SCIENCE 39%** (494/1250) — 학명 어원, 화학 성분, 식물학적 특징
- **HISTORY 26%** (322) — 도입 역사, 문헌 기록, 시대적 사용
- **EPISODE 15%** (190) — 한국 현대 일상의 식물, 추억, 작가 단상
- **ART 11%** (133) — 회화·문학·조각에서의 등장
- **MYTH 9%** (111) — 신화·전설·민담

신규 종도 비슷한 비율이 나오도록. 단 강제는 아님 — 종에 따라 신화가 없으면 SCIENCE/HISTORY로 채우기.

### 3. 사실 정확성 — KPNI 본문이 1차 소스
- KPNI N_PLANT_SPECIES의 활용_내용·특이사항_내용·환경_내용에 **사실 신호** 존재
- 외부 인문 지식 (신화·문학·문화사) 추가는 OK, 단 **검증 가능한 것만**
- ❌ 만들어내기 금지: "어떤 시인이 이 꽃을 노래했다고 전해진다" 식의 모호한 출처
- ⭕ 안전: "조선시대 사대부들은 ~로 활용했다", "OO 신화에 등장한다" (실제 출처 있을 때만)

### 4. 종별 메타 활용
v2 항목에 이미 들어있음:
- `taxonomy.family` — 같은 family 식물의 일반 특성 가져올 때
- `bloomingMonths` — 계절 묘사 정확히
- `habitat` — 자생지 표현
- `horticulture.usage` — 활용 방식 (밀원, 약재, 관상 등)
- `_kpni_meta.flower_text_source` — 꽃 형태·색·향기 묘사의 원천

---

## 워크플로우

### 청크 단위 처리

청크 1 (10종) — 워밍업, 톤 검증
청크 2~13 (50종 × 12) — 본격 생성  
청크 14 (남은 30종) — 마무리

50종당 추정 토큰: 입력 50K + 출력 30K = 약 80K. Max 5x 5시간 한도(약 88K) 거의 한도 직전. **분할 추천**: 50종을 2번에 나눠 25종씩.

### 검증 단계

각 청크 끝낸 후:
1. `python backend/pipeline/scripts/validate.py` 실행 — 길이/장르 분포/필수 필드 검증
2. 사용자가 5~10종 샘플 검토
3. 문제 있으면 프롬프트 수정 후 재생성
4. OK면 다음 청크

---

## 파일 구조

| 파일 | 용도 |
|---|---|
| `docs/README.md` | 이 문서 |
| `backend/pipeline/stories/PROMPT_TEMPLATE.md` | LLM에게 줄 프롬프트 (Claude Code가 사용) |
| `backend/pipeline/stories/sample_v1_reference.json` | v1 1부 stories 샘플 30종 (톤 레퍼런스) |
| `backend/pipeline/stories/genre_examples.md` | 5개 장르별 좋은 예시 / 피해야 할 패턴 |
| `backend/pipeline/stories/chunks.json` | 640종을 50종씩 청크로 나눔 |
| `backend/pipeline/stories/_content.py` | 청크별 생성 콘텐츠 기록 (톤 레퍼런스) |
| `backend/pipeline/scripts/validate.py` | 생성된 stories 자동 검증 |
| `backend/data/floripedia_v2.json` | 마스터 데이터 (결과 반영 대상) |

---

## 생성 대상 필드

각 v2 항목에서 채울 것:

```json
{
  "stories": [
    {"genre": "SCIENCE", "content": "..."},
    {"genre": "HISTORY", "content": "..."},
    {"genre": "...", "content": "..."}
  ],
  "colorInfo": {
    "hexCodes": ["#...", "#..."],
    "colorLabels": ["..."],
    "colorGroup": ["빨강/분홍" | "푸른색" | "백색/미색" | "노랑/주황" | "갈색/검정"]
  },
  "scentInfo": {
    "scentTags": ["은은한", ...],
    "scentGroup": ["은은·차분" | "싱그러운·시원" | "달콤·화사" | "무향"]
  },
  "flowerInfo": {
    "language": "꽃말 한 줄",
    "flowerGroup": "사랑/고백" | "감사/존경" | "행복/즐거움" | "위로/슬픔" | "이별/그리움"
  },
  "horticulture.preContent": "이 식물의 분류·원산·종류 개요 (200~400자)"
}
```
