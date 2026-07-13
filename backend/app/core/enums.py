"""
도메인 열거값 단일 소스 (Single Source of Truth).

파이프라인(pipeline/scripts/validate.py)과 앱이 이 값들을 공유한다.
과거엔 validate.py·스키마 docstring·안드로이드 세 곳에 각각 하드코딩돼 드리프트가 났다.
백엔드 쪽은 여기서 import 해 쓴다. (안드로이드는 언어가 달라 별도 상수 파일 필요)

⚠️ categoryGroup은 현재 DB에 비표준 값이 섞여 있어(예: '풀과 들꽃' 351종, '구근', '수생')
   정규 세트가 확정되기 전까지 화이트리스트에 넣지 않는다. — 데이터 정리 후 추가할 것.
"""

STORY_GENRES = frozenset({"SCIENCE", "HISTORY", "EPISODE", "ART", "MYTH"})

COLOR_GROUPS = frozenset({
    "빨강/분홍", "푸른색", "백색/미색", "노랑/주황", "갈색/검정", "초록/연두",
})

SCENT_GROUPS = frozenset({
    "은은·차분", "싱그러운·시원", "달콤·화사", "무향",
})

FLOWER_GROUPS = frozenset({
    "사랑/고백", "감사/존경", "행복/즐거움", "위로/슬픔", "이별/그리움",
})
