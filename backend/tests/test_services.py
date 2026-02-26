"""
AuthService + UserService 비즈니스 로직 테스트
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.auth_service import AuthService, AuthenticationError
from app.services.user_service import UserService


# ============================================
# AuthService (6개)
# ============================================

class TestAuthServiceLogin:
    """로그인/회원가입 비즈니스 로직"""

    @pytest.mark.asyncio
    async def test_login_existing_user(self, auth_service: AuthService):
        """기존 활성 유저 -> 유저 정보 반환"""
        with patch("app.services.auth_service.firebase_auth") as mock_fb:
            mock_fb.verify_id_token.return_value = {
                "uid": "user1",
                "email": "active@test.com",
                "name": "활성유저",
            }

            result = await auth_service.login_or_signup("valid-token")

        assert result["_id"] == "user1"
        assert result["email"] == "active@test.com"

    @pytest.mark.asyncio
    async def test_login_deactivated_user(self, auth_service: AuthService):
        """탈퇴한 유저 로그인 -> PermissionError"""
        with patch("app.services.auth_service.firebase_auth") as mock_fb:
            mock_fb.verify_id_token.return_value = {
                "uid": "user2",
                "email": "deactivated@test.com",
            }

            with pytest.raises(PermissionError, match="탈퇴한 계정"):
                await auth_service.login_or_signup("valid-token")

    @pytest.mark.asyncio
    async def test_signup_new_user(self, auth_service: AuthService):
        """신규 유저 -> DB 생성 + 기본값 확인"""
        with patch("app.services.auth_service.firebase_auth") as mock_fb:
            mock_fb.verify_id_token.return_value = {
                "uid": "new-uid",
                "email": "new@test.com",
                "name": "신규유저",
                "picture": "https://example.com/pic.jpg",
            }

            result = await auth_service.login_or_signup("new-token")

        assert result["_id"] == "new-uid"
        assert result["email"] == "new@test.com"
        assert result["isActive"] is True
        assert result["favoritePlantIds"] == []

    @pytest.mark.asyncio
    async def test_invalid_token(self, auth_service: AuthService):
        """잘못된 토큰 -> AuthenticationError"""
        with patch("app.services.auth_service.firebase_auth") as mock_fb:
            mock_fb.InvalidIdTokenError = type("InvalidIdTokenError", (Exception,), {})
            mock_fb.ExpiredIdTokenError = type("ExpiredIdTokenError", (Exception,), {})
            mock_fb.verify_id_token.side_effect = mock_fb.InvalidIdTokenError("bad")

            with pytest.raises(AuthenticationError, match="유효하지 않은 토큰"):
                await auth_service.login_or_signup("bad-token")

    @pytest.mark.asyncio
    async def test_expired_token(self, auth_service: AuthService):
        """만료된 토큰 -> AuthenticationError"""
        with patch("app.services.auth_service.firebase_auth") as mock_fb:
            mock_fb.InvalidIdTokenError = type("InvalidIdTokenError", (Exception,), {})
            mock_fb.ExpiredIdTokenError = type("ExpiredIdTokenError", (Exception,), {})
            mock_fb.verify_id_token.side_effect = mock_fb.ExpiredIdTokenError("expired")

            with pytest.raises(AuthenticationError, match="만료된 토큰"):
                await auth_service.login_or_signup("expired-token")

    @pytest.mark.asyncio
    async def test_check_email_exists(self, auth_service: AuthService):
        """이메일 존재 여부 확인"""
        exists = await auth_service.check_email_exists("active@test.com")
        assert exists is True

        not_exists = await auth_service.check_email_exists("nobody@test.com")
        assert not_exists is False


# ============================================
# UserService (8개)
# ============================================

class TestUserServiceProfile:
    """프로필 관련 비즈니스 로직"""

    @pytest.mark.asyncio
    async def test_get_profile_active(self, user_service: UserService):
        """활성 유저 프로필 정상 반환"""
        result = await user_service.get_profile("user1")

        assert result is not None
        assert result["nickname"] == "활성유저"

    @pytest.mark.asyncio
    async def test_get_profile_deactivated(self, user_service: UserService):
        """탈퇴 유저 프로필 -> ValueError"""
        with pytest.raises(ValueError, match="탈퇴한 계정"):
            await user_service.get_profile("user2")

    @pytest.mark.asyncio
    async def test_upload_image_success(self, user_service: UserService, mock_firebase_storage):
        """프로필 이미지 업로드 성공"""
        with patch("app.services.user_service.firebase_storage", mock_firebase_storage):
            result = await user_service.upload_profile_image(
                user_id="user1",
                file_data=b"fake-image-data",
                content_type="image/jpeg",
            )

        assert result is not None
        mock_firebase_storage.upload_profile_image.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_image_user_not_found(self, user_service: UserService):
        """존재하지 않는 유저 이미지 업로드 -> ValueError"""
        with pytest.raises(ValueError, match="유저를 찾을 수 없습니다"):
            await user_service.upload_profile_image(
                user_id="nonexistent",
                file_data=b"fake-image-data",
                content_type="image/jpeg",
            )


class TestUserServiceFavorite:
    """찜 토글 비즈니스 로직"""

    @pytest.mark.asyncio
    async def test_toggle_add_favorite(self, user_service: UserService):
        """찜 추가 -> isFavorite=True"""
        result = await user_service.toggle_favorite("user1", "2")

        assert result["isFavorite"] is True

    @pytest.mark.asyncio
    async def test_toggle_remove_favorite(self, user_service: UserService):
        """찜 취소 -> isFavorite=False (user1은 이미 "1"을 찜한 상태)"""
        result = await user_service.toggle_favorite("user1", "1")

        assert result["isFavorite"] is False

    @pytest.mark.asyncio
    async def test_toggle_user_not_found(self, user_service: UserService):
        """존재하지 않는 유저 -> ValueError"""
        with pytest.raises(ValueError, match="유저를 찾을 수 없습니다"):
            await user_service.toggle_favorite("nonexistent", "1")

    @pytest.mark.asyncio
    async def test_toggle_plant_not_found(self, user_service: UserService):
        """존재하지 않는 식물 -> ValueError"""
        with pytest.raises(ValueError, match="식물을 찾을 수 없습니다"):
            await user_service.toggle_favorite("user1", "999")
