"""
Firebase Admin SDK 초기화 모듈.

Google Firebase 서비스(Authentication, Storage 등) 연동을 위한 초기화를 담당한다.

[설정 방법]
1. Firebase Console → 프로젝트 설정 → 서비스 계정
2. '새 비공개 키 생성' 클릭하여 JSON 파일 다운로드
3. 다운로드한 파일을 app/core/firebase-key.json 경로에 배치
4. .gitignore에 해당 파일 추가 (보안상 필수)
5. .env에 FIREBASE_STORAGE_BUCKET 설정 (예: project-id.appspot.com)
"""
import firebase_admin
from firebase_admin import credentials

from app.core.config import settings


def initialize_firebase() -> None:
    """
    Firebase Admin SDK 초기화 (Auth + Storage).

    이미 초기화된 경우 재초기화하지 않음 (멱등성 보장).

    Raises:
        FileNotFoundError: firebase-key.json 파일이 없는 경우
        ValueError: JSON 파일 형식이 올바르지 않은 경우
    """
    if firebase_admin._apps:
        return  # 이미 초기화됨

    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)

    # Storage 버킷이 설정된 경우 함께 초기화
    options = {}
    if settings.FIREBASE_STORAGE_BUCKET:
        options["storageBucket"] = settings.FIREBASE_STORAGE_BUCKET

    firebase_admin.initialize_app(cred, options if options else None)
    print("[Firebase] Admin SDK initialized")