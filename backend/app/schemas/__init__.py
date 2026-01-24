from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelCaseModel(BaseModel):
    """
    공통 베이스 모델: Python 내부에서는 snake_case,
    JSON 직렬화(API 응답) 시에는 camelCase로 자동 변환
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # snake_case로도 접근 가능
        from_attributes=True,   # ORM/dict → Pydantic 변환 허용
    )


# Re-export: CamelCaseModel 정의 후에 import해야 순환 참조 방지
from app.schemas.plant import (
    Season,
    StoryGenre,
    Story,
    Taxonomy,
    Horticulture,
    ColorInfo,
    ScentInfo,
    FlowerInfo,
    Plant,
    PlantCardDto,
    PlantDetailDto,
    PlantExploreDto,
    PlantSearchResultDto,
)
from app.schemas.user import (
    UserBase,
    UserLoginRequest,
    UserResponse,
    UserUpdate,
)

__all__ = [
    # Base
    "CamelCaseModel",
    # Plant schemas
    "Season",
    "StoryGenre",
    "Story",
    "Taxonomy",
    "Horticulture",
    "ColorInfo",
    "ScentInfo",
    "FlowerInfo",
    "Plant",
    "PlantCardDto",
    "PlantDetailDto",
    "PlantExploreDto",
    "PlantSearchResultDto",
    # User schemas
    "UserBase",
    "UserLoginRequest",
    "UserResponse",
    "UserUpdate",
]
