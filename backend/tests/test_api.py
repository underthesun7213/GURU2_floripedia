"""
API 통합 테스트 — 주요 엔드포인트 패턴 검증
Plants (4) + Auth (3) + Users (3) = 10개
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# ============================================
# Plants Endpoints (4개)
# ============================================

class TestPlantsAPI:

    @pytest.mark.asyncio
    async def test_get_plants_200(self, client):
        """GET /plants -> 200 + 리스트 반환"""
        resp = await client.get("/api/v1/plants")

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_plant_detail_404(self, client):
        """GET /plants/999 -> 404"""
        resp = await client.get("/api/v1/plants/999")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_search_image_200(self, client):
        """POST /plants/search/image -> 200 (Gemini mock)"""
        resp = await client.post(
            "/api/v1/plants/search/image",
            files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data

    @pytest.mark.asyncio
    async def test_recommend_200(self, client):
        """POST /plants/recommend -> 200 + recommendation 필드"""
        resp = await client.post(
            "/api/v1/plants/recommend",
            params={"situation": "우울할 때 위로가 되는 꽃"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "recommendation" in data


# ============================================
# Auth Endpoints (3개)
# ============================================

class TestAuthAPI:

    @pytest.mark.asyncio
    async def test_login_200(self, client):
        """POST /auth/login -> 200 + UserResponse"""
        with patch("app.services.auth_service.firebase_auth") as mock_fb:
            mock_fb.verify_id_token.return_value = {
                "uid": "user1",
                "email": "active@test.com",
                "name": "활성유저",
            }
            mock_fb.InvalidIdTokenError = type("InvalidIdTokenError", (Exception,), {})
            mock_fb.ExpiredIdTokenError = type("ExpiredIdTokenError", (Exception,), {})

            resp = await client.post(
                "/api/v1/auth/login",
                json={"idToken": "valid-firebase-token"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "active@test.com"

    @pytest.mark.asyncio
    async def test_login_401(self, client):
        """POST /auth/login -> 401 잘못된 토큰"""
        with patch("app.services.auth_service.firebase_auth") as mock_fb:
            mock_fb.InvalidIdTokenError = type("InvalidIdTokenError", (Exception,), {})
            mock_fb.ExpiredIdTokenError = type("ExpiredIdTokenError", (Exception,), {})
            mock_fb.verify_id_token.side_effect = mock_fb.InvalidIdTokenError("bad")

            resp = await client.post(
                "/api/v1/auth/login",
                json={"idToken": "bad-token"},
            )

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_check_email(self, client):
        """GET /auth/check-email -> {exists: bool}"""
        resp = await client.get(
            "/api/v1/auth/check-email",
            params={"email": "active@test.com"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "exists" in data


# ============================================
# Users Endpoints (3개)
# ============================================

class TestUsersAPI:

    @pytest.mark.asyncio
    async def test_get_profile_200(self, client):
        """GET /users/me -> 200 + 프로필"""
        resp = await client.get("/api/v1/users/me")

        assert resp.status_code == 200
        data = resp.json()
        assert "email" in data

    @pytest.mark.asyncio
    async def test_toggle_favorite_200(self, client):
        """POST /users/me/favorites/1 -> 200 + {isFavorite: bool}"""
        resp = await client.post("/api/v1/users/me/favorites/1")

        assert resp.status_code == 200
        data = resp.json()
        assert "isFavorite" in data

    @pytest.mark.asyncio
    async def test_upload_image_400(self, client):
        """POST /users/me/profile-image -> 400 잘못된 형식"""
        resp = await client.post(
            "/api/v1/users/me/profile-image",
            files={"file": ("test.txt", b"not-an-image", "text/plain")},
        )

        assert resp.status_code == 400
