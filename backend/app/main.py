"""
Floripedia API - 메인 애플리케이션 모듈.

FastAPI 앱 인스턴스 생성 및 미들웨어/라우터 설정을 담당한다.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import firebase_admin
from firebase_admin import credentials

from app.api.v1 import api_router
from app.core.config import settings
from app.db.session import mongodb


# ==========================================
# 1. Firebase 초기화 (앱 시작 시 1회 수행)
# ==========================================
if not firebase_admin._apps:
    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred, {
        'storageBucket': settings.FIREBASE_STORAGE_BUCKET
    })


# ==========================================
# 2. 수명 주기(Lifespan) 관리
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 생명주기 관리.
    - startup: MongoDB 연결 수립
    - shutdown: MongoDB 연결 해제
    """
    await mongodb.connect()
    print("✅ MongoDB Connected")  # 로그 추가 (확인용)
    
    yield
    
    await mongodb.close()
    print("⛔ MongoDB Closed")    # 로그 추가 (확인용)


# ==========================================
# 3. FastAPI 앱 인스턴스 생성
# ==========================================
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="식물 정보 및 AI 기반 추천 서비스 API",
    version="1.0.0",
    lifespan=lifespan,
)


# ==========================================
# 4. 미들웨어 및 정적 파일 설정
# ==========================================

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Assets 폴더 마운트 (프로필 기본 이미지 등 서빙용)
if not os.path.exists("assets"):
    os.makedirs("assets")

app.mount("/assets", StaticFiles(directory="assets"), name="assets")


# ==========================================
# 5. 라우터 등록
# ==========================================
app.include_router(api_router, prefix=settings.API_V1_STR)


# ==========================================
# 6. 기본 엔드포인트
# ==========================================
@app.get("/", tags=["health"])
async def root():
    """API 루트 엔드포인트. 서비스 정보 반환."""
    return {"message": settings.PROJECT_NAME, "version": "1.0.0"}


@app.get("/health", tags=["health"])
async def health_check():
    """헬스체크 엔드포인트. 서비스 상태 확인용."""
    return {"status": "healthy"}