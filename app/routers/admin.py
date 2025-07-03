"""
관리자 전용 API 라우터
AI 제공자 설정, 시스템 설정 등을 관리합니다
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel

# --- 변경점 1: 필요한 Supabase 라이브러리 import ---
import os
from supabase import create_client, Client

from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

# --- 변경점 2: 파일 경로 대신 Supabase 클라이언트 설정 ---
# 이 설정은 환경 변수에서 가져옵니다.
try:
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)
    logger.info("Supabase 클라이언트가 성공적으로 초기화되었습니다.")
except Exception as e:
    logger.error(f"Supabase 클라이언트 초기화 실패: {e}")
    supabase = None

# AI 설정 요청/응답 모델
class AISettingsRequest(BaseModel):
    default_provider: str
    openai_model_name: str
    gemini_model_name: str

class AISettingsResponse(BaseModel):
    default_provider: str
    openai_model_name: str
    gemini_model_name: str
    # created_at: datetime  # DB에서 직접 가져오므로 모델에서 필요 없을 수 있음

def load_ai_settings_from_db() -> Dict[str, Any]:
    """AI 설정을 Supabase DB에서 로드"""
    if not supabase:
        raise HTTPException(status_code=500, detail="데이터베이스 연결이 설정되지 않았습니다.")
        
    try:
        # 'settings' 테이블에서 모든 데이터를 가져옵니다.
        response = supabase.table('settings').select('key, value').execute()
        data = response.get('data', [])
        
        # 키-값 리스트를 하나의 딕셔너리로 변환합니다.
        # 예: [{'key': 'default_provider', 'value': 'openai'}] -> {'default_provider': 'openai'}
        settings_dict = {item['key']: item['value'] for item in data}
        
        if not settings_dict:
            logger.warning("DB에 설정이 없습니다. 기본 설정을 반환합니다.")
            # DB에 데이터가 없을 경우를 대비한 기본값
            return {
                "default_provider": "openai",
                "openai_model_name": "gpt-4o",
                "gemini_model_name": "gemini-1.5-pro-latest"
            }
        
        return settings_dict
    except Exception as e:
        logger.error(f"DB에서 AI 설정 로드 실패: {e}")
        raise HTTPException(status_code=500, detail="데이터베이스에서 설정을 불러오는 데 실패했습니다.")

def save_ai_settings_to_db(settings: AISettingsRequest):
    """AI 설정을 Supabase DB에 저장"""
    if not supabase:
        raise HTTPException(status_code=500, detail="데이터베이스 연결이 설정되지 않았습니다.")

    try:
        # 받은 데이터를 기반으로 각 설정을 하나씩 업데이트합니다.
        # .upsert()는 데이터가 있으면 update, 없으면 insert를 해줘서 더 안정적입니다.
        supabase.table('settings').upsert({'key': 'default_provider', 'value': settings.default_provider}).execute()
        supabase.table('settings').upsert({'key': 'openai_model_name', 'value': settings.openai_model_name}).execute()
        supabase.table('settings').upsert({'key': 'gemini_model_name', 'value': settings.gemini_model_name}).execute()

        logger.info(f"DB에 AI 설정 저장 완료: {settings.dict()}")
    except Exception as e:
        logger.error(f"DB에 AI 설정 저장 실패: {e}")
        raise HTTPException(status_code=500, detail="데이터베이스에 설정을 저장하는 데 실패했습니다.")

@router.get("/ai-settings")
async def get_ai_settings():
    """
    현재 AI 제공자 설정을 DB에서 조회합니다.
    """
    settings = load_ai_settings_from_db()
    return settings

@router.put("/ai-settings")
async def update_ai_settings(request: AISettingsRequest):
    """
    AI 제공자 설정을 DB에 업데이트합니다.
    """
    save_ai_settings_to_db(request)
    # 저장 후 최신 데이터를 다시 읽어서 반환
    updated_settings = load_ai_settings_from_db()
    return updated_settings

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
    current_settings = load_ai_settings_from_db()
    
    return {
        "api_name": "Plango Admin API",
        "version": "1.1.0 (DB-Connected)",
        "current_ai_provider": current_settings.get("default_provider"),
        "supported_providers": ["openai", "gemini"],
        "endpoints": [
            "GET /api/v1/admin/ai-settings - AI 설정 조회",
            "PUT /api/v1/admin/ai-settings - AI 설정 업데이트",
            "GET /api/v1/admin/health - 상태 확인",
            "GET /api/v1/admin/info - API 정보"
        ]
    } 