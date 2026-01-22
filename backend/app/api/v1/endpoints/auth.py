from fastapi import APIRouter, HTTPException, Depends, status

from app.services.auth_service import AuthService, AuthenticationError
from app.schemas.user import UserLoginRequest, UserResponse
from app.api.v1.endpoints.deps import get_auth_service

router = APIRouter()

# ==========================================
# 1. 로그인/회원가입 (Firebase Auth 통합)
# ==========================================
@router.post("/login", response_model=UserResponse)
async def login_or_signup(
    request: UserLoginRequest,
    service: AuthService = Depends(get_auth_service)
):
    """
    Firebase ID Token 기반 로그인/자동 회원가입

    1. 클라이언트가 Firebase에서 받은 ID Token을 전송
    2. 서버가 Token 검증 및 이메일/UID 추출
    3. DB에 없으면 자동 회원가입, 있으면 로그인 처리
    4. 유저 정보 반환
    """
    try:
        # request.id_token 안에 "ey..." 로 시작하는 JWT 토큰이 들어있어야 함
        user = await service.login_or_signup(request.id_token)
        return user

    except AuthenticationError as e:
        # 인증 실패 (토큰 만료, 위조 등)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=str(e)
        )
    except ValueError as e:
        # 잘못된 요청
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
    except PermissionError as e:
        # 차단된 계정 등
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=str(e)
        )


# ==========================================
# 2. 아이디 중복 체크 (회원가입 전)
# ==========================================
@router.get("/check-email")
async def check_email_exists(
    email: str,
    service: AuthService = Depends(get_auth_service)
):
    """
    이메일 중복 확인
    (Firebase Auth를 쓰면 사실상 Firebase가 중복을 막아주지만, 
    UX상 미리 확인할 때 사용)
    """
    exists = await service.check_email_exists(email)
    return {"exists": exists}