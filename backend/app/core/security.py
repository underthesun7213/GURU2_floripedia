"""
보안 유틸리티 모듈.

비밀번호 해싱 및 JWT 토큰 관련 유틸리티 함수를 제공한다.

[현재 상태]
- 비밀번호 해싱: 사용 가능 (bcrypt)
- JWT 토큰: 현재 미사용 (Firebase Auth 토큰 사용 중)

[향후 자체 JWT 발급 시 필요한 설정]
config.py에 아래 설정 추가 필요:
    JWT_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
"""
from datetime import datetime, timedelta
from typing import Optional

from jose import jwt
from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """평문 비밀번호와 해시값 비교."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """비밀번호를 bcrypt로 해싱."""
    return pwd_context.hash(password)


# ============================================================
# [미사용] 아래 JWT 함수들은 현재 Firebase Auth 사용으로 인해 미사용.
# 향후 자체 토큰 발급 필요 시 config.py 설정 추가 후 활성화할 것.
# ============================================================

# def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
#     """JWT 액세스 토큰 생성."""
#     to_encode = data.copy()
#     expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
#     to_encode.update({"exp": expire})
#     return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)
#
#
# def decode_access_token(token: str) -> Optional[dict]:
#     """JWT 토큰 디코딩. 만료/오류 시 None 반환."""
#     try:
#         return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
#     except (jwt.ExpiredSignatureError, jwt.JWTError):
#         return None
