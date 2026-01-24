from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException, UploadFile, File, Depends, status

from app.db.session import mongodb
from app.repositories import PlantRepository, UserRepository
from app.services.plant_service import PlantService
from app.schemas import PlantCardDto, PlantDetailDto, PlantExploreDto, PlantSearchResultDto


# [핵심] deps.py에서 만든 3가지를 가져옵니다.
from app.api.v1.endpoints.deps import (
    get_plant_service, 
    get_current_user_id, 
    get_current_user_id_optional
)
router = APIRouter()
# ==========================================
# 0. 식물 api 관련 인증 의존성 주입(메소드 별 Depends로 permit state 조절절)
# ==========================================

# ==========================================
# 1. 꽃갈피(찜) 목록 조회 API 
# ==========================================
# 주의: 동적 경로(/{plant_id})보다 위에 있어야 함
@router.get("/favorites", response_model=List[PlantCardDto])
async def get_user_favorites(
    # [인증] 로그인 필수
    current_user_id: str = Depends(get_current_user_id),
    
    # [필터] 꽃갈피 내 재검색 (단일 선택)
    season: Optional[str] = Query(None, description="계절"),
    category_group: Optional[str] = Query(None, description="카테고리"),
    color_group: Optional[str] = Query(None, description="색상"),
    
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """
    내 꽃갈피(찜) 목록 조회.
    로그인한 사용자가 찜한 식물만 모아봅니다.
    """
    service = get_plant_service()
    
    return await service.get_user_favorites(
        user_id=current_user_id,
        season=season,
        category_group=category_group,
        color_group=color_group,
        skip=skip,
        limit=limit
    )


# ==========================================
# 2. 카테고리별 통합 조회 API (Filter & List)
# ==========================================
@router.get("", response_model=List[PlantCardDto])
async def get_plants(
    season: Optional[str] = Query(None, description="계절 (SPRING, SUMMER, FALL, WINTER)"),
    blooming_month: Optional[int] = Query(None, ge=1, le=12, description="개화 월 (1-12)"),
    
    # [수정] List[str] -> str (단일 선택으로 변경됨)
    category_group: Optional[str] = Query(None, description="식물 분류 (단일 선택)"),
    color_group: Optional[str] = Query(None, description="색상 그룹 (단일 선택)"),
    scent_group: Optional[str] = Query(None, description="향기 그룹 (단일 선택)"),
    flower_group: Optional[str] = Query(None, description="꽃말 그룹 (단일 선택)"),
    
    story_genre: Optional[str] = Query(None, description="스토리 장르"),
    keyword: Optional[str] = Query(None, description="검색어"),
    
    skip: int = Query(0, ge=0, description="건너뛸 개수"),
    limit: int = Query(20, ge=1, le=100, description="가져올 개수"),
    sort_by: str = Query("name", description="정렬 기준"),
    sort_order: str = Query("asc", description="정렬 방향"),
):
    """
    전체 식물 목록 조회 및 필터링.
    (단일 선택 필터 적용)
    """
    service = get_plant_service()

    # Service 호출 (인자명: groups -> group 변경 확인)
    plants = await service.get_plants(
        season=season,
        blooming_month=blooming_month,
        category_group=category_group,
        color_group=color_group,
        scent_group=scent_group,
        flower_group=flower_group,
        story_genre=story_genre,
        keyword=keyword,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return plants


@router.get("/count")
async def get_plants_count(
    season: Optional[str] = Query(None),
    blooming_month: Optional[int] = Query(None, ge=1, le=12),
    
    # [수정] 단일 선택
    category_group: Optional[str] = Query(None),
    color_group: Optional[str] = Query(None),
    scent_group: Optional[str] = Query(None),
    flower_group: Optional[str] = Query(None),
    
    story_genre: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
):
    """필터 조건에 맞는 식물 총 개수 반환"""
    service = get_plant_service()

    count = await service.get_plants_count(
        season=season,
        blooming_month=blooming_month,
        category_group=category_group,
        color_group=color_group,
        scent_group=scent_group,
        flower_group=flower_group,
        story_genre=story_genre,
        keyword=keyword,
    )
    return {"count": count}


# ==========================================
# 3. 상황별 꽃 추천 API (AI Curation, 체험 차원에서 열어 둠. 추후 배포 한다면 비즈니스 모델에 따라 permit state 조절)
# ==========================================
@router.post("/recommend", response_model=PlantExploreDto)
async def recommend_plants(situation: str = Query(..., description="사용자 상황 설명")):
    """
    상황에 맞는 단일 식물 추천
    """
    service = get_plant_service()

    try:
        result = await service.recommend_plants(situation)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 4. 이미지 기반 식물 검색 (Vision Search, 체험 차원에서 열어 둠. 추후 배포 한다면 비즈니스 모델에 따라 permit state 조절)
# ==========================================
@router.post("/search/image", response_model=PlantSearchResultDto)
async def search_plant_by_image(
    file: UploadFile = File(...),
    # [추가] 검색 결과에서도 찜 여부를 알기 위해 유저 ID 주입 (선택적)
    user_id: Optional[str] = Depends(get_current_user_id_optional)
):
    """
    이미지로 식물 검색
    
    - 응답: PlantSearchResultDto (전체 식물 정보 + is_newly_created + is_favorite)
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다")

    image_data = await file.read()
    service = get_plant_service()

    try:
        # Service에 user_id 전달
        result = await service.search_by_image(image_data, user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 5. 식물 상세페이지 조회 API
# ==========================================
@router.get("/{plant_id}", response_model=PlantDetailDto)
async def get_plant_detail(
    plant_id: str,
    # [수정] Header 직접 파싱 -> Depends 사용 (권장)
    user_id: Optional[str] = Depends(get_current_user_id_optional),
):
    """
    특정 식물의 상세 정보 조회
    - 로그인 시 is_favorite 필드에 True/False 반영
    """
    service = get_plant_service()
    plant = await service.get_plant_detail(plant_id, user_id)

    if not plant:
        raise HTTPException(status_code=404, detail="식물을 찾을 수 없습니다")

    return plant