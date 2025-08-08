"""
Railway 환경에서 Supabase 연결 진단을 위한 엔드포인트
"""

import os
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from app.services.supabase_service import supabase_service
from app.config import settings

router = APIRouter(
    prefix="/diagnosis",
    tags=["diagnosis"]
)

logger = logging.getLogger(__name__)


@router.get("/supabase-connection")
async def diagnose_supabase_connection() -> Dict[str, Any]:
    """Railway 환경에서 Supabase 연결 상태 진단"""
    try:
        result = {
            "timestamp": "현재 시각",
            "environment": "Railway Production",
            "supabase_config": {},
            "connection_test": {},
            "tables_test": {},
            "prompts_test": {}
        }
        
        # 1. 환경변수 확인
        result["supabase_config"] = {
            "SUPABASE_URL_exists": bool(settings.SUPABASE_URL),
            "SUPABASE_KEY_exists": bool(settings.SUPABASE_KEY),
            "SUPABASE_URL_preview": settings.SUPABASE_URL[:50] + "..." if settings.SUPABASE_URL else "None",
            "SUPABASE_KEY_preview": settings.SUPABASE_KEY[:20] + "...***" if settings.SUPABASE_KEY else "None"
        }
        
        # 2. 연결 테스트
        try:
            is_connected = supabase_service.is_connected()
            result["connection_test"] = {
                "success": is_connected,
                "message": "Supabase 클라이언트 연결 성공" if is_connected else "Supabase 클라이언트 연결 실패"
            }
        except Exception as e:
            result["connection_test"] = {
                "success": False,
                "error": str(e)
            }
        
        # 3. 기본 테이블 접근 테스트 (settings)
        try:
            settings_response = supabase_service.client.table('settings').select('*').limit(1).execute()
            result["tables_test"]["settings"] = {
                "success": True,
                "data_count": len(settings_response.data) if settings_response.data else 0
            }
        except Exception as e:
            result["tables_test"]["settings"] = {
                "success": False,
                "error": str(e)
            }
        
        # 4. prompts 테이블 접근 테스트
        try:
            prompts_response = supabase_service.client.table('prompts').select('*').limit(1).execute()
            result["prompts_test"] = {
                "success": True,
                "data_count": len(prompts_response.data) if prompts_response.data else 0,
                "message": "prompts 테이블 접근 성공"
            }
        except Exception as e:
            result["prompts_test"] = {
                "success": False,
                "error": str(e),
                "message": "prompts 테이블 접근 실패"
            }
        
        # 5. 마스터 프롬프트 조회 테스트
        try:
            test_prompt = await supabase_service.get_master_prompt("place_recommendation_v1")
            result["prompts_test"]["master_prompt_test"] = {
                "success": True,
                "prompt_length": len(test_prompt),
                "message": "마스터 프롬프트 조회 성공"
            }
        except Exception as e:
            result["prompts_test"]["master_prompt_test"] = {
                "success": False,
                "error": str(e),
                "message": "마스터 프롬프트 조회 실패"
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Supabase 진단 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"진단 실패: {str(e)}")


@router.get("/environment-variables")
async def check_environment_variables() -> Dict[str, Any]:
    """Railway 환경변수 확인"""
    try:
        return {
            "SUPABASE_URL": settings.SUPABASE_URL[:50] + "..." if settings.SUPABASE_URL else "Missing",
            "SUPABASE_KEY": "Set" if settings.SUPABASE_KEY else "Missing",
            "OPENAI_API_KEY": "Set" if settings.OPENAI_API_KEY else "Missing", 
            "GEMINI_API_KEY": "Set" if settings.GEMINI_API_KEY else "Missing",
            "MAPS_PLATFORM_API_KEY": "Set" if settings.GOOGLE_MAPS_API_KEY else "Missing",
            "ENV": settings.ENV,
            "ENVIRONMENT": settings.ENVIRONMENT
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"환경변수 확인 실패: {str(e)}")
