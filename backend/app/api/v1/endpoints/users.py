from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, status

from app.schemas.user import UserResponse, UserUpdate
from app.schemas import PlantCardDto
from app.services.user_service import UserService
from app.api.v1.endpoints.deps import get_user_service, get_current_user_id


router = APIRouter()


# ==========================================
# 0. 유저 api 관련 인증 의존성 주입(메소드 별 Depends로 permit state 조절절)
# ==========================================

# ==========================================
# 1. 마이페이지 - 프로필 조회
# ==========================================
@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    # [인증] Firebase Token 검증 후 uid 반환
    user_id: str = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service)
):
    """현재 로그인한 유저의 프로필 조회"""
    try:
        user = await service.get_profile(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다")
        return user
    except ValueError as e:
        # 탈퇴한 계정 등 비즈니스 로직 에러
        raise HTTPException(status_code=403, detail=str(e))


# ==========================================
# 2. 마이페이지 - 프로필 수정
# ==========================================
@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    update_data: UserUpdate,
    user_id: str = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service)
):
    """
    프로필 정보 수정 (닉네임 등).
    참고: 프로필 이미지는 별도 API로 처리합니다.
    """
    # Pydantic v2의 model_dump를 사용하여 None 값 필터링
    update_dict = {
        k: v for k, v in update_data.model_dump(by_alias=True).items() 
        if v is not None
    }

    if not update_dict:
        raise HTTPException(status_code=400, detail="수정할 내용이 없습니다")

    updated_user = await service.update_profile(user_id, update_dict)

    if not updated_user:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다")

    return updated_user


# ==========================================
# 3. 마이페이지 - 프로필 이미지 업로드
# ==========================================
@router.post("/me/profile-image", response_model=UserResponse)
async def upload_profile_image(
    file: UploadFile = File(..., description="업로드할 프로필 이미지"),
    user_id: str = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service)
):
    """
    프로필 이미지 업로드.
    - 파일 형식 및 크기 검증
    - Firebase Storage 업로드
    - MongoDB URL 업데이트
    """
    allowed_types = ["image/jpeg", "image/png", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="지원하지 않는 이미지 형식입니다. JPEG 또는 PNG만 가능합니다."
        )

    # 5MB 용량 제한
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="파일 크기가 너무 큽니다. 최대 5MB까지 업로드 가능합니다."
        )

    try:
        updated_user = await service.upload_profile_image(
            user_id=user_id,
            file_data=contents,
            content_type=file.content_type,
        )
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 4. 꽃갈피(찜) - 토글
# ==========================================
@router.post("/me/favorites/{plant_id}")
async def toggle_favorite(
    plant_id: str,
    user_id: str = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service)
):
    """
    식물 찜하기/취소 (Toggle)
    """
    try:
        result = await service.toggle_favorite(user_id, plant_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==========================================
# 5. 꽃갈피(찜) - 목록 조회 (main /plants와 동일한 필터 구조)
# ==========================================
@router.get("/me/favorites", response_model=List[PlantCardDto])
async def get_my_favorites(
    # 필터 파라미터 (main /plants endpoint와 동일 - 모두 단일 선택)
    season: Optional[str] = Query(None, description="계절 (SPRING, SUMMER, FALL, WINTER)"),
    category_group: Optional[str] = Query(None, description="카테고리 그룹"),
    color_group: Optional[str] = Query(None, description="색상 그룹"),
    scent_group: Optional[str] = Query(None, description="향기 그룹"),
    flower_group: Optional[str] = Query(None, description="꽃말 그룹"),
    keyword: Optional[str] = Query(None, description="검색어"),
    # 정렬 & 페이지네이션
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    sort_by: str = Query("name", description="정렬 기준 (name, popularity_score)"),
    sort_order: str = Query("asc", description="정렬 방향 (asc, desc)"),
    # 인증
    user_id: str = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service)
):
    """
    내 찜 목록 조회 - 찜한 식물 내에서 main plants 필터링 로직 적용
    """
    plants = await service.get_favorites(
        user_id=user_id,
        season=season,
        category_group=category_group,
        color_group=color_group,
        scent_group=scent_group,
        flower_group=flower_group,
        keyword=keyword,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order
    )
    return plants


# ==========================================
# 6. 꽃갈피(찜) - 개수 조회
# ==========================================
@router.get("/me/favorites/count")
async def get_my_favorites_count(
    user_id: str = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service)
):
    """내 찜 목록 개수 조회"""
    count = await service.get_favorites_count(user_id)
    return {"count": count}


# ==========================================
# 7. 로그아웃
# ==========================================
@router.post("/logout")
async def logout(
    user_id: str = Depends(get_current_user_id)
):
    """
    로그아웃.
    - 서버는 Stateless(JWT)이므로, 실제로는 클라이언트가 토큰을 폐기하면 됩니다.
    - 여기서는 성공 메시지만 반환합니다.
    """
    return {"message": "로그아웃 되었습니다"}


# ==========================================
# 8. 회원 탈퇴
# ==========================================
@router.delete("/me")
async def delete_account(
    user_id: str = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service)
):
    """
    회원 탈퇴 (Soft Delete).
    isActive를 False로 변경합니다.
    """
    success = await service.delete_account(user_id)

    if not success:
        raise HTTPException(status_code=404, detail="유저를 찾을 수 없습니다")

    return {"message": "회원 탈퇴가 완료되었습니다"}