"""
Plant 도메인 모델.

MongoDB 문서 스키마 + 내부 비즈니스 로직을 정의한다.
외부 의존성이 없는 순수 계산/검증 로직만 포함.
"""
from typing import ClassVar
from pydantic import Field

from app.schemas import CamelCaseModel


class PlantModel(CamelCaseModel):
    """
    Plant 도메인 모델 - 런타임 필드 + 내부 로직.

    [용도]
    - MongoDB 런타임 추가 필드 스키마 정의
    - 인기도 계산 등 순수 비즈니스 로직 제공

    [참고]
    전체 Plant 스키마는 app/schemas/plant.py 참조
    """

    # 런타임 추가 필드 (Repository에서 $inc로 관리)
    view_count: int = Field(default=0, description="조회수")
    favorite_count: int = Field(default=0, description="찜한 유저 수")
    popularity_score: int = Field(default=0, description="인기도 점수")

    # ==========================================
    # 인기도 계산 로직 (내부 비즈니스 규칙)
    # ==========================================

    # 가중치 상수 (ClassVar로 선언하여 Pydantic 필드가 아닌 클래스 변수로 인식)
    VIEW_WEIGHT: ClassVar[int] = 1
    FAVORITE_WEIGHT: ClassVar[int] = 10

    @classmethod
    def calculate_popularity_delta(
        cls, view_delta: int = 0, favorite_delta: int = 0
    ) -> int:
        """
        인기도 변화량 계산.

        순수 함수 - 외부 의존성 없음.

        Args:
            view_delta: 조회수 변화량 (보통 +1)
            favorite_delta: 찜 수 변화량 (+1 또는 -1)

        Returns:
            popularity_score에 더할 값
        """
        return (view_delta * cls.VIEW_WEIGHT) + (favorite_delta * cls.FAVORITE_WEIGHT)