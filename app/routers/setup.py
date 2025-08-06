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


@router.post("/migrate-prompts-table")
async def migrate_prompts_table():
    """prompts 테이블 구조 개선 및 데이터 마이그레이션"""
    try:
        if not supabase_service.is_connected():
            raise HTTPException(status_code=500, detail="Supabase에 연결할 수 없습니다.")
        
        logger.info("prompts 테이블 구조 개선 시작")
        
        # 1. 기존 데이터 백업
        existing_data = supabase_service.client.table('prompts').select('*').execute()
        logger.info(f"기존 prompts 데이터 {len(existing_data.data)}개 백업 완료")
        
        # 2. name 컬럼 추가 (이미 존재할 경우 무시)
        try:
            # name 컬럼 추가
            supabase_service.client.rpc('exec_sql', {
                'sql': 'ALTER TABLE prompts ADD COLUMN IF NOT EXISTS name TEXT;'
            }).execute()
            logger.info("name 컬럼 추가 완료")
        except Exception as e:
            logger.warning(f"name 컬럼 추가 시도 중 오류 (이미 존재할 수 있음): {e}")
        
        # 3. description 컬럼 추가 (이미 존재할 경우 무시)
        try:
            supabase_service.client.rpc('exec_sql', {
                'sql': 'ALTER TABLE prompts ADD COLUMN IF NOT EXISTS description TEXT;'
            }).execute()
            logger.info("description 컬럼 추가 완료")
        except Exception as e:
            logger.warning(f"description 컬럼 추가 시도 중 오류 (이미 존재할 수 있음): {e}")
        
        # 4. 기존 데이터가 있으면 name 값 설정
        if existing_data.data:
            for item in existing_data.data:
                try:
                    # key 값을 기반으로 name 설정
                    key_value = item.get('key', '')
                    name_value = key_value
                    
                    # key-name 매핑
                    if key_value == 'stage1_destinations_prompt':
                        name_value = 'place_recommendation'
                    elif key_value == 'stage3_detailed_itinerary_prompt':
                        name_value = 'itinerary_generation'
                    elif not name_value:
                        # id가 없을 경우 다른 방법으로 고유값 생성
                        row_id = item.get('id')
                        if row_id:
                            name_value = f"prompt_{row_id}"
                        else:
                            name_value = f"prompt_{len(existing_data.data)}"
                    
                    # name과 description 업데이트 (id 조건 사용)
                    if 'id' in item and item['id']:
                        supabase_service.client.table('prompts').update({
                            'name': name_value,
                            'description': f"프롬프트: {name_value}"
                        }).eq('id', item['id']).execute()
                        logger.info(f"기존 프롬프트 업데이트: {name_value} (ID: {item['id']})")
                    else:
                        logger.warning(f"ID가 없는 프롬프트 발견, 건너뜀: {item}")
                        
                except Exception as e:
                    logger.error(f"개별 프롬프트 업데이트 실패: {e}, 데이터: {item}")
                    continue
        
        # 5. 새로운 프롬프트들 추가
        new_prompts = [
            {
                'name': 'place_recommendation',
                'value': '''당신은 여행 전문가입니다. 다음 정보를 바탕으로 {city}에서 방문할 만한 장소들을 추천해주세요.

여행 정보:
- 도시: {city}
- 국가: {country}
- 총 여행 기간: {total_duration}일
- 여행자 수: {travelers_count}명
- 예산: {budget_range}
- 여행 스타일: {travel_style}
- 특별 요청: {special_requests}
{multi_destination_context}

다음 카테고리별로 3-5개씩 추천해주세요:
1. 관광지 (명소, 박물관, 역사적 장소)
2. 음식점 (현지 음식, 맛집)
3. 활동 (체험, 엔터테인먼트)
4. 숙박 (호텔, 게스트하우스)

각 장소는 실제 존재하는 곳이어야 하며, 구글에서 검색 가능한 이름이어야 합니다.

JSON 형식으로 다음과 같이 응답해주세요:
{
  "관광지": ["경복궁", "북촌한옥마을", "남산타워"],
  "음식점": ["명동교자", "광장시장", "이태원 맛집"],
  "활동": ["한강공원", "동대문 쇼핑", "홍대 클럽"],
  "숙박": ["롯데호텔", "명동 게스트하우스", "강남 호텔"]
}''',
                'description': '장소 추천을 위한 AI 프롬프트'
            },
            {
                'name': 'itinerary_generation',
                'value': '''너는 10년 경력의 전문 여행 큐레이터 "플랜고 플래너"야. 너의 전문 분야는 사용자가 선택한 장소들을 바탕으로, 가장 효율적인 동선과 감성적인 스토리를 담아 최고의 여행 일정을 기획하는 것이야.

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
}''',
                'description': '여행 일정 생성을 위한 마스터 프롬프트'
            }
        ]
        
        # 기존에 없는 프롬프트들만 추가
        for prompt in new_prompts:
            try:
                # 같은 name을 가진 프롬프트가 있는지 확인
                existing = supabase_service.client.table('prompts').select('id').eq('name', prompt['name']).execute()
                if not existing.data:
                    supabase_service.client.table('prompts').insert(prompt).execute()
                    logger.info(f"새 프롬프트 추가: {prompt['name']}")
                else:
                    # 기존 프롬프트 업데이트
                    supabase_service.client.table('prompts').update({
                        'value': prompt['value'],
                        'description': prompt['description']
                    }).eq('name', prompt['name']).execute()
                    logger.info(f"기존 프롬프트 업데이트: {prompt['name']}")
            except Exception as e:
                logger.error(f"프롬프트 {prompt['name']} 처리 중 오류: {e}")
        
        return {
            "success": True,
            "message": "prompts 테이블 구조 개선 및 데이터 마이그레이션 완료",
            "backup_count": len(existing_data.data) if existing_data.data else 0
        }
        
    except Exception as e:
        logger.error(f"prompts 테이블 마이그레이션 실패: {e}")
        raise HTTPException(status_code=500, detail=f"테이블 마이그레이션 실패: {str(e)}")