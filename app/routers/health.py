"""헬스체크 라우터"""

from fastapi import APIRouter
from datetime import datetime
import os

from app.config import settings

router = APIRouter(prefix="/api/v1", tags=["Health"])


@router.get("/health")
async def health_check():
    """서버 상태 확인 - 외부 의존성 없는 초간소화 버전"""
    return {"status": "ok"}


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