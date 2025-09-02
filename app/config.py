"""애플리케이션 설정 관리"""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """애플리케이션 설정 클래스"""
    
    # 프로젝트 정보
    PROJECT_NAME: str = "plango-api"
    PROJECT_VERSION: str = "2.1.1"

    # 서버 설정
    ENV: str = "development"
    ENVIRONMENT: str = "development"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True
    
    # API 키
    OPENAI_API_KEY: str = ""
    openai_api_key: str = ""  # 하위 호환성을 위한 별칭
    GEMINI_API_KEY: str = ""
    gemini_api_key: str = ""  # 하위 호환성을 위한 별칭
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    
    # Supabase 설정
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    
    # 데이터베이스 설정
    DATABASE_URL: str = "postgresql://username:password@localhost:5432/plango_db"
    
    # Redis 설정
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # CORS 설정
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003,http://localhost:3004,http://localhost:3005,https://plango-zeta.vercel.app,https://plango.kr,https://www.plango.kr"
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000", 
        "http://localhost:3001", 
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:3004",
        "http://localhost:3005",
        "https://plango-zeta.vercel.app",
        "https://plango.kr",              # 커스텀 도메인 (루트)
        "https://www.plango.kr"           # 커스텀 도메인 (www)
    ]
    
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
    
    # 로깅 설정
    LOGGING_LEVEL: str = "INFO"
    
    # Google Maps Platform API Key (Backend - Server-side use only)
    # This key is for server-side use only and must be kept secret.
    # It should NOT have HTTP Referer restrictions.
    MAPS_PLATFORM_API_KEY_BACKEND: str = ""

    # Config 클래스 완전 제거 (env_file 등은 model_config로 대체)
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "allow"
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 하위 호환성을 위한 속성 매핑
        if self.OPENAI_API_KEY and not self.openai_api_key:
            self.openai_api_key = self.OPENAI_API_KEY
        if self.GEMINI_API_KEY and not self.gemini_api_key:
            self.gemini_api_key = self.GEMINI_API_KEY


# 전역 설정 인스턴스
settings = Settings() 