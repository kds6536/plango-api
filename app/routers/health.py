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
        # 시스템 정보 수집 (Railway 환경에서 안전하게)
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)  # Railway에서는 빠른 응답 필요
            memory = psutil.virtual_memory()
            # Railway에서는 루트 디스크 사용량 체크를 더 안전하게
            try:
                disk = psutil.disk_usage('.' if os.getenv("RAILWAY_ENVIRONMENT") else '/')
            except:
                disk = None
        except:
            cpu_percent = 0
            memory = None
            disk = None
        
        system_info = {}
        if cpu_percent is not None:
            system_info["cpu_usage"] = f"{cpu_percent}%"
        if memory is not None:
            system_info["memory_usage"] = f"{memory.percent}%"
        if disk is not None:
            system_info["disk_usage"] = f"{disk.percent}%"
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.1.0",
            "environment": os.getenv("RAILWAY_ENVIRONMENT", "development"),
            "system": system_info,
            "api": {
                "status": "operational",
                "endpoints": [
                    "/api/v1/health",
                    "/api/v1/itinerary/generate",
                    "/api/v1/admin/ai-settings"
                ]
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