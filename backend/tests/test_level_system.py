"""
레벨 시스템 테스트
- 레벨 계산 로직
- EXP 부여
- Repository 메서드 (discovered, viewed)
- Service 통합 (award_exp, get_profile levelInfo 주입)
"""
import pytest
from datetime import datetime, timezone

from app.schemas.user import LEVEL_THRESHOLDS, compute_level_info
from app.services.user_service import _compute_level, UserService
from app.repositories.user_repository import UserRepository


# ============================================
# 순수 함수 단위 테스트
# ============================================

class TestComputeLevel:
    """_compute_level 레벨 계산"""

    def test_level_1_at_zero(self):
        assert _compute_level(0) == 1

    def test_level_1_below_threshold(self):
        assert _compute_level(29) == 1

    def test_level_2_at_threshold(self):
        assert _compute_level(30) == 2

    def test_level_3_at_threshold(self):
        assert _compute_level(70) == 3

    def test_level_4_at_threshold(self):
        assert _compute_level(130) == 4

    def test_level_5_at_threshold(self):
        assert _compute_level(210) == 5

    def test_level_8_at_threshold(self):
        assert _compute_level(640) == 8

    def test_level_10_at_threshold(self):
        assert _compute_level(1150) == 10

    def test_level_10_above_max(self):
        assert _compute_level(9999) == 10


class TestComputeLevelInfo:
    """compute_level_info DTO 생성"""

    def test_level_1_info(self):
        info = compute_level_info(20, 1, 2)
        assert info["level"] == 1
        assert info["title"] == "씨앗"
        assert info["totalExp"] == 20
        assert info["currentLevelExp"] == 20  # 20 - 0
        assert info["nextLevelExp"] == 30     # 30 - 0
        assert info["discoveredPlantCount"] == 2

    def test_level_3_info(self):
        info = compute_level_info(100, 3, 10)
        assert info["level"] == 3
        assert info["title"] == "떡잎"
        assert info["currentLevelExp"] == 30   # 100 - 70
        assert info["nextLevelExp"] == 60       # 130 - 70

    def test_level_10_max(self):
        info = compute_level_info(1200, 10, 50)
        assert info["level"] == 10
        assert info["title"] == "식물 마스터"
        assert info["currentLevelExp"] == 50   # 1200 - 1150
        # 만렙(레벨 10)일 때 nextLevelExp는 0 (다음 레벨 없음)
        assert info["nextLevelExp"] == 0


# ============================================
# Repository 테스트
# ============================================

class TestUserRepoLevelMethods:
    """UserRepository 레벨 관련 메서드"""

    @pytest.fixture
    async def repo_with_user(self, mock_db):
        """EXP 테스트용 유저"""
        await mock_db.users.insert_one({
            "_id": "lvl_user",
            "email": "level@test.com",
            "nickname": "레벨유저",
            "isActive": True,
            "totalExp": 0,
            "level": 1,
            "discoveredPlantIds": [],
            "viewedPlantIds": [],
            "favoritePlantIds": [],
            "createdAt": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "updatedAt": datetime(2025, 1, 1, tzinfo=timezone.utc),
        })
        return UserRepository(mock_db)

    @pytest.mark.asyncio
    async def test_add_exp(self, repo_with_user):
        repo = repo_with_user
        result = await repo.add_exp("lvl_user", 20, 1)
        assert result is True

        user = await repo.get_by_id("lvl_user")
        assert user["totalExp"] == 20
        assert user["level"] == 1

    @pytest.mark.asyncio
    async def test_add_exp_level_up(self, repo_with_user):
        repo = repo_with_user
        await repo.add_exp("lvl_user", 50, 2)

        user = await repo.get_by_id("lvl_user")
        assert user["totalExp"] == 50
        assert user["level"] == 2

    @pytest.mark.asyncio
    async def test_add_discovered_plant(self, repo_with_user):
        repo = repo_with_user
        result = await repo.add_discovered_plant("lvl_user", "plant_1")
        assert result is True

        user = await repo.get_by_id("lvl_user")
        assert "plant_1" in user["discoveredPlantIds"]

    @pytest.mark.asyncio
    async def test_add_discovered_plant_no_duplicate(self, repo_with_user):
        repo = repo_with_user
        await repo.add_discovered_plant("lvl_user", "plant_1")
        result = await repo.add_discovered_plant("lvl_user", "plant_1")
        assert result is False  # $addToSet, 중복 없음

        user = await repo.get_by_id("lvl_user")
        assert user["discoveredPlantIds"].count("plant_1") == 1

    @pytest.mark.asyncio
    async def test_add_viewed_plant(self, repo_with_user):
        repo = repo_with_user
        result = await repo.add_viewed_plant("lvl_user", "plant_2")
        assert result is True

        user = await repo.get_by_id("lvl_user")
        assert "plant_2" in user["viewedPlantIds"]

    @pytest.mark.asyncio
    async def test_add_viewed_plant_no_duplicate(self, repo_with_user):
        repo = repo_with_user
        await repo.add_viewed_plant("lvl_user", "plant_2")
        result = await repo.add_viewed_plant("lvl_user", "plant_2")
        assert result is False

        user = await repo.get_by_id("lvl_user")
        assert user["viewedPlantIds"].count("plant_2") == 1


