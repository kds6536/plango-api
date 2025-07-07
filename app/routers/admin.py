"""
관리자 전용 API 라우터
AI 제공자 설정, 시스템 설정 등을 관리합니다
"""

from fastapi import APIRouter, HTTPException, Request
from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel

# --- 변경점 1: 필요한 Supabase 라이브러리 import ---
import os
from supabase import create_client, Client

from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["관리자 API"])

# --- 변경점 2: 파일 경로 대신 Supabase 클라이언트 설정 ---
# 이 설정은 환경 변수에서 가져옵니다.
try:
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_API_KEY")  # Railway에서 설정한 환경 변수명과 일치
    
    if not url or not key:
        raise ValueError(f"환경 변수 누락: SUPABASE_URL={url}, SUPABASE_API_KEY={'설정됨' if key else '누락'}")
        
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

# --- 프롬프트 모델 추가 ---
class PromptsRequest(BaseModel):
    stage1_destinations_prompt: str
    stage3_detailed_itinerary_prompt: str

def load_ai_settings_from_db() -> Dict[str, Any]:
    """AI 설정을 Supabase DB에서 로드"""
    if not supabase:
        raise HTTPException(status_code=500, detail="데이터베이스 연결이 설정되지 않았습니다.")
        
    try:
        # 'settings' 테이블에서 모든 데이터를 가져옵니다.
        logger.info("Supabase에서 settings 테이블 조회 시작")
        response = supabase.table('settings').select('key, value').execute()
        logger.info(f"Supabase 응답 타입: {type(response)}")
        logger.info(f"Supabase 응답 속성들: {dir(response)}")
        
        # 다양한 방법으로 데이터 접근 시도
        data = []
        if hasattr(response, 'data'):
            data = response.data
            logger.info(f"response.data 사용: {data}")
        elif hasattr(response, 'json'):
            json_data = response.json()
            data = json_data.get('data', [])
            logger.info(f"response.json() 사용: {data}")
        else:
            logger.error("응답에서 데이터를 추출할 수 없습니다.")
            # 기본값 반환
            return {
                "default_provider": "openai",
                "openai_model_name": "gpt-4o",
                "gemini_model_name": "gemini-1.5-pro-latest"
            }
            
        logger.info(f"조회된 데이터: {data}")
        
        # 키-값 리스트를 하나의 딕셔너리로 변환합니다.
        # 예: [{'key': 'default_provider', 'value': 'openai'}] -> {'default_provider': 'openai'}
        settings_dict = {item['key']: item['value'] for item in data}
        
        if not settings_dict:
            logger.warning("DB에 설정이 없습니다. 기본 설정을 반환합니다.")
            # DB에 데이터가 없을 경우를 대비한 기본값
            default_settings = {
                "default_provider": "openai",
                "openai_model_name": "gpt-4o",
                "gemini_model_name": "gemini-1.5-pro-latest"
            }
            # 기본값을 DB에 저장
            try:
                supabase.table('settings').upsert({
                    'key': 'default_provider', 
                    'value': 'openai',
                    'is_encrypted': False
                }).execute()
                supabase.table('settings').upsert({
                    'key': 'openai_model_name', 
                    'value': 'gpt-4o',
                    'is_encrypted': False
                }).execute()
                supabase.table('settings').upsert({
                    'key': 'gemini_model_name', 
                    'value': 'gemini-1.5-pro-latest',
                    'is_encrypted': False
                }).execute()
                logger.info("기본 설정을 DB에 저장했습니다.")
            except Exception as insert_error:
                logger.error(f"기본 설정 저장 실패: {insert_error}")
            
            return default_settings
        
        logger.info(f"최종 설정 딕셔너리: {settings_dict}")
        return settings_dict
    except Exception as e:
        logger.error(f"DB에서 AI 설정 로드 실패: {e}")
        logger.error(f"에러 타입: {type(e).__name__}")
        logger.error(f"에러 세부사항: {str(e)}")
        raise HTTPException(status_code=500, detail=f"데이터베이스에서 설정을 불러오는 데 실패했습니다: {str(e)}")

def save_ai_settings_to_db(settings: AISettingsRequest):
    """AI 설정을 Supabase DB에 저장"""
    if not supabase:
        raise HTTPException(status_code=500, detail="데이터베이스 연결이 설정되지 않았습니다.")

    try:
        # 받은 데이터를 기반으로 각 설정을 하나씩 업데이트합니다.
        # .upsert()는 데이터가 있으면 update, 없으면 insert를 해줘서 더 안정적입니다.
        logger.info(f"DB에 AI 설정 저장 시작: {settings.dict()}")
        
        # is_encrypted 컬럼을 포함하여 데이터 삽입
        response1 = supabase.table('settings').upsert({
            'key': 'default_provider', 
            'value': settings.default_provider,
            'is_encrypted': False
        }).execute()
        logger.info(f"default_provider 저장 완료: {response1}")
        
        response2 = supabase.table('settings').upsert({
            'key': 'openai_model_name', 
            'value': settings.openai_model_name,
            'is_encrypted': False
        }).execute()
        logger.info(f"openai_model_name 저장 완료: {response2}")
        
        response3 = supabase.table('settings').upsert({
            'key': 'gemini_model_name', 
            'value': settings.gemini_model_name,
            'is_encrypted': False
        }).execute()
        logger.info(f"gemini_model_name 저장 완료: {response3}")

        logger.info(f"DB에 AI 설정 저장 완료: {settings.dict()}")
    except Exception as e:
        logger.error(f"DB에 AI 설정 저장 실패: {e}")
        logger.error(f"에러 타입: {type(e).__name__}")
        logger.error(f"에러 세부사항: {str(e)}")
        raise HTTPException(status_code=500, detail=f"데이터베이스에 설정을 저장하는 데 실패했습니다: {str(e)}")

