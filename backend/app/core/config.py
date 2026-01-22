"""
애플리케이션 설정 모듈.

Pydantic Settings를 사용하여 .env 파일에서 환경 변수를 로드한다.
모든 설정값은 이 모듈의 settings 인스턴스를 통해 접근한다.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """
    환경 변수 기반 애플리케이션 설정.

    .env 파일에서 자동으로 값을 읽어오며,
    필수 값이 누락된 경우 애플리케이션 시작 시 ValidationError 발생.
    """

    # === Database ===
    MONGO_URI: str                                  # MongoDB Atlas 연결 문자열
    MONGODB_DB_NAME: str = "floripedia"             # 사용할 데이터베이스명

    # === External Services (Keys) ===
    GEMINI_API_KEY: str                             # Google Gemini API 키
    
    # [추가] 이미지 검색 API 키 (값이 없으면 빈 문자열)
    UNSPLASH_ACCESS_KEY: str = ""
    PIXABAY_API_KEY: str = ""

    # === External Services (URLs)  ===
    # 환경 변수가 없어도 작동하도록 기본값(Default)을 https 주소로 고정합니다.
    UNSPLASH_BASE_URL: str = "https://api.unsplash.com"
    PIXABAY_BASE_URL: str = "https://pixabay.com/api"
    INATURALIST_BASE_URL: str = "https://api.inaturalist.org/v1"
    WIKIMEDIA_BASE_URL: str = "https://commons.wikimedia.org/w/api.php"

    # === Google Custom Search (이미지 검색) ===
    GOOGLE_SEARCH_API_KEY: str = ""             # Google Custom Search API 키
    GOOGLE_SEARCH_ENGINE_ID: str = ""           # Custom Search Engine ID (cx)

    # === Firebase ===
    FIREBASE_CREDENTIALS_PATH: str = "app/core/firebase-key.json"  # Firebase 서비스 계정 키 파일 경로
    FIREBASE_STORAGE_BUCKET: str = "floripedia-c0bf0.firebasestorage.app"    # Firebase Storage 버킷

    # === Application ===
    PROJECT_NAME: str = "Floripedia API"
    API_V1_STR: str = "/api/v1"

    # === Security ===
    # [주의] 프로덕션에서는 특정 도메인만 허용할 것
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # 정의되지 않은 환경 변수가 있어도 에러 내지 않고 무시함
    )


# 전역 설정 인스턴스 (싱글톤)
settings = Settings()