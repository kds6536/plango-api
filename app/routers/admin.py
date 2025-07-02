"""
관리자 전용 API 라우터
AI 제공자 설정, 시스템 설정 등을 관리합니다
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Dict, Any
import json
import os
from pydantic import BaseModel

from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

# AI 설정 데이터를 저장할 파일 경로
AI_SETTINGS_FILE = "app/data/ai_settings.json"

# AI 설정 요청/응답 모델
class AISettingsRequest(BaseModel):
    provider: str  # 'openai' 또는 'gemini'
    updated_by: str

class AISettingsResponse(BaseModel):
    provider: str
    last_updated: str
    updated_by: str

def ensure_data_directory():
    """데이터 디렉토리가 존재하는지 확인하고 없으면 생성"""
    os.makedirs("app/data", exist_ok=True)

def load_ai_settings() -> Dict[str, Any]:
    """AI 설정을 파일에서 로드"""
    ensure_data_directory()
    
    try:
        if os.path.exists(AI_SETTINGS_FILE):
            with open(AI_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"AI 설정 로드 실패: {e}")
    
    # 기본 설정 반환
    return {
        "provider": "openai",
        "last_updated": datetime.now().isoformat(),
        "updated_by": "system"
    }

def save_ai_settings(settings: Dict[str, Any]):
    """AI 설정을 파일에 저장"""
    ensure_data_directory()
    
    try:
        with open(AI_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        logger.info(f"AI 설정 저장 완료: {settings}")
    except Exception as e:
        logger.error(f"AI 설정 저장 실패: {e}")
        raise HTTPException(status_code=500, detail="설정 저장에 실패했습니다")

@router.get("/ai-settings", response_model=AISettingsResponse)
async def get_ai_settings():
    """
    현재 AI 제공자 설정을 조회합니다
    """
    try:
        settings = load_ai_settings()
        logger.info(f"AI 설정 조회: {settings}")
        return AISettingsResponse(**settings)
    except Exception as e:
        logger.error(f"AI 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="설정 조회에 실패했습니다")

@router.put("/ai-settings", response_model=AISettingsResponse)
async def update_ai_settings(request: AISettingsRequest):
    """
    AI 제공자 설정을 업데이트합니다
    """
    if request.provider not in ['openai', 'gemini']:
        raise HTTPException(
            status_code=400, 
            detail="provider는 'openai' 또는 'gemini'여야 합니다"
        )
    
    try:
        # 새로운 설정 생성
        new_settings = {
            "provider": request.provider,
            "last_updated": datetime.now().isoformat(),
            "updated_by": request.updated_by
        }
        
        # 설정 저장
        save_ai_settings(new_settings)
        
        logger.info(f"AI 제공자가 {request.provider}로 변경됨 (by: {request.updated_by})")
        
        return AISettingsResponse(**new_settings)
        
    except Exception as e:
        logger.error(f"AI 설정 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail="설정 업데이트에 실패했습니다")

@router.get("/health")
async def admin_health():
    """
    관리자 API 상태 확인
    """
    return {
        "status": "healthy",
        "message": "Admin API is running",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/info")
async def admin_info():
    """
    관리자 API 정보 조회
    """
    current_settings = load_ai_settings()
    
    return {
        "api_name": "Plango Admin API",
        "version": "1.0.0",
        "current_ai_provider": current_settings.get("provider", "openai"),
        "supported_providers": ["openai", "gemini"],
        "endpoints": [
            "GET /api/v1/admin/ai-settings - AI 설정 조회",
            "PUT /api/v1/admin/ai-settings - AI 설정 업데이트",
            "GET /api/v1/admin/health - 상태 확인",
            "GET /api/v1/admin/info - API 정보"
        ]
    } 