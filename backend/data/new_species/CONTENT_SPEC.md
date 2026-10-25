# 신규 종 콘텐츠 생성 스펙 (조경종 배치, 2026-09)

배정받은 종 각각에 대해 아래 스키마의 JSON 객체를 생성한다.
출력 파일: 배열 형태 `[ {종1}, {종2}, ... ]`, UTF-8, 지정된 batch 파일 경로에 저장.

## 절대 규칙

1. **사실만 쓴다.** 확신 없는 신화·전설·역사는 지어내지 않는다. MYTH 장르는 실제 전승이 있을 때만 쓰고, 없으면 EPISODE/ART/HISTORY로 대체한다.
2. **문체**: stories, usage, management, habitat, seasonDescription은 **습니다체**. preContent만 **~이다체 한 문장(95자 이내)**.
3. **stories는 정확히 4개**, 마지막은 반드시 SCIENCE. 앞 3개는 EPISODE/MYTH/HISTORY/ART 중 그 종에 맞는 3개. 각 스토리는 2문장.
4. enum 값은 아래 허용값만 사용 (오타·변형 금지).

## 필드 스키마

```json
{
  "name": "(입력값 그대로)",
  "scientificName": "(입력값 그대로)",
  "isRepresentative": true,
  "taxonomy": {
    "genus": "학명 첫 단어",
    "species": "학명 둘째 단어",
    "family": "한글 과명 (예: 국화과, 장미과, 물푸레나무과)"
  },
  "horticulture": {
    "category": "숙근초|일년초|구근식물|조경수목|화목|관목|덩굴식물|수생식물|다육식물 중 1",
    "categoryGroup": "나무와 조경|꽃과 풀|텃밭과 정원 중 1 (교목·관목·침엽수→나무와 조경, 초화·구근·그라스→꽃과 풀, 허브·식용→텃밭과 정원)",
    "usage": ["조경·활용 용도 설명 2~3문장, 습니다체"],
    "management": "관리법 2~3문장 (햇빛·물·전정·월동 등 실질 정보), 습니다체",
    "preContent": "~이다체 한 문장, 95자 이내. 카드에 표시되는 요약."
  },
  "habitat": "원산지와 국내 식재 환경 설명 1~2문장, 습니다체",
  "stories": [
    {"genre": "EPISODE|MYTH|HISTORY|ART", "content": "2문장, 습니다체"},
    {"genre": "…", "content": "…"},
    {"genre": "…", "content": "…"},
    {"genre": "SCIENCE", "content": "형태·생태 특징 2문장, 습니다체"}
  ],
  "season": "SPRING|SUMMER|FALL|WINTER (개화 중심 계절. 단풍·열매 관상수는 그 계절)",
  "bloomingMonths": [개화 월 정수 배열, 1~12. 침엽수 등 꽃 관상 아닌 종은 관상 최성기 월],
  "seasonDescription": "개화(관상) 시기 설명 2문장, 습니다체",
  "searchKeywords": ["이름", "별명/이명", "영명 한글표기", "과명", "용도·특징 키워드 등 6~9개"],
  "popularity_score": 0,
  "colorInfo": {
    "hexCodes": ["#RRGGBB", "..."],
    "colorLabels": ["대표색 먼저 (칩은 첫 라벨 기준)", "..."],
    "colorGroup": ["백색/미색|노랑/주황|빨강/분홍|푸른색|초록/연두|갈색/검정 중 해당값들"]
  },
  "scentInfo": {
    "scentTags": ["구체적 향 표현 1~3개"],
    "scentGroup": ["은은·차분|싱그러운·시원|달콤·화사|무향 중 해당값들"]
  },
  "flowerInfo": {
    "language": "꽃말 (실제 통용되는 것)",
    "flowerGroup": "사랑/고백|위로/슬픔|감사/존경|이별/그리움|행복/즐거움 중 1"
  }
}
```

## 넣지 않는 필드

`_id`, `images`, `imageUrl`, `imageCredits`, `searchTokens`, `view_count` — 이후 파이프라인에서 부여한다.

## 색상 규칙

- colorLabels 첫 값 = 그 식물의 대표 꽃색(관엽·침엽은 잎색). 색상 칩이 첫 라벨로 그려지므로 순서 중요.
- colorGroup은 라벨들이 속한 그룹을 전부 나열 (중복 제거).
- 예: 블루세이지 → hexCodes ["#4169E1"], colorLabels ["파랑"], colorGroup ["푸른색"]

## 품질 기준 (개망초 _id 2164 예시 수준)

- 스토리는 그 종 고유의 이야기여야 한다. "아름다운 꽃입니다" 류의 어느 종에나 붙는 문장 금지.
- 한국 조경 맥락(아파트 화단, 가로수, 공원 등)을 아는 사람이 쓴 것처럼: 실제 식재 위치·계절 풍경을 언급하면 좋다.
- 학명·과명·개화기는 정확해야 한다. 모르면 그 종을 배정자에게 반려 목록으로 보고(파일 끝에 "_rejected" 배열)하고 지어내지 않는다.
