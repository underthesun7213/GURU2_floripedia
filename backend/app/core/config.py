from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Gemini API
    GEMINI_API_KEY: str
    
    # MongoDB Atlas
    MONGODB_URL: str
    
    # Firebase
    FIREBASE_STORAGE_BUCKET: str
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    
    # Security
    JWT_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
