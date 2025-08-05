"""
관리자 전용 API 엔드포인트
Supabase 기반 AI 설정 및 프롬프트 관리
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from app.services.supabase_service import supabase_service
from app.services.enhanced_ai_service import enhanced_ai_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


class AISettings(BaseModel):
    """AI 설정 모델"""
    provider: str = "openai"  # openai 또는 gemini
    openai_model: str = "gpt-4"
    gemini_model: str = "gemini-1.5-flash"
    temperature: float = 0.7
    max_tokens: int = 2000


class PromptUpdate(BaseModel):
    """프롬프트 업데이트 모델"""
    prompt_type: str
    prompt_content: str


# 기존 호환성을 위한 함수들 (deprecated)
def load_ai_settings_from_db():
    """기존 호환성을 위한 함수 - deprecated"""
    logger.warning("load_ai_settings_from_db는 deprecated입니다. enhanced_ai_service를 사용하세요.")
    return {
        "default_provider": "openai",
        "openai_model_name": "gpt-4",
        "gemini_model_name": "gemini-1.5-flash"
    }


def load_prompts_from_db():
    """기존 호환성을 위한 함수 - deprecated"""
    logger.warning("load_prompts_from_db는 deprecated입니다. enhanced_ai_service를 사용하세요.")
    return {
        "ai_brainstorming": "기본 AI 브레인스토밍 프롬프트",
        "final_optimization": "기본 최종 최적화 프롬프트"
    }


@router.get("/ai-settings")
async def get_ai_settings():
    """현재 AI 설정 조회"""
    try:
        settings = await enhanced_ai_service.get_current_ai_settings()
        return {
            "success": True,
            "data": settings,
            "message": f"현재 AI 제공자: {settings.get('provider', 'openai')}"
        }
    except Exception as e:
        logger.error(f"AI 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/ai-settings")
async def update_ai_settings(settings: AISettings):
    """AI 설정 업데이트"""
    try:
        settings_dict = settings.model_dump()
        success = await enhanced_ai_service.update_ai_settings(settings_dict)
        
        if success:
            return {
                "success": True,
                "message": f"AI 설정이 성공적으로 업데이트되었습니다. 현재 제공자: {settings_dict['provider']}",
                "data": settings_dict
            }
        else:
            raise HTTPException(status_code=500, detail="AI 설정 저장에 실패했습니다")
            
    except Exception as e:
        logger.error(f"AI 설정 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompts/{prompt_type}")
async def get_prompt(prompt_type: str):
    """특정 타입의 프롬프트 조회"""
    try:
        prompt_content = await enhanced_ai_service.get_master_prompt(prompt_type)
        return {
            "success": True,
            "data": {
                "prompt_type": prompt_type,
                "prompt_content": prompt_content
            }
        }
    except Exception as e:
        logger.error(f"프롬프트 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompts")
async def get_all_prompts():
    """모든 프롬프트 조회 (기본 타입들)"""
    try:
        prompt_types = ['itinerary_generation', 'place_recommendation', 'optimization']
        prompts = {}
        
        for prompt_type in prompt_types:
            try:
                prompts[prompt_type] = await enhanced_ai_service.get_master_prompt(prompt_type)
            except:
                prompts[prompt_type] = "프롬프트를 찾을 수 없습니다."
        
        return {
            "success": True,
            "data": prompts
        }
    except Exception as e:
        logger.error(f"프롬프트 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/prompts")
async def update_prompt(prompt_update: PromptUpdate):
    """프롬프트 업데이트"""
    try:
        success = await enhanced_ai_service.update_master_prompt(
            prompt_update.prompt_type, 
            prompt_update.prompt_content
        )
        
        if success:
            return {
                "success": True,
                "message": f"'{prompt_update.prompt_type}' 프롬프트가 성공적으로 업데이트되었습니다",
                "data": {
                    "prompt_type": prompt_update.prompt_type,
                    "updated": True
                }
            }
        else:
            raise HTTPException(status_code=500, detail="프롬프트 저장에 실패했습니다")
            
    except Exception as e:
        logger.error(f"프롬프트 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompts/{prompt_type}/history")
async def get_prompt_history(prompt_type: str):
    """프롬프트 히스토리 조회"""
    try:
        history = await enhanced_ai_service.get_prompt_history(prompt_type)
        return {
            "success": True,
            "data": {
                "prompt_type": prompt_type,
                "history": history
            }
        }
    except Exception as e:
        logger.error(f"프롬프트 히스토리 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/status")
async def get_system_status():
    """시스템 상태 조회"""
    try:
        ai_settings = await enhanced_ai_service.get_current_ai_settings()
        supabase_connected = supabase_service.is_connected()
        
        return {
            "success": True,
            "data": {
                "supabase_connected": supabase_connected,
                "current_ai_provider": ai_settings.get('provider', 'unknown'),
                "ai_model": ai_settings.get(f"{ai_settings.get('provider', 'openai')}_model", 'unknown'),
                "system_ready": supabase_connected and ai_settings.get('provider') is not None
            }
        }
    except Exception as e:
        logger.error(f"시스템 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/ai-generation")
async def test_ai_generation():
    """AI 생성 기능 테스트"""
    try:
        test_data = {
            "목적지": "대한민국 서울",
            "여행기간_일": 2,
            "사용자_선택_장소": [
                {
                    "장소_id": "test_1",
                    "이름": "경복궁",
                    "타입": "관광",
                    "위도": 37.5796,
                    "경도": 126.9770,
                    "사전_그룹": 1
                },
                {
                    "장소_id": "test_2", 
                    "이름": "명동",
                    "타입": "쇼핑",
                    "위도": 37.5636,
                    "경도": 126.9834,
                    "사전_그룹": 1
                }
            ]
        }
        
        result = await enhanced_ai_service.generate_itinerary_with_master_prompt(test_data)
        
        return {
            "success": True,
            "message": "AI 생성 테스트 완료",
            "data": {
                "test_input": test_data,
                "ai_response": result[:500] + "..." if len(result) > 500 else result,
                "response_length": len(result)
            }
        }
    except Exception as e:
        logger.error(f"AI 생성 테스트 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def admin_health():
    """관리자 API 상태 확인"""
    return {
        "status": "healthy",
        "message": "Admin API is running with Supabase integration",
        "timestamp": datetime.now().isoformat(),
        "supabase_connected": supabase_service.is_connected()
    }


@router.get("/info")
async def admin_info():
    """관리자 API 정보 조회"""
    try:
        current_settings = await enhanced_ai_service.get_current_ai_settings()
        
        return {
            "api_name": "Plango Admin API v2.0",
            "version": "2.0.0 (Supabase Enhanced)",
            "current_ai_provider": current_settings.get("provider", "unknown"),
            "supported_providers": ["openai", "gemini"],
            "supabase_integrated": True,
            "features": [
                "실시간 AI 제공자 전환",
                "Supabase 기반 설정 관리", 
                "마스터 프롬프트 버전 관리",
                "프롬프트 히스토리 추적"
            ],
            "endpoints": [
                "GET /api/v1/admin/ai-settings - AI 설정 조회",
                "PUT /api/v1/admin/ai-settings - AI 설정 업데이트",
                "GET /api/v1/admin/prompts - 모든 프롬프트 조회",
                "GET /api/v1/admin/prompts/{type} - 특정 프롬프트 조회",
                "PUT /api/v1/admin/prompts - 프롬프트 업데이트",
                "GET /api/v1/admin/prompts/{type}/history - 프롬프트 히스토리",
                "GET /api/v1/admin/system/status - 시스템 상태",
                "POST /api/v1/admin/test/ai-generation - AI 생성 테스트",
                "GET /api/v1/admin/health - 상태 확인",
                "GET /api/v1/admin/info - API 정보"
            ]
        }
    except Exception as e:
        logger.error(f"관리자 정보 조회 실패: {e}")
        # 에러가 발생해도 기본 정보는 반환
        return {
            "api_name": "Plango Admin API v2.0",
            "version": "2.0.0 (Supabase Enhanced)",
            "status": "partial",
            "error": str(e)
        }