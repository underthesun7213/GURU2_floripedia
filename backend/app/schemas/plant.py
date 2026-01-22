# app/schemas/plant.py
from pydantic import Field, ConfigDict
from typing import List, Optional
from enum import Enum
from pydantic import model_validator

from app.schemas import CamelCaseModel

# ==========================================
# 1. 공통 열거형(Enums) 정의
# ==========================================

class Season(str, Enum):
    """식물의 주요 계절 정의"""
    SPRING = "SPRING"
    SUMMER = "SUMMER"
    FALL = "FALL"
    WINTER = "WINTER"

class StoryGenre(str, Enum):
    """AI가 생성한 스토리의 장르 분류"""
    MYTH = "MYTH"         # 신화/전설/민담
    SCIENCE = "SCIENCE"   # 식물학적 정보/생태적 특징
    HISTORY = "HISTORY"   # 역사적 사실/관련 인물
    ART = "ART"           # 문학/예술/시/그림
    EPISODE = "EPISODE"   # 재미있는 에피소드/TMI

# ==========================================
# 2. 하위 구조 스키마 (Nested Models)
# ==========================================

class Story(CamelCaseModel):
    """식물에 얽힌 스토리 정보"""
    genre: StoryGenre  # 장르 (Enum 사용)
    content: str       # 스토리 본문 내용

class Taxonomy(CamelCaseModel):
    """
    식물의 학술적 분류 정보.

    [TODO] family 필드 데이터 정제 필요
    현재 DB 내 family 값에 조사가 포함되거나("수선화과에", "난과의")
    부정확한 데이터가 존재함. 현재 버전에서는 미사용 필드이나,
    향후 분류 기반 검색/필터 기능 개발 시 데이터 클리닝 필수.
    """
    genus: str         # 속 (예: Juniperus)
    species: str       # 종 (예: chinensis)
    family: str        # 과 (예: 측백나무과) - 데이터 정제 필요

class Horticulture(CamelCaseModel):
    """
    식물의 원예 및 관리 정보.

    [categoryGroup 허용값]
    - 나무와 조경
    - 꽃과 풀
    - 열매와 채소
    - 실내 인테리어
    """
    category: str                       # 화훼 부류 (예: 조경수목, 일년초, 숙근초)
    category_group: str                 # 카테고리 그룹 (4대 분류)
    usage: List[str]                    # 이용 부위 및 목적 (예: 관상용, 정원수)
    management: Optional[str] = None    # 물주기, 햇빛 등 구체적인 관리법
    pre_content: Optional[str] = None   # 사전 설명 내용


class ColorInfo(CamelCaseModel):
    """
    식물의 색상 정보.

    [colorGroup 허용값]
    - 백색/미색
    - 노랑/주황
    - 푸른색
    - 갈색/검정
    """
    hex_codes: List[str]                # 대표 색상 HEX 코드 목록
    color_labels: List[str]             # 색상 레이블 (예: 검정, 갈색)
    color_group: List[str]              # 색상 그룹


class ScentInfo(CamelCaseModel):
    """
    식물의 향기 정보.

    [scentGroup 허용값]
    - 달콤·화사
    - 싱그럽고 시원
    - 은은·차분
    - 향 없음
    """
    scent_tags: List[str]               # 향기 태그 (예: 숲속의, 은은한)
    scent_group: List[str]              # 향기 그룹


class FlowerInfo(CamelCaseModel):
    """
    꽃말 정보.

    [flowerGroup 허용값]
    - 사랑/고백
    - 위로/슬픔
    - 감사/존경
    - 이별/그리움
    - 행복/즐거움
    - 기타
    """
    language: str                       # 꽃말 (예: 영원한 향기)
    flower_group: str                   # 꽃말 그룹

# ==========================================
# 3. 메인 식물 스키마 (Main Models)
# ==========================================

class Plant(CamelCaseModel):
    """식물 전체 정보를 담는 메인 모델"""

    # MongoDB의 _id(문자열)를 API 응답에서는 id로 사용합니다.
    id: str = Field(alias="_id")

    name: str                                   # 한글 이름 (예: 향나무)
    scientific_name: str                        # 학명 (예: Juniperus chinensis)
    is_representative: bool = True              # 대표종 여부 (기본값 True)

    taxonomy: Taxonomy                          # 학술 분류 정보
    horticulture: Horticulture                  # 원예/관리 정보

    habitat: str                                # 자연 서식지 설명
    flower_info: FlowerInfo                     # 꽃말 정보

    stories: List[Story]                        # AI가 생성한 다채로운 스토리들 (최대 5개)

    images: List[str] = Field(default_factory=list) # 이미지 경로 3개 리스트
    image_url: Optional[str] = Field(None)      # 대표 이미지 저장 경로/URL

    season: Season                              # 대표 계절 (Enum 사용)
    blooming_months: List[int]                  # 개화 시기 (1~12월 숫자 리스트)
    search_keywords: List[str]                  # 검색 최적화를 위한 키워드 뭉치
    popularity_score: int = 0                   # 인기도 점수

    color_info: ColorInfo                       # 색상 정보
    scent_info: ScentInfo                       # 향기 정보

    # Pydantic V2 설정: CamelCaseModel 설정을 확장
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        from_attributes=True
    )

