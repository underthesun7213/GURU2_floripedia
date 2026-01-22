"""
인증 관련 비즈니스 로직 서비스.
Firebase 인증, 로그인/회원가입 처리 등을 담당한다.
"""
from typing import Optional
from datetime import datetime, timezone

from firebase_admin import auth as firebase_auth
from app.repositories import UserRepository

class AuthService:
    """인증 비즈니스 로직 서비스"""

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
        # initialize_firebase() # main.py에서 수행됨

    async def login_or_signup(self, id_token: str) -> dict:
        """
        Firebase ID Token 기반 로그인/자동 회원가입.

        Args:
            id_token: Firebase에서 발급받은 ID Token

        Returns:
            유저 정보 dict
        """
        # 1. Firebase ID Token 검증 및 정보 추출
        decoded_token = self._verify_token(id_token)
        uid = decoded_token.get("uid")
        email = decoded_token.get("email")

        if not uid or not email:
            raise ValueError("토큰에서 필수 정보를 가져올 수 없습니다")

        # 2. 기존 유저 확인 (ID로 조회 - 빠름)
        existing_user = await self.user_repo.get_by_id(uid)

        if existing_user:
            if not existing_user.get("isActive", True):
                raise PermissionError("탈퇴한 계정입니다")
            return existing_user

        # 3. 신규 유저 생성
        firebase_name = decoded_token.get("name", "식물 탐험가")
        firebase_picture = decoded_token.get("picture", "/assets/logo_placeholder.png")

        new_user_dict = {
            "_id": uid,  # [핵심] Firebase UID를 MongoDB _id로 사용
            "email": email,
            "nickname": firebase_name,
            "profileImageUrl": firebase_picture,
            "isActive": True,
            "favoritePlantIds": [],
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc)
        }

        created_user = await self.user_repo.create(new_user_dict)
        return created_user

    async def check_email_exists(self, email: str) -> bool:
        """이메일 중복 확인."""
        existing = await self.user_repo.get_by_email(email)
        return existing is not None

    def _verify_token(self, id_token: str) -> dict:
        """
        Firebase ID Token 검증.
        """
        try:
            return firebase_auth.verify_id_token(id_token)
        except firebase_auth.InvalidIdTokenError:
            raise AuthenticationError("유효하지 않은 토큰입니다")
        except firebase_auth.ExpiredIdTokenError:
            raise AuthenticationError("만료된 토큰입니다")
        except Exception as e:
            raise AuthenticationError(f"토큰 검증 실패: {str(e)}")


class AuthenticationError(Exception):
    """인증 관련 예외"""
    pass