"""
데이터베이스 설정 및 초기화 API
Supabase 스키마 생성 및 초기 데이터 설정
"""

import logging
import os
from fastapi import APIRouter, HTTPException
from app.services.supabase_service import supabase_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/setup", tags=["Setup"])


@router.post("/initialize-database")
async def initialize_database():
    """데이터베이스 스키마 및 초기 데이터 설정"""
    try:
        if not supabase_service.is_connected():
            raise HTTPException(status_code=500, detail="Supabase에 연결할 수 없습니다.")
        
        # SQL 파일 읽기
        sql_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'setup_supabase_schema.sql')
        
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            sql_content = file.read()
        
        # SQL 실행 (여러 구문을 분리해서 실행)
        sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        results = []
        for i, statement in enumerate(sql_statements):
            if statement and not statement.startswith('--'):
                try:
                    result = supabase_service.client.rpc('exec_sql', {'sql': statement}).execute()
                    results.append(f"Statement {i+1}: Success")
                    logger.info(f"SQL 구문 {i+1} 실행 완료")
                except Exception as e:
                    # 테이블이 이미 존재하거나 무해한 에러는 무시
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        results.append(f"Statement {i+1}: Already exists (OK)")
                        logger.info(f"SQL 구문 {i+1}: 이미 존재함 (정상)")
                    else:
                        logger.error(f"SQL 구문 {i+1} 실행 실패: {e}")
                        results.append(f"Statement {i+1}: Error - {str(e)}")
        
        # 직접 테이블 생성 시도 (RPC가 안 되는 경우)
        await create_tables_directly()
        
        return {
            "success": True,
            "message": "데이터베이스 초기화 완료",
            "details": results
        }
        
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        raise HTTPException(status_code=500, detail=f"데이터베이스 초기화 실패: {str(e)}")


async def create_tables_directly():
    """직접 테이블 생성 및 데이터 삽입"""
    try:
        # 1. ai_settings 테이블 데이터 확인/삽입
        try:
            response = supabase_service.client.table('ai_settings').select('*').execute()
            if not response.data:
                # 초기 AI 설정 삽입
                supabase_service.client.table('ai_settings').insert({
                    'provider': 'openai',
                    'openai_model': 'gpt-4',
                    'gemini_model': 'gemini-1.5-flash',
                    'temperature': 0.7,
                    'max_tokens': 2000,
                    'is_active': True
                }).execute()
                logger.info("ai_settings 초기 데이터 삽입 완료")
        except Exception as e:
            logger.warning(f"ai_settings 테이블 처리 실패: {e}")
        
        # 2. master_prompts 테이블 데이터 확인/삽입
        try:
            response = supabase_service.client.table('master_prompts').select('*').eq('prompt_type', 'itinerary_generation').execute()
            if not response.data:
                # 마스터 프롬프트 삽입
                master_prompt = '''너는 10년 경력의 전문 여행 큐레이터 "플랜고 플래너"야. 너의 전문 분야는 사용자가 선택한 장소들을 바탕으로, 가장 효율적인 동선과 감성적인 스토리를 담아 최고의 여행 일정을 기획하는 것이야.

**//-- 절대 규칙 --//**

1. **엄격한 JSON 출력:** 너의 답변은 반드시 유효한 JSON 객체여야만 한다.
2. **논리적인 동선 구성:** 지리적으로 가까운 장소들을 묶어 이동 시간을 최소화해야 한다.
3. **현실적인 시간 배분:** 각 활동에 필요한 시간을 합리적으로 할당해야 한다.
4. **모든 장소 포함:** 사용자가 선택한 모든 장소를 반드시 포함시켜야 한다.
5. **감성적인 콘텐츠:** 전문 여행 작가처럼 매력적인 문구를 작성해야 한다.

**//-- 입력 데이터 --//**
{input_data}

**//-- 필수 JSON 출력 형식 --//**
{
  "여행_제목": "나만의 맞춤 여행",
  "일정": [
    {
      "일차": 1,
      "날짜": "YYYY-MM-DD",
      "일일_테마": "여행의 시작",
      "시간표": [
        {
          "시작시간": "09:00",
          "종료시간": "10:00",
          "활동": "활동명 🎯",
          "장소명": "장소명",
          "설명": "활동 설명",
          "소요시간_분": 60,
          "이동시간_분": 0
        }
      ]
    }
  ]
}'''
                
                supabase_service.client.table('master_prompts').insert({
                    'prompt_type': 'itinerary_generation',
                    'prompt_content': master_prompt,
                    'version': 1,
                    'is_active': True
                }).execute()
                logger.info("master_prompts 초기 데이터 삽입 완료")
        except Exception as e:
            logger.warning(f"master_prompts 테이블 처리 실패: {e}")
        
        # 3. 호환성을 위한 기존 테이블 데이터
        try:
            # settings 테이블
            settings_data = [
                {'key': 'default_provider', 'value': 'openai', 'is_encrypted': False},
                {'key': 'openai_model_name', 'value': 'gpt-4', 'is_encrypted': False},
                {'key': 'gemini_model_name', 'value': 'gemini-1.5-flash', 'is_encrypted': False}
            ]
            
            for setting in settings_data:
                try:
                    supabase_service.client.table('settings').upsert(setting).execute()
                except:
                    pass  # 이미 존재하는 경우 무시
            
            logger.info("settings 테이블 데이터 확인/삽입 완료")
        except Exception as e:
            logger.warning(f"settings 테이블 처리 실패: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"직접 테이블 생성 실패: {e}")
        return False


@router.get("/status")
async def get_setup_status():
    """데이터베이스 설정 상태 확인"""
    try:
        if not supabase_service.is_connected():
            return {
                "success": False,
                "message": "Supabase 연결 실패",
                "tables": {}
            }
        
        tables_status = {}
        
        # 각 테이블 상태 확인
        table_names = ['ai_settings', 'master_prompts', 'settings', 'prompts']
        
        for table_name in table_names:
            try:
                response = supabase_service.client.table(table_name).select('*').limit(1).execute()
                tables_status[table_name] = {
                    "exists": True,
                    "has_data": len(response.data) > 0,
                    "count": len(response.data) if response.data else 0
                }
            except Exception as e:
                tables_status[table_name] = {
                    "exists": False,
                    "error": str(e)
                }
        
        return {
            "success": True,
            "message": "데이터베이스 상태 확인 완료",
            "supabase_connected": True,
            "tables": tables_status
        }
        
    except Exception as e:
        logger.error(f"설정 상태 확인 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-data")
async def reset_initial_data():
    """초기 데이터 재설정"""
    try:
        success = await create_tables_directly()
        
        if success:
            return {
                "success": True,
                "message": "초기 데이터 재설정 완료"
            }
        else:
            raise HTTPException(status_code=500, detail="초기 데이터 재설정 실패")
            
    except Exception as e:
        logger.error(f"초기 데이터 재설정 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))