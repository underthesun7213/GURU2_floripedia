from datetime import datetime, timezone
from typing import List
from pydantic import Field, EmailStr

from app.schemas import CamelCaseModel


def _utc_now() -> datetime:
    """UTC 기준 현재 시각 반환 (timezone-aware)"""
    return datetime.now(timezone.utc)


class UserModel(CamelCaseModel):
    """
    User 도메인 모델.

    MongoDB 'users' 컬렉션 문서 구조 + 기본값 정의.
    """
    # 1. 고유 식별 정보
    email: EmailStr = Field(..., description="사용자 이메일 (Unique Key 역할)")
    auth_provider: str = Field(default="google", description="인증 제공자 (현재는 google 고정)")

    # 2. 사용자 프로필 (최소 정보만 저장)
    nickname: str = Field(default="식물 탐험가")
    profile_image_url: str = Field(default="/assets/logo_placeholder.png")

    # 3. 서비스 데이터
    favorite_plant_ids: List[str] = Field(default_factory=list, description="사용자가 하트를 누른 식물 ID 목록")

    # 4. 관리용 데이터
    is_active: bool = Field(default=True, description="활성 계정 여부 (탈퇴 시 False)")
    is_terms_agreed: bool = Field(default=True, description="약관 동의 여부")
    created_at: datetime = Field(default_factory=_utc_now, description="가입 시각 (UTC)")
    updated_at: datetime = Field(default_factory=_utc_now, description="마지막 수정 시각 (UTC)")