# ==========================================
# 4. 리스트/검색결과 화면에서 성능 최적화를 위해 사용하는 경량 모델(DTO)
# ==========================================

class PlantCardDto(CamelCaseModel):
    """리스트/검색결과/꽃갈피 화면용 경량 모델 (평탄화 적용)"""
    id: str = Field(alias="_id")
    name: str
    flower_language: str  # FlowerInfo 객체 대신 문자열만 추출 (평탄화 1)
    image_url: str
    season: Season
    pre_content: str      # Horticulture 내부에서 추출 (평탄화 2)

    @model_validator(mode='before')
    @classmethod
    def flatten_data(cls, data: dict) -> dict:
        """MongoDB 문서(camelCase)를 평탄화"""
        # 1. flowerInfo.language -> flower_language로 평탄화
        flower_info = data.get('flowerInfo') or data.get('flower_info')
        if flower_info and isinstance(flower_info, dict):
            data['flower_language'] = flower_info.get('language', '')

        # 2. horticulture.preContent -> pre_content로 평탄화
        horticulture = data.get('horticulture')
        if horticulture and isinstance(horticulture, dict):
            data['pre_content'] = horticulture.get('preContent') or horticulture.get('pre_content', '')

        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        from_attributes=True
    )

# ==========================================
# 5. 안드로이드 상세 화면용 최종 응답 스키마(DTO)
# ==========================================

class PlantDetailDto(Plant):
    """상세페이지용 DTO - Plant 상속 + is_favorite 필드"""

    is_favorite: bool = False

    # 부모(Plant)의 use_enum_values=True를 유지하기 위해 명시적으로 설정
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        from_attributes=True
    )

# ==========================================
# 6. 탐색(Explore) 화면용 DTO 
# ==========================================

class PlantExploreDto(CamelCaseModel):
    """
    탐색(상황별 추천) 결과 DTO
    - 텍스트 기반 AI 추천 결과
    - Gemini 추천사 포함
    """
    id: str = Field(alias="_id")
    name: str
    image_url: str
    
    # 원예 정보 (평탄화)
    category: str                       # horticulture.category
    season: Season
    
    # 향기 (평탄화)
    scent_tags: List[str]              # scent_info.scent_tags
    
    # 색상 (첫번째만, 평탄화)
    hex_code: str                      # color_info.hex_codes[0]
    color_label: str                   # color_info.color_labels[0]
    
    # Gemini 추천사 (동적 생성 필드, 300~500자 감성 에세이 줄글)
    recommendation: str
    
    @model_validator(mode='before')
    @classmethod
    def flatten_data(cls, data: dict) -> dict:
        """MongoDB 문서(camelCase)를 평탄화"""
        # horticulture.category 추출
        horticulture = data.get('horticulture')
        if horticulture and isinstance(horticulture, dict):
            data['category'] = horticulture.get('category', '')

        # scentInfo.scentTags 추출
        scent_info = data.get('scentInfo') or data.get('scent_info')
        if scent_info and isinstance(scent_info, dict):
            data['scent_tags'] = scent_info.get('scentTags') or scent_info.get('scent_tags', [])

        # colorInfo에서 첫번째 요소만 추출
        color_info = data.get('colorInfo') or data.get('color_info')
        if color_info and isinstance(color_info, dict):
            hex_codes = color_info.get('hexCodes') or color_info.get('hex_codes', [])
            color_labels = color_info.get('colorLabels') or color_info.get('color_labels', [])

            data['hex_code'] = hex_codes[0] if hex_codes else "#000000"
            data['color_label'] = color_labels[0] if color_labels else "기타"

        # recommendation은 Service에서 추가되므로 여기서는 처리 안함

        return data
    
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        from_attributes=True
    )


# ==========================================
# 7. 이미지 기반 식물 검색 응답 DTO(추후 게이미피케이션 활용)
# ==========================================

class PlantSearchResultDto(Plant): 
    is_newly_created: bool = Field(..., description="DB에 새로 생성된 식물인지 여부")
    is_favorite: bool = Field(False, description="찜 여부")
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        from_attributes=True
    )