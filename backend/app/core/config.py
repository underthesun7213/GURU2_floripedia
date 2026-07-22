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

    # === App Check (봇/어뷰징 방어) ===
    # False(monitor): 토큰을 검증·로깅만 하고 통과시킴(점진 배포용).
    # True(enforce): 유효한 App Check 토큰이 없으면 거부. 디버그 토큰 등록·검증 확인 후 켤 것.
    APP_CHECK_ENFORCED: bool = False

    # === Gemini Models ===
    # 앱에서 실제 쓰는 건 2개(basic/essay). 모델명은 비밀이 아니므로 여기 기본값으로 관리(필요 시 env override).
    GEMINI_BASIC_MODEL: str = "gemini-3.1-flash-lite"   # 이미지 판정·식별·상황 추천(고빈도·가성비, stable)
    GEMINI_ESSAY_MODEL: str = "gemini-3.5-flash"        # 추천 에세이(저빈도·UX 핵심, stable)

    # === Application ===
    PROJECT_NAME: str = "Floripedia API"
    API_V1_STR: str = "/api/v1"

    # === Cache (인메모리; 추후 Redis 교체 대비 추상화) ===
    CACHE_ENABLED: bool = True          # False면 캐시 완전 우회(디버깅용)
    CACHE_TTL: int = 3600               # 기본 캐시 TTL(초)
    CACHE_NEGATIVE_TTL: int = 60        # 존재하지 않는 리소스(None) 캐시 TTL(초)
    CACHE_MAXSIZE: int = 2048           # 최대 캐시 엔트리 수
    CACHE_SCHEMA_VERSION: int = 1       # 캐시 키 스키마 버전 (일괄 무효화용)
    CACHE_INVALIDATE_TOKEN: str = ""    # 관리자 무효화 토큰 (빈값이면 무효화 엔드포인트 거부)

    # === Security ===
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://10.0.2.2:8000",   # Android 에뮬레이터
        "http://localhost:8000",   # 로컬 개발
        "http://localhost:3000",   # 웹 프론트 (필요 시)
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # 정의되지 않은 환경 변수가 있어도 에러 내지 않고 무시함
    )


# 전역 설정 인스턴스 (싱글톤)
settings = Settings()