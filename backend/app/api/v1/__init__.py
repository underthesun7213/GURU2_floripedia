from fastapi import APIRouter

from app.api.v1.endpoints import plants, auth, users, admin

api_router = APIRouter()

# 식물 관련 API
api_router.include_router(plants.router, prefix="/plants", tags=["plants"])

# 인증 관련 API
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# 유저 관련 API
api_router.include_router(users.router, prefix="/users", tags=["users"])

# 관리자 API (캐시 무효화 등)
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
