"""
도메인 열거값 단일 소스 (Single Source of Truth).

파이프라인(pipeline/scripts/validate.py)과 앱이 이 값들을 공유한다.
과거엔 validate.py·스키마 docstring·안드로이드 세 곳에 각각 하드코딩돼 드리프트가 났다.
백엔드 쪽은 여기서 import 해 쓴다. (안드로이드는 언어가 달라 별도 상수 파일 필요)
"""

STORY_GENRES = frozenset({"SCIENCE", "HISTORY", "EPISODE", "ART", "MYTH"})

# 카테고리 그룹: 앱 필터가 쓰는 정규 4종.
# (과거 DB에 '풀과 들꽃'·'구근'·'수생' 354종이 섞여 필터에 안 잡히던 것을 정리해 편입 완료)
CATEGORY_GROUPS = frozenset({
    "꽃과 풀", "나무와 조경", "실내 인테리어", "텃밭과 정원",
})

COLOR_GROUPS = frozenset({
    "빨강/분홍", "푸른색", "백색/미색", "노랑/주황", "갈색/검정", "초록/연두",
})

SCENT_GROUPS = frozenset({
    "은은·차분", "싱그러운·시원", "달콤·화사", "무향",
})

FLOWER_GROUPS = frozenset({
    "사랑/고백", "감사/존경", "행복/즐거움", "위로/슬픔", "이별/그리움",
})
