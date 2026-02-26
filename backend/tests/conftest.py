"""
테스트 공통 Fixture Factory
- MongoDB Mock (plants / users / 통합)
- Service DI Fixtures
- API TestClient
"""
import os
from unittest.mock import MagicMock

# ============================================
# 1. 환경변수 (모든 import 보다 먼저)
# ============================================
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("GEMINI_API_KEY", "test-dummy-key")
os.environ.setdefault("FIREBASE_STORAGE_BUCKET", "test-bucket")

# ============================================
# 2. Firebase 초기화 방지 (테스트 환경에서는 불필요)
# ============================================
import firebase_admin
if not firebase_admin._apps:
    firebase_admin._apps["[DEFAULT]"] = MagicMock()

# ============================================
# 3. 일반 import
# ============================================
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from mongomock_motor import AsyncMongoMockClient

from app.repositories.plant_repository import PlantRepository
from app.repositories.user_repository import UserRepository


# ============================================
# MongoDB Mock Fixtures
# ============================================

@pytest.fixture
async def mock_db():
    """클린 MongoDB mock 인스턴스"""
    client = AsyncMongoMockClient()
    db = client["test_floripedia"]
    yield db
    await client.drop_database("test_floripedia")


@pytest.fixture
async def mock_db_with_plants(mock_db):
    """테스트용 식물 데이터가 포함된 DB"""
    test_plants = [
        {
            "_id": "1",
            "name": "장미",
            "englishName": "Rose",
            "scientificName": "Rosa canina",
            "imageUrl": "https://example.com/rose.jpg",
            "images": ["https://example.com/rose.jpg"],
            "season": "SPRING",
            "bloomingMonths": [5, 6],
            "searchKeywords": ["장미", "rose", "사랑"],
            "habitat": "온대 지역",
            "taxonomy": {"genus": "Rosa", "species": "canina", "family": "장미과"},
            "horticulture": {
                "category": "관목",
                "categoryGroup": "꽃과 풀",
                "usage": ["관상용", "절화"],
                "management": "햇빛과 배수가 좋은 곳",
                "preContent": "사랑을 상징하는 대표적인 꽃"
            },
            "flowerInfo": {"language": "사랑", "flowerGroup": "사랑/고백"},
            "colorInfo": {"hexCodes": ["#FF0000"], "colorLabels": ["빨강"], "colorGroup": ["빨강/분홍"]},
            "scentInfo": {"scentTags": ["달콤한"], "scentGroup": ["달콤·화사"]},
            "stories": [{"genre": "MYTH", "content": "그리스 신화에서 아프로디테의 꽃"}],
            "view_count": 100,
            "favorite_count": 50,
            "popularity_score": 600
        },
        {
            "_id": "2",
            "name": "라벤더",
            "englishName": "Lavender",
            "scientificName": "Lavandula angustifolia",
            "imageUrl": "https://example.com/lavender.jpg",
            "images": ["https://example.com/lavender.jpg"],
            "season": "SUMMER",
            "bloomingMonths": [6, 7, 8],
            "searchKeywords": ["라벤더", "lavender", "허브"],
            "habitat": "지중해 지역",
            "taxonomy": {"genus": "Lavandula", "species": "angustifolia", "family": "꿀풀과"},
            "horticulture": {
                "category": "허브",
                "categoryGroup": "꽃과 풀",
                "usage": ["아로마", "관상용"],
                "management": "건조하게 관리",
                "preContent": "마음을 편안하게 해주는 허브"
            },
            "flowerInfo": {"language": "침묵", "flowerGroup": "위로/슬픔"},
            "colorInfo": {"hexCodes": ["#9370DB"], "colorLabels": ["보라"], "colorGroup": ["푸른색"]},
            "scentInfo": {"scentTags": ["허브향"], "scentGroup": ["싱그럽고 시원"]},
            "stories": [{"genre": "HISTORY", "content": "고대 로마에서 목욕에 사용"}],
            "view_count": 80,
            "favorite_count": 40,
            "popularity_score": 480
        }
    ]

    await mock_db.plants.insert_many(test_plants)
    return mock_db


