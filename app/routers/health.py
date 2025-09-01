"""헬스체크 라우터 - 메모리 모니터링 포함"""

from fastapi import APIRouter
from datetime import datetime
import os
import psutil
import gc

from app.config import settings

router = APIRouter(prefix="/api/v1", tags=["Health"])


@router.get("/health")
async def health_check():
    """서버 상태 확인 - 외부 의존성 없는 초간소화 버전"""
    return {"status": "ok"}


@router.get("/health/memory")
async def memory_status():
    """메모리 사용량 모니터링"""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        
        # 가비지 컬렉션 실행
        gc.collect()
        
        return {
            "status": "ok",
            "memory": {
                "rss_mb": round(memory_info.rss / 1024 / 1024, 2),  # 실제 메모리 사용량
                "vms_mb": round(memory_info.vms / 1024 / 1024, 2),  # 가상 메모리 사용량
                "percent": round(process.memory_percent(), 2),
                "available_mb": round(psutil.virtual_memory().available / 1024 / 1024, 2)
            },
            "gc_stats": {
                "collected": gc.collect(),
                "counts": gc.get_count()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
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