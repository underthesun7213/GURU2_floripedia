"""
인증 관련 비즈니스 로직 서비스.
Firebase 인증, 로그인/회원가입 처리 등을 담당한다.
"""
from typing import Optional
from datetime import datetime, timezone

from firebase_admin import auth as firebase_auth
from app.repositories import UserRepository
from app.core.nickname import generate_nickname

class AuthService:
    """인증 비즈니스 로직 서비스"""

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
        # initialize_firebase() # main.py에서 수행됨

    async def login_or_signup(
        self,
        id_token: str,
        terms_agreed: bool = False,
        privacy_agreed: bool = False,
    ) -> dict:
        """
        Firebase ID Token 기반 로그인/자동 회원가입.

        Args:
            id_token: Firebase에서 발급받은 ID Token
            terms_agreed: 이용약관 동의 여부 (신규 가입 시 기록)
            privacy_agreed: 개인정보 처리방침 동의 여부 (신규 가입 시 기록)

        Returns:
            유저 정보 dict
        """
        # 1. Firebase ID Token 검증 및 정보 추출
        decoded_token = self._verify_token(id_token)
        uid = decoded_token.get("uid")
        # Apple 로그인은 '이메일 가리기'/재로그인 시 email 클레임이 없을 수 있으므로
        # 신원 식별은 항상 존재하는 uid로만 하고, email은 선택값으로 둔다.
        email = decoded_token.get("email")

        if not uid:
            raise ValueError("토큰에서 사용자 식별자(uid)를 가져올 수 없습니다")

        # 2. 기존 유저 확인 (ID로 조회 - 빠름)
        existing_user = await self.user_repo.get_by_id(uid)

        if existing_user:
            if not existing_user.get("isActive", True):
                raise PermissionError("탈퇴한 계정입니다")
            return existing_user

        # 3. 신규 유저 생성
        # 토큰에 name이 없으면(이메일/비번·일부 소셜 로그인) 부담 없는 랜덤 닉네임 부여.
        # (안드로이드는 가입 직후 updateProfile로 사용자가 고른 닉네임으로 덮어씀)
        firebase_name = decoded_token.get("name") or generate_nickname()
        firebase_picture = decoded_token.get("picture", "/assets/logo_placeholder.png")

        # 동의 캡처: 두 항목 모두 동의한 경우에만 동의 시각 기록
        now = datetime.now(timezone.utc)
        both_agreed = bool(terms_agreed and privacy_agreed)

        new_user_dict = {
            "_id": uid,  # [핵심] Firebase UID를 MongoDB _id로 사용
            "email": email,
            "nickname": firebase_name,
            "profileImageUrl": firebase_picture,
            "isActive": True,
            "isTermsAgreed": bool(terms_agreed),
            "isPrivacyAgreed": bool(privacy_agreed),
            "agreedAt": now if both_agreed else None,
            "favoritePlantIds": [],
            "createdAt": now,
            "updatedAt": now
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