@pytest.fixture
async def mock_db_with_users(mock_db):
    """테스트용 유저 데이터가 포함된 DB (active + deactivated)"""
    test_users = [
        {
            "_id": "user1",
            "email": "active@test.com",
            "nickname": "활성유저",
            "profileImageUrl": "https://example.com/profile1.jpg",
            "isActive": True,
            "favoritePlantIds": ["1"],
            "createdAt": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "updatedAt": datetime(2025, 1, 1, tzinfo=timezone.utc),
        },
        {
            "_id": "user2",
            "email": "deactivated@test.com",
            "nickname": "탈퇴유저",
            "profileImageUrl": "https://example.com/profile2.jpg",
            "isActive": False,
            "favoritePlantIds": [],
            "createdAt": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "updatedAt": datetime(2025, 6, 1, tzinfo=timezone.utc),
        },
    ]

    await mock_db.users.insert_many(test_users)
    return mock_db


@pytest.fixture
async def mock_db_full(mock_db):
    """Plants + Users 통합 DB"""
    # Plants
    test_plants = [
        {
            "_id": "1",
            "name": "장미",
            "englishName": "Rose",
            "scientificName": "Rosa canina",
            "imageUrl": "https://example.com/rose.jpg",
            "images": ["https://example.com/rose.jpg"],
            "season": "SPRING",
            "bloomingMonths": [5, 6],
            "searchKeywords": ["장미", "rose", "사랑"],
            "habitat": "온대 지역",
            "taxonomy": {"genus": "Rosa", "species": "canina", "family": "장미과"},
            "horticulture": {
                "category": "관목",
                "categoryGroup": "꽃과 풀",
                "usage": ["관상용", "절화"],
                "management": "햇빛과 배수가 좋은 곳",
                "preContent": "사랑을 상징하는 대표적인 꽃"
            },
            "flowerInfo": {"language": "사랑", "flowerGroup": "사랑/고백"},
            "colorInfo": {"hexCodes": ["#FF0000"], "colorLabels": ["빨강"], "colorGroup": ["빨강/분홍"]},
            "scentInfo": {"scentTags": ["달콤한"], "scentGroup": ["달콤·화사"]},
            "stories": [{"genre": "MYTH", "content": "그리스 신화에서 아프로디테의 꽃"}],
            "view_count": 100,
            "favorite_count": 50,
            "popularity_score": 600
        },
        {
            "_id": "2",
            "name": "라벤더",
            "englishName": "Lavender",
            "scientificName": "Lavandula angustifolia",
            "imageUrl": "https://example.com/lavender.jpg",
            "images": ["https://example.com/lavender.jpg"],
            "season": "SUMMER",
            "bloomingMonths": [6, 7, 8],
            "searchKeywords": ["라벤더", "lavender", "허브"],
            "habitat": "지중해 지역",
            "taxonomy": {"genus": "Lavandula", "species": "angustifolia", "family": "꿀풀과"},
            "horticulture": {
                "category": "허브",
                "categoryGroup": "꽃과 풀",
                "usage": ["아로마", "관상용"],
                "management": "건조하게 관리",
                "preContent": "마음을 편안하게 해주는 허브"
            },
            "flowerInfo": {"language": "침묵", "flowerGroup": "위로/슬픔"},
            "colorInfo": {"hexCodes": ["#9370DB"], "colorLabels": ["보라"], "colorGroup": ["푸른색"]},
            "scentInfo": {"scentTags": ["허브향"], "scentGroup": ["싱그럽고 시원"]},
            "stories": [{"genre": "HISTORY", "content": "고대 로마에서 목욕에 사용"}],
            "view_count": 80,
            "favorite_count": 40,
            "popularity_score": 480
        },
    ]

    # Users
    test_users = [
        {
            "_id": "user1",
            "email": "active@test.com",
            "nickname": "활성유저",
            "profileImageUrl": "https://example.com/profile1.jpg",
            "isActive": True,
            "favoritePlantIds": ["1"],
            "createdAt": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "updatedAt": datetime(2025, 1, 1, tzinfo=timezone.utc),
        },
        {
            "_id": "user2",
            "email": "deactivated@test.com",
            "nickname": "탈퇴유저",
            "profileImageUrl": "https://example.com/profile2.jpg",
            "isActive": False,
            "favoritePlantIds": [],
            "createdAt": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "updatedAt": datetime(2025, 6, 1, tzinfo=timezone.utc),
        },
    ]

    await mock_db.plants.insert_many(test_plants)
    await mock_db.users.insert_many(test_users)
    return mock_db


# ============================================
# Repository Fixtures
# ============================================

@pytest.fixture
async def plant_repo(mock_db_with_plants):
    """PlantRepository 인스턴스 (식물 데이터 포함)"""
    return PlantRepository(mock_db_with_plants)


