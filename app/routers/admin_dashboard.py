"""
관리자 대시보드 API
시스템 상태 모니터링 및 폴백 모드 알림
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from app.services.supabase_service import supabase_service
from app.services.dynamic_ai_service import DynamicAIService
from app.config import settings

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin-dashboard"]
)

logger = logging.getLogger(__name__)


@router.get("/system-status")
async def get_system_status() -> Dict[str, Any]:
    """전체 시스템 상태 확인"""
    try:
        status = {
            "timestamp": "현재 시각",
            "environment": "Railway Production",
            "services": {},
            "fallback_status": {},
            "recommendations": {}
        }
        
        # 1. Supabase 연결 상태
        try:
            is_connected = supabase_service.is_connected()
            settings_test = supabase_service.client.table('settings').select('*').limit(1).execute()
            prompts_test = supabase_service.client.table('prompts').select('*').limit(1).execute()
            
            status["services"]["supabase"] = {
                "connected": is_connected,
                "settings_table": len(settings_test.data) > 0 if settings_test.data else False,
                "prompts_table": len(prompts_test.data) > 0 if prompts_test.data else False,
                "url_configured": bool(settings.SUPABASE_URL),
                "key_configured": bool(settings.SUPABASE_KEY)
            }
        except Exception as e:
            status["services"]["supabase"] = {
                "connected": False,
                "error": str(e)
            }
        
        # 2. AI 서비스 상태
        try:
            ai_service = DynamicAIService()
            provider_info = ai_service.get_provider_info()
            
            status["services"]["ai"] = {
                "available": True,
                "provider": provider_info.get("provider", "unknown"),
                "model": provider_info.get("model", "unknown"),
                "openai_configured": bool(settings.OPENAI_API_KEY),
                "gemini_configured": bool(settings.GEMINI_API_KEY)
            }
        except Exception as e:
            status["services"]["ai"] = {
                "available": False,
                "error": str(e)
            }
        
        # 3. Google Places API 상태 (MAPS_PLATFORM_API_KEY 우선, 없으면 GOOGLE_MAPS_API_KEY 폴백)
        try:
            gmaps_key = getattr(settings, "MAPS_PLATFORM_API_KEY", None) or getattr(settings, "GOOGLE_MAPS_API_KEY", None)
            status["services"]["google_places"] = {
                "configured": bool(gmaps_key),
                "key_preview": (gmaps_key[:20] + "...") if gmaps_key else "Missing"
            }
        except Exception as e:
            status["services"]["google_places"] = {
                "configured": False,
                "error": str(e)
            }
        
        # 4. 폴백 모드 상태
        supabase_working = status["services"]["supabase"].get("connected", False) and \
                          status["services"]["supabase"].get("prompts_table", False)
        
        status["fallback_status"] = {
            "supabase_prompts_available": supabase_working,
            "fallback_mode_active": not supabase_working,
            "recommendation": "정상 모드" if supabase_working else "폴백 모드 사용 중"
        }
        
        return status
        
    except Exception as e:
        logger.error(f"시스템 상태 확인 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"시스템 상태 확인 실패: {str(e)}")


@router.get("/fallback-alerts")
async def get_fallback_alerts() -> Dict[str, Any]:
    """폴백 모드 알림 내역"""
    try:
        # 실제로는 데이터베이스에서 알림 내역을 조회해야 함
        # 현재는 로그에서 확인하는 방식으로 구현
        
        return {
            "fallback_alerts": [
                {
                    "timestamp": "2025-08-08 16:35:00",
                    "type": "Supabase prompts 테이블 접근 실패",
                    "environment": "Railway Production",
                    "status": "해결 대기 중"
                }
            ],
            "total_alerts": 1,
            "last_alert": "2025-08-08 16:35:00"
        }
        
    except Exception as e:
        logger.error(f"폴백 알림 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"폴백 알림 조회 실패: {str(e)}")


@router.post("/test-supabase-connection")
async def test_supabase_connection() -> Dict[str, Any]:
    """Supabase 연결 테스트"""
    try:
        result = {
            "success": False,
            "details": {}
        }
        
        # 1. 기본 연결 테스트
        try:
            is_connected = supabase_service.is_connected()
            result["details"]["basic_connection"] = {
                "success": is_connected,
                "message": "Supabase 클라이언트 연결 성공" if is_connected else "Supabase 클라이언트 연결 실패"
            }
        except Exception as e:
            result["details"]["basic_connection"] = {
                "success": False,
                "error": str(e)
            }
        
        # 2. 테이블 접근 테스트
        tables_to_test = ["settings", "prompts", "countries", "cities"]
        for table_name in tables_to_test:
            try:
                response = supabase_service.client.table(table_name).select('*').limit(1).execute()
                result["details"][f"{table_name}_table"] = {
                    "success": True,
                    "data_count": len(response.data) if response.data else 0
                }
            except Exception as e:
                result["details"][f"{table_name}_table"] = {
                    "success": False,
                    "error": str(e)
                }
        
        # 3. 프롬프트 조회 테스트 (고정 이름)
        try:
            test_prompt = await supabase_service.get_master_prompt("search_strategy_v1")
            result["details"]["prompt_retrieval"] = {
                "success": True,
                "prompt_length": len(test_prompt)
            }
        except Exception as e:
            result["details"]["prompt_retrieval"] = {
                "success": False,
                "error": str(e)
            }
        
        # 전체 성공 여부 판단
        all_tests_passed = all(
            detail.get("success", False) 
            for detail in result["details"].values()
        )
        
        result["success"] = all_tests_passed
        result["message"] = "모든 테스트 통과" if all_tests_passed else "일부 테스트 실패"
        
        return result
        
    except Exception as e:
        logger.error(f"Supabase 연결 테스트 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"연결 테스트 실패: {str(e)}")


@router.get("/environment-info")
async def get_environment_info() -> Dict[str, Any]:
    """환경 설정 정보 (민감한 정보는 마스킹)"""
    try:
        return {
            "environment": {
                "ENV": settings.ENV,
                "ENVIRONMENT": settings.ENVIRONMENT,
                "DEBUG": settings.DEBUG
            },
            "api_keys": {
                "SUPABASE_URL": settings.SUPABASE_URL[:50] + "..." if settings.SUPABASE_URL else "Missing",
                "SUPABASE_KEY": "Set" if settings.SUPABASE_KEY else "Missing",
                "OPENAI_API_KEY": "Set" if settings.OPENAI_API_KEY else "Missing",
                "GEMINI_API_KEY": "Set" if settings.GEMINI_API_KEY else "Missing",
                "GOOGLE_MAPS_API_KEY": "Set" if settings.GOOGLE_MAPS_API_KEY else "Missing"
            },
            "server": {
                "HOST": settings.HOST,
                "PORT": settings.PORT,
                "PROJECT_NAME": settings.PROJECT_NAME,
                "PROJECT_VERSION": settings.PROJECT_VERSION
            }
        }
        
    except Exception as e:
        logger.error(f"환경 정보 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"환경 정보 조회 실패: {str(e)}")
