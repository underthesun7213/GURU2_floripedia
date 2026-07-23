from pydantic import EmailStr, Field, ConfigDict
from typing import List, Optional
from datetime import datetime

from app.schemas import CamelCaseModel


# ==========================================
# 레벨 시스템 상수 & 헬퍼
# ==========================================

LEVEL_THRESHOLDS = [
    (1, "씨앗", 0),
    (2, "새싹", 30),
    (3, "떡잎", 70),
    (4, "어린잎", 130),
    (5, "줄기", 210),
    (6, "꽃봉오리", 320),
    (7, "꽃송이", 460),
    (8, "식물 탐험가", 640),
    (9, "식물 전문가", 870),
    (10, "식물 마스터", 1150),
]

MAX_LEVEL = len(LEVEL_THRESHOLDS)  # 10


def compute_level(total_exp: int) -> int:
    """누적 경험치로 레벨(1~MAX_LEVEL) 계산. EXP/레벨 계산 단일 소스."""
    level = 1
    for lv, _, threshold in LEVEL_THRESHOLDS:
        if total_exp >= threshold:
            level = lv
    return level


def compute_level_info(total_exp: int, level: int, discovered_count: int = 0) -> dict:
    """레벨 정보를 계산하여 LevelInfo dict 반환"""
    # 레벨 범위 방어 (1~MAX_LEVEL)
    level = max(1, min(level, MAX_LEVEL))
    # 현재 레벨의 임계값과 다음 레벨의 임계값
    current_threshold = LEVEL_THRESHOLDS[level - 1][2]  # 현재 레벨 시작 EXP
    # 만렙이면 다음 임계값이 없으므로 nextLevelExp=0 (안드로이드가 게이지 꽉 참으로 처리)
    next_threshold = (
        LEVEL_THRESHOLDS[level][2] if level < MAX_LEVEL else current_threshold
    )
    title = LEVEL_THRESHOLDS[level - 1][1]

    return {
        "level": level,
        "title": title,
        "totalExp": total_exp,
        "currentLevelExp": total_exp - current_threshold,
        "nextLevelExp": next_threshold - current_threshold,
        "discoveredPlantCount": discovered_count,
    }


# ==========================================
# 스키마 정의
# ==========================================

class LevelInfo(CamelCaseModel):
    """레벨 시스템 DTO"""
    level: int = Field(..., description="현재 레벨 (1~10)")
    title: str = Field(..., description="레벨 칭호")
    total_exp: int = Field(..., description="누적 경험치")
    current_level_exp: int = Field(..., description="현재 레벨 내 경험치")
    next_level_exp: int = Field(..., description="다음 레벨까지 필요 경험치")
    discovered_plant_count: int = Field(default=0, description="발견한 식물 수")


class UserBase(CamelCaseModel):
    """
    유저의 공통 필드 정의
    - DB 저장 및 조회 시 공통적으로 사용되는 필드들
    """
    email: Optional[EmailStr] = Field(
        default=None,
        description="사용자 이메일 (Apple '이메일 가리기' 시 없거나 relay 주소일 수 있음)"
    )
    nickname: str = Field(default="식물 탐험가", description="앱 내 표시될 별명")

    # 기본값은 로컬 placeholder 이미지로 설정.
    profile_image_url: Optional[str] = Field(
        default="https://your-default-image-url.com/placeholder.png",
        description="프로필 이미지 경로 (Firebase Storage URL 또는 기본 이미지)"
    )


class UserLoginRequest(CamelCaseModel):
    """안드로이드에서 로그인 요청 시 보낼 데이터 규격"""
    id_token: str = Field(..., description="Firebase에서 발급받은 ID Token")
    # 신규 가입 시 동의 캡처용 (기존 유저 로그인 시에는 무시됨)
    terms_agreed: bool = Field(default=False, description="이용약관 동의 여부")
    privacy_agreed: bool = Field(default=False, description="개인정보 처리방침 동의 여부")


class UserResponse(UserBase):
    """
    안드로이드로 내보낼 유저 정보
    UserBase를 상속받았기 때문에 email, nickname, profile_image_url이 모두 포함됨.
    """
    id: str = Field(..., alias="_id", description="MongoDB의 고유 ID (문자열)")
    favorite_plant_ids: List[str] = Field(default_factory=list, description="찜한 식물 ID 리스트")
    created_at: datetime = Field(..., description="가입 일시")
    level_info: Optional[LevelInfo] = Field(default=None, description="레벨 정보")
    discovered_plant_ids: List[str] = Field(default_factory=list, description="발견한 식물 ID 목록")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )


class UserUpdate(CamelCaseModel):
    """회원 정보 수정 시 사용할 규격"""
    nickname: Optional[str] = None
    profile_image_url: Optional[str] = None