@pytest.fixture
async def user_repo(mock_db_with_users):
    """UserRepository 인스턴스 (유저 데이터 포함)"""
    return UserRepository(mock_db_with_users)


# ============================================
# Gemini Service Mock
# ============================================

@pytest.fixture
def mock_gemini_service():
    """Gemini Service Mock"""
    mock = MagicMock()

    mock.get_plant_name_from_image = AsyncMock(return_value={
        "name": "장미",
        "englishName": "Rose",
        "scientificName": "Rosa canina"
    })

    mock.get_plant_name_from_text = AsyncMock(return_value={
        "name": "라벤더",
        "englishName": "Lavender",
        "scientificName": "Lavandula angustifolia"
    })

    mock.generate_recommendation_essay = AsyncMock(
        return_value="라벤더는 마음의 평화를 선사하는 식물입니다..."
    )

    return mock


# ============================================
# Firebase Storage Mock
# ============================================

@pytest.fixture
def mock_firebase_storage():
    """Firebase Storage Mock"""
    mock = MagicMock()
    mock.upload_profile_image = MagicMock(
        return_value="https://storage.googleapis.com/test-bucket/profile.jpg"
    )
    return mock


# ============================================
# Service Factory Fixtures (DI 패턴)
# ============================================

@pytest.fixture
async def auth_service(mock_db_with_users):
    """AuthService (유저 데이터 포함 DB)"""
    from app.services.auth_service import AuthService
    repo = UserRepository(mock_db_with_users)
    return AuthService(repo)


@pytest.fixture
async def user_service(mock_db_full):
    """UserService (plants + users 통합 DB)"""
    from app.services.user_service import UserService
    user_repo = UserRepository(mock_db_full)
    plant_repo = PlantRepository(mock_db_full)
    return UserService(user_repo, plant_repo)


@pytest.fixture
async def plant_service(mock_db_full, mock_gemini_service):
    """PlantService (통합 DB + Gemini mock)"""
    from app.services.plant_service import PlantService
    plant_repo = PlantRepository(mock_db_full)
    user_repo = UserRepository(mock_db_full)
    return PlantService(plant_repo, user_repo, mock_gemini_service)


# ============================================
# API Test Fixtures
# ============================================

@pytest.fixture
async def test_app(mock_db_full):
    """FastAPI 앱 + DI override + plants 직접 호출 패치"""
    from app.main import app
    from app.api.v1.endpoints.deps import (
        get_user_service as _gus,
        get_auth_service as _gas,
        get_current_user_id as _gcui,
        get_current_user_id_optional as _gcuio,
    )
    from app.services.plant_service import PlantService
    from app.services.user_service import UserService
    from app.services.auth_service import AuthService

    plant_repo = PlantRepository(mock_db_full)
    user_repo_inst = UserRepository(mock_db_full)
    gemini_mock = MagicMock()
    gemini_mock.get_plant_name_from_image = AsyncMock(return_value={
        "name": "장미", "englishName": "Rose", "scientificName": "Rosa canina"
    })
    gemini_mock.get_plant_name_from_text = AsyncMock(return_value={
        "name": "라벤더", "englishName": "Lavender",
        "scientificName": "Lavandula angustifolia"
    })
    gemini_mock.generate_recommendation_essay = AsyncMock(
        return_value="추천 에세이입니다."
    )

    def override_plant_service():
        return PlantService(plant_repo, user_repo_inst, gemini_mock)

    def override_user_service():
        return UserService(user_repo_inst, plant_repo)

    def override_auth_service():
        return AuthService(user_repo_inst)

    async def override_current_user_id():
        return "user1"

    async def override_current_user_id_optional():
        return "user1"

    # Depends() 기반 DI override (auth, users 라우터)
    app.dependency_overrides[_gus] = override_user_service
    app.dependency_overrides[_gas] = override_auth_service
    app.dependency_overrides[_gcui] = override_current_user_id
    app.dependency_overrides[_gcuio] = override_current_user_id_optional

    # plants 라우터는 get_plant_service()를 직접 호출하므로 모듈 레벨 패치
    with patch("app.api.v1.endpoints.plants.get_plant_service", override_plant_service):
        yield app

    app.dependency_overrides.clear()


@pytest.fixture
async def client(test_app):
    """httpx AsyncClient"""
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test"
    ) as ac:
        yield ac
