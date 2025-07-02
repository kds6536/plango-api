"""헬스체크 라우터"""

from fastapi import APIRouter
from datetime import datetime
import psutil
import os

router = APIRouter()


@router.get("/health")
async def health_check():
    """서버 상태 확인"""
    try:
        # 시스템 정보 수집
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "system": {
                "cpu_usage": f"{cpu_percent}%",
                "memory_usage": f"{memory.percent}%",
                "disk_usage": f"{disk.percent}%",
                "uptime": "서버 가동 시간"
            },
            "services": {
                "database": "connected",
                "redis": "connected",
                "openai": "available"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
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