from pydantic import EmailStr, Field, ConfigDict
from typing import List, Optional
from datetime import datetime

from app.schemas import CamelCaseModel


class UserBase(CamelCaseModel):
    """
    유저의 공통 필드 정의
    - DB 저장 및 조회 시 공통적으로 사용되는 필드들
    """
    email: EmailStr = Field(..., description="사용자 구글 이메일")
    nickname: str = Field(default="식물 탐험가", description="앱 내 표시될 별명")
    
    # 기본값은 로컬 placeholder 이미지로 설정.
    profile_image_url: Optional[str] = Field(
        default="https://your-default-image-url.com/placeholder.png", 
        description="프로필 이미지 경로 (Firebase Storage URL 또는 기본 이미지)"
    )


class UserLoginRequest(CamelCaseModel):
    """안드로이드에서 로그인 요청 시 보낼 데이터 규격"""
    id_token: str = Field(..., description="Firebase에서 발급받은 구글 ID Token")


class UserResponse(UserBase):
    """
    안드로이드로 내보낼 유저 정보
    UserBase를 상속받았기 때문에 email, nickname, profile_image_url이 모두 포함됨.
    """
    id: str = Field(..., alias="_id", description="MongoDB의 고유 ID (문자열)")
    favorite_plant_ids: List[str] = Field(default_factory=list, description="찜한 식물 ID 리스트")
    created_at: datetime = Field(..., description="가입 일시")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )


class UserUpdate(CamelCaseModel):
    """회원 정보 수정 시 사용할 규격"""
    nickname: Optional[str] = None
    profile_image_url: Optional[str] = None