# ============================================
# Service 통합 테스트
# ============================================

class TestUserServiceLevel:
    """UserService 레벨 관련 통합"""

    @pytest.fixture
    async def level_service(self, mock_db):
        """레벨 테스트용 서비스"""
        from app.repositories.plant_repository import PlantRepository

        await mock_db.users.insert_one({
            "_id": "svc_user",
            "email": "svc@test.com",
            "nickname": "서비스유저",
            "isActive": True,
            "totalExp": 0,
            "level": 1,
            "discoveredPlantIds": [],
            "viewedPlantIds": [],
            "favoritePlantIds": [],
            "createdAt": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "updatedAt": datetime(2025, 1, 1, tzinfo=timezone.utc),
        })

        user_repo = UserRepository(mock_db)
        plant_repo = PlantRepository(mock_db)
        return UserService(user_repo, plant_repo)

    @pytest.mark.asyncio
    async def test_award_exp(self, level_service):
        svc = level_service
        await svc.award_exp("svc_user", 20, "test")

        user = await svc.user_repo.get_by_id("svc_user")
        assert user["totalExp"] == 20
        assert user["level"] == 1

    @pytest.mark.asyncio
    async def test_award_exp_level_up(self, level_service):
        svc = level_service
        await svc.award_exp("svc_user", 50, "test")

        user = await svc.user_repo.get_by_id("svc_user")
        assert user["totalExp"] == 50
        assert user["level"] == 2

    @pytest.mark.asyncio
    async def test_award_exp_cumulative(self, level_service):
        svc = level_service
        await svc.award_exp("svc_user", 30, "a")
        await svc.award_exp("svc_user", 30, "b")

        user = await svc.user_repo.get_by_id("svc_user")
        assert user["totalExp"] == 60
        assert user["level"] == 2

    @pytest.mark.asyncio
    async def test_get_profile_includes_level_info(self, level_service):
        svc = level_service
        await svc.award_exp("svc_user", 160, "test")

        profile = await svc.get_profile("svc_user")
        assert profile is not None
        assert "levelInfo" in profile

        info = profile["levelInfo"]
        assert info["level"] == 4       # 160 EXP → 130(lv4) 이상, 210(lv5) 미만
        assert info["title"] == "어린잎"

    @pytest.mark.asyncio
    async def test_get_profile_default_level(self, level_service):
        """EXP 0인 유저도 levelInfo 포함"""
        profile = await level_service.get_profile("svc_user")
        info = profile["levelInfo"]
        assert info["level"] == 1
        assert info["title"] == "씨앗"
        assert info["totalExp"] == 0

    @pytest.mark.asyncio
    async def test_award_exp_nonexistent_user(self, level_service):
        """존재하지 않는 유저에 EXP 부여 -> 무시"""
        # 에러 없이 조용히 무시되는지 확인
        await level_service.award_exp("nonexistent", 100, "test")
