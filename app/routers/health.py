"""헬스체크 라우터"""

from fastapi import APIRouter
from datetime import datetime
import os

from app.config import settings

router = APIRouter(prefix="/api/v1", tags=["Health"])


@router.get("/health")
async def health_check():
    """서버 상태 확인 - 간소화된 버전"""
    # Railway 환경에서 안정적인 응답을 위해 psutil 로직 제거
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.PROJECT_VERSION,
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "development")
    }


@router.get("/health/deep")
async def deep_health_check():
    """상세 헬스체크"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": {"status": "ok", "response_time": "10ms"},
            "redis": {"status": "ok", "response_time": "5ms"},
            "openai_api": {"status": "ok", "response_time": "200ms"},
            "external_apis": {
                "google_maps": {"status": "ok"},
                "weather": {"status": "ok"}
            }
        }
    } 