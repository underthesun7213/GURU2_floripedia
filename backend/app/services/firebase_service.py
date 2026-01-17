import firebase_admin
from firebase_admin import credentials, storage
from app.core.config import settings
import os


class FirebaseService:
    """Firebase Storage 서비스 클래스"""
    
    _initialized = False
    
    @classmethod
    def initialize(cls):
        """Firebase 초기화"""
        if not cls._initialized:
            if settings.FIREBASE_CREDENTIALS_PATH and os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred, {
                    'storageBucket': settings.FIREBASE_STORAGE_BUCKET
                })
            else:
                # 기본 인증 사용 (환경 변수에서)
                firebase_admin.initialize_app(options={
                    'storageBucket': settings.FIREBASE_STORAGE_BUCKET
                })
            cls._initialized = True
    
    @classmethod
    def upload_file(cls, file_data: bytes, file_name: str, content_type: str = None) -> str:
        """파일 업로드"""
        cls.initialize()
        bucket = storage.bucket()
        blob = bucket.blob(file_name)
        blob.upload_from_string(file_data, content_type=content_type)
        blob.make_public()
        return blob.public_url
    
    @classmethod
    def delete_file(cls, file_name: str):
        """파일 삭제"""
        cls.initialize()
        bucket = storage.bucket()
        blob = bucket.blob(file_name)
        blob.delete()
