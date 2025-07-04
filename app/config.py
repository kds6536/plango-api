"""애플리케이션 설정 관리"""

import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정 클래스"""
    
    # 서버 설정
    ENV: str = "development"
    ENVIRONMENT: str = "development"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True
    
    # API 키
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GOOGLE_PLACES_API_KEY: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    
    # Supabase 설정
    SUPABASE_URL: str = ""
    SUPABASE_API_KEY: str = ""
    
    # 데이터베이스 설정
    DATABASE_URL: str = "postgresql://username:password@localhost:5432/plango_db"
    
    # Redis 설정
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # CORS 설정
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001,https://plango.vercel.app,https://plango-production-24ea.up.railway.app"
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """ALLOWED_ORIGINS 문자열을 리스트로 변환"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    # JWT 설정
    SECRET_KEY: str = "your_secret_key_here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 외부 API 설정
    GOOGLE_MAPS_API_KEY: str = ""
    WEATHER_API_KEY: str = ""
    
    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 전역 설정 인스턴스
settings = Settings() 