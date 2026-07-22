import logging
from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from firebase_admin import auth, app_check

from app.core.config import settings
from app.db.session import mongodb
from app.repositories import PlantRepository, UserRepository
from app.services.plant_service import PlantService

from app.services.user_service import UserService
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

# Firebase 초기화는 main.py에서 수행됨 (settings.FIREBASE_CREDENTIALS_PATH 사용)

# Swagger UI에서 자물쇠 버튼을 누를 때 사용할 스키마 (실제 검증은 Firebase가 하므로 URL은 장식용입니다)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="firebase_auth", auto_error=False)


# =================================================================
# 1. 의존성 주입 (Service/Repo 생성)
# =================================================================

def get_plant_service() -> PlantService:
    """PlantService 인스턴스 반환"""
    plant_repo = PlantRepository(mongodb.db)
    user_repo = UserRepository(mongodb.db)
    return PlantService(plant_repo, user_repo)

def get_user_service() -> UserService:
    """UserService 인스턴스 반환"""
    user_repo = UserRepository(mongodb.db)
    plant_repo = PlantRepository(mongodb.db)
    return UserService(user_repo, plant_repo)

def get_auth_service() -> AuthService:
        """AuthService 인스턴스 반환"""
        user_repo = UserRepository(mongodb.db)
        return AuthService(user_repo)


# =================================================================
# 2. Firebase 인증 의존성
# =================================================================

async def get_current_user_id(
    token: str = Depends(oauth2_scheme)
) -> str:
    """
    [필수 인증] Firebase ID Token을 검증하고 UID를 반환합니다.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Firebase Admin SDK로 토큰 검증
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']
        return uid
        
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 만료되었습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print(f"Firebase Auth Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증에 실패했습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user_id_optional(
    token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[str]:
    """
    [선택 인증] 토큰이 유효하면 UID 반환, 아니면 None 반환.
    """
    if not token:
        return None
    
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token['uid']
    except Exception:
        # 선택적 인증이므로 에러를 내지 않고 None 반환
        return None


# =================================================================
# 3. App Check 검증 (봇/어뷰징 방어)
# =================================================================

async def verify_app_check(
    x_firebase_appcheck: Optional[str] = Header(None, alias="X-Firebase-AppCheck")
) -> None:
    """
    Firebase App Check 토큰 검증.

    - monitor 모드(APP_CHECK_ENFORCED=False): 검증 결과를 로깅만 하고 항상 통과(점진 배포).
    - enforce 모드(True): 유효한 App Check 토큰이 없으면 403으로 거부.

    ※ 커스텀 백엔드는 App Check가 자동 적용되지 않으므로 여기서 직접 검증한다.
    """
    enforced = settings.APP_CHECK_ENFORCED

    if not x_firebase_appcheck:
        if enforced:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="App Check 토큰이 필요합니다.",
            )
        logger.warning("[AppCheck] 토큰 없음 (monitor 모드, 허용)")
        return

    try:
        app_check.verify_token(x_firebase_appcheck)
        logger.info("[AppCheck] 토큰 검증 성공")
    except Exception as e:
        if enforced:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="App Check 검증에 실패했습니다.",
            )
        logger.warning(f"[AppCheck] 검증 실패 (monitor 모드, 허용): {e}")


