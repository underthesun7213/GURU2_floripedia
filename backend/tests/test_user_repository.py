"""
UserRepository 단위 테스트
- 비자명한 로직만: soft delete, favorite CRUD
"""
import pytest

from app.repositories.user_repository import UserRepository


class TestSoftDelete:
    """소프트 삭제 테스트"""

    @pytest.mark.asyncio
    async def test_soft_delete(self, user_repo: UserRepository):
        """활성 유저 soft delete -> isActive=False"""
        result = await user_repo.soft_delete("user1")

        assert result is True

        user = await user_repo.get_by_id("user1")
        assert user["isActive"] is False

    @pytest.mark.asyncio
    async def test_soft_delete_nonexistent(self, user_repo: UserRepository):
        """존재하지 않는 유저 soft delete -> False"""
        result = await user_repo.soft_delete("nonexistent")

        assert result is False


class TestFavorites:
    """찜 기능 테스트"""

    @pytest.mark.asyncio
    async def test_add_favorite(self, user_repo: UserRepository):
        """찜 추가 ($addToSet)"""
        result = await user_repo.add_favorite("user1", "2")

        assert result is True

        favorites = await user_repo.get_favorites("user1")
        assert "2" in favorites

    @pytest.mark.asyncio
    async def test_add_duplicate_favorite(self, user_repo: UserRepository):
        """중복 찜 추가 방지 ($addToSet)"""
        # user1은 이미 "1"을 찜한 상태
        result = await user_repo.add_favorite("user1", "1")

        assert result is False  # modified_count == 0

        favorites = await user_repo.get_favorites("user1")
        assert favorites.count("1") == 1  # 중복 없음

    @pytest.mark.asyncio
    async def test_remove_favorite(self, user_repo: UserRepository):
        """찜 제거 ($pull)"""
        # user1은 "1"을 찜한 상태
        result = await user_repo.remove_favorite("user1", "1")

        assert result is True

        favorites = await user_repo.get_favorites("user1")
        assert "1" not in favorites

    @pytest.mark.asyncio
    async def test_get_favorites(self, user_repo: UserRepository):
        """찜 목록 조회"""
        favorites = await user_repo.get_favorites("user1")

        assert isinstance(favorites, list)
        assert "1" in favorites