# --- 프롬프트 로드 함수 추가 ---
def load_prompts_from_db() -> Dict[str, Any]:
    """프롬프트를 Supabase DB에서 로드"""
    if not supabase:
        raise HTTPException(status_code=500, detail="데이터베이스 연결이 설정되지 않았습니다.")
    try:
        logger.info("Supabase에서 prompts 테이블 조회 시작")
        # 'prompts' 테이블에서 'key'와 'value'를 가져옵니다.
        response = supabase.table('prompts').select('key, value').execute()
        data = response.data
        logger.info(f"조회된 프롬프트 데이터: {data}")
        
        prompts_dict = {item['key']: item['value'] for item in data}
        
        if not prompts_dict or 'stage1_destinations_prompt' not in prompts_dict:
            logger.warning("DB에 프롬프트가 없습니다. 기본 프롬프트를 반환하고 저장합니다.")
            default_prompts = {
                "stage1_destinations_prompt": "You are a helpful assistant that extracts travel destinations from a user's request...",
                "stage3_detailed_itinerary_prompt": "You are a travel planning expert. Based on the provided list of destinations..."
            }
            # 기본 프롬프트를 DB에 저장
            try:
                supabase.table('prompts').upsert({
                    'key': 'stage1_destinations_prompt', 
                    'value': default_prompts['stage1_destinations_prompt']
                }).execute()
                supabase.table('prompts').upsert({
                    'key': 'stage3_detailed_itinerary_prompt', 
                    'value': default_prompts['stage3_detailed_itinerary_prompt']
                }).execute()
                logger.info("기본 프롬프트를 DB에 저장했습니다.")
            except Exception as insert_error:
                logger.error(f"기본 프롬프트 저장 실패: {insert_error}")
            
            return default_prompts
            
        logger.info(f"최종 프롬프트 딕셔너리: {prompts_dict}")
        return prompts_dict
    except Exception as e:
        logger.error(f"DB에서 프롬프트 로드 실패: {e}")
        raise HTTPException(status_code=500, detail=f"데이터베이스에서 프롬프트를 불러오는 데 실패했습니다: {str(e)}")

# --- 프롬프트 저장 함수 추가 ---
def save_prompts_to_db(prompts: PromptsRequest):
    """프롬프트를 Supabase DB에 저장"""
    if not supabase:
        raise HTTPException(status_code=500, detail="데이터베이스 연결이 설정되지 않았습니다.")

    try:
        logger.info(f"DB에 프롬프트 저장 시작: {prompts.dict()}")
        
        supabase.table('prompts').upsert({
            'key': 'stage1_destinations_prompt', 
            'value': prompts.stage1_destinations_prompt
        }).execute()
        
        supabase.table('prompts').upsert({
            'key': 'stage3_detailed_itinerary_prompt', 
            'value': prompts.stage3_detailed_itinerary_prompt
        }).execute()

        logger.info(f"DB에 프롬프트 저장 완료: {prompts.dict()}")
    except Exception as e:
        logger.error(f"DB에 프롬프트 저장 실패: {e}")
        raise HTTPException(status_code=500, detail=f"데이터베이스에 프롬프트를 저장하는 데 실패했습니다: {str(e)}")


@router.get("/ai-settings")
async def get_ai_settings():
    """
    현재 AI 제공자 설정을 반환합니다.
    """
    try:
        settings = load_ai_settings_from_db()
        return settings
    except Exception as e:
        logger.error(f"AI 설정 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/ai-settings")
async def update_ai_settings(request: AISettingsRequest):
    """
    AI 제공자 설정을 DB에 업데이트합니다.
    """
    try:
        logger.info(f"AI 설정 업데이트 요청 받음: {request.dict()}")
        
        save_ai_settings_to_db(request)
        # 저장 후 최신 데이터를 다시 읽어서 반환
        updated_settings = load_ai_settings_from_db()
        logger.info(f"AI 설정 업데이트 완료: {updated_settings}")
        return updated_settings
    except Exception as e:
        logger.error(f"AI 설정 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- 프롬프트 GET, PUT 엔드포인트 추가 ---
@router.get("/prompts")
async def get_prompts():
    """
    현재 프롬프트 설정을 반환합니다.
    """
    try:
        prompts = load_prompts_from_db()
        return prompts
    except Exception as e:
        logger.error(f"프롬프트 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/prompts")
async def update_prompts(request: PromptsRequest):
    """
    프롬프트 설정을 DB에 업데이트합니다.
    """
    try:
        logger.info(f"프롬프트 업데이트 요청 받음: {request.dict()}")
        save_prompts_to_db(request)
        updated_prompts = load_prompts_from_db()
        logger.info(f"프롬프트 업데이트 완료: {updated_prompts}")
        return updated_prompts
    except Exception as e:
        logger.error(f"프롬프트 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
            "GET /api/v1/admin/prompts - 프롬프트 조회",
            "PUT /api/v1/admin/prompts - 프롬프트 업데이트",
            "GET /api/v1/admin/health - 상태 확인",
            "GET /api/v1/admin/info - API 정보"
        ]
    } 