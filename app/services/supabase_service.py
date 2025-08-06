"""
Supabase 연동 서비스
AI 설정 및 프롬프트 관리를 위한 Supabase 연결
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from supabase import create_client, Client
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SupabaseService:
    """Supabase 연동 서비스"""
    
    def __init__(self):
        """Supabase 클라이언트 초기화"""
        try:
            if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
                logger.warning("Supabase 설정이 없습니다. 로컬 파일을 사용합니다.")
                self.client = None
                return
                
            self.client: Client = create_client(
                supabase_url=settings.SUPABASE_URL,
                supabase_key=settings.SUPABASE_KEY
            )
            logger.info("Supabase 클라이언트 초기화 완료")
            
        except Exception as e:
            logger.error(f"Supabase 클라이언트 초기화 실패: {e}")
            self.client = None
    
    def is_connected(self) -> bool:
        """Supabase 연결 상태 확인"""
        return self.client is not None
    
    async def get_ai_settings(self) -> Dict[str, Any]:
        """AI 설정 조회 (기존 settings 테이블만 사용)"""
        try:
            if not self.is_connected():
                return self._get_local_ai_settings()
            
            # 기존 settings 테이블 사용
            response = self.client.table('settings').select('*').execute()
            if response.data:
                settings_dict = {item['key']: item['value'] for item in response.data}
                return {
                    'provider': settings_dict.get('default_provider', 'openai'),
                    'openai_model': settings_dict.get('openai_model_name', 'gpt-4'),
                    'gemini_model': settings_dict.get('gemini_model_name', 'gemini-1.5-flash'),
                    'temperature': 0.7,
                    'max_tokens': 2000
                }
            else:
                logger.warning("AI 설정이 없습니다. 기본값을 사용합니다.")
                return self._get_default_ai_settings()
                
        except Exception as e:
            logger.error(f"AI 설정 조회 실패: {e}")
            return self._get_local_ai_settings()
    
    async def update_ai_settings(self, settings_data: Dict[str, Any]) -> bool:
        """AI 설정 업데이트"""
        try:
            if not self.is_connected():
                return self._update_local_ai_settings(settings_data)
            
            # 기존 settings 테이블 업데이트
            provider = settings_data.get('provider', 'openai')
            openai_model = settings_data.get('openai_model', 'gpt-4')
            gemini_model = settings_data.get('gemini_model', 'gemini-1.5-flash')
            
            updates = [
                {'key': 'default_provider', 'value': provider, 'is_encrypted': False},
                {'key': 'openai_model_name', 'value': openai_model, 'is_encrypted': False},
                {'key': 'gemini_model_name', 'value': gemini_model, 'is_encrypted': False}
            ]
            
            for update in updates:
                self.client.table('settings').upsert(update).execute()
            
            logger.info(f"AI 설정 업데이트 완료: {settings_data}")
            return True
            
        except Exception as e:
            logger.error(f"AI 설정 업데이트 실패: {e}")
            return False
    
    async def get_master_prompt(self, prompt_type: str = 'itinerary_generation') -> str:
        """마스터 프롬프트 조회 (새로운 prompts 테이블 스키마 사용)"""
        try:
            if not self.is_connected():
                return self._get_local_prompt(prompt_type)
            
            # 새로운 스키마: name 컬럼으로 조회
            response = self.client.table('prompts').select('value').eq('name', prompt_type).execute()
            
            if response.data:
                logger.info(f"Supabase에서 프롬프트 조회 성공: {prompt_type}")
                return response.data[0]['value']
            else:
                logger.warning(f"{prompt_type} 프롬프트가 없습니다. 기본값을 사용합니다.")
                return self._get_default_prompt(prompt_type)
                
        except Exception as e:
            logger.error(f"마스터 프롬프트 조회 실패: {e}")
            return self._get_local_prompt(prompt_type)
    
    async def update_master_prompt(self, prompt_type: str, prompt_content: str) -> bool:
        """마스터 프롬프트 업데이트 (새로운 prompts 테이블 스키마 사용)"""
        try:
            if not self.is_connected():
                return self._update_local_prompt(prompt_type, prompt_content)
            
            # 새로운 스키마: name을 기준으로 upsert 사용
            upsert_data = {
                'name': prompt_type,
                'value': prompt_content,
                'description': f"프롬프트: {prompt_type}"
            }
            
            # Supabase upsert 사용 (name이 존재하면 업데이트, 없으면 새로 생성)
            self.client.table('prompts').upsert(upsert_data).execute()
            
            logger.info(f"프롬프트 upsert 완료: {prompt_type}")
            return True
            
        except Exception as e:
            logger.error(f"마스터 프롬프트 업데이트 실패: {e}")
            return False
    
    async def get_prompt_history(self, prompt_type: str = None) -> List[Dict[str, Any]]:
        """프롬프트 히스토리 조회 (새로운 스키마 사용)"""
        try:
            if not self.is_connected():
                return []
            
            if prompt_type:
                # 특정 프롬프트 조회
                response = self.client.table('prompts').select('*').eq('name', prompt_type).execute()
            else:
                # 모든 프롬프트 조회
                response = self.client.table('prompts').select('*').order('created_at', desc=True).execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"프롬프트 히스토리 조회 실패: {e}")
            return []
    
    async def delete_prompt(self, prompt_type: str) -> bool:
        """프롬프트 삭제 (새로운 스키마 사용)"""
        try:
            if not self.is_connected():
                return False
            
            # name을 기준으로 삭제
            self.client.table('prompts').delete().eq('name', prompt_type).execute()
            
            logger.info(f"프롬프트 삭제 완료: {prompt_type}")
            return True
            
        except Exception as e:
            logger.error(f"프롬프트 삭제 실패: {e}")
            return False
    
    async def get_prompt_by_name(self, prompt_name: str) -> Optional[Dict[str, Any]]:
        """이름으로 프롬프트 조회 (새로운 스키마 사용)"""
        try:
            if not self.is_connected():
                return None
            
            response = self.client.table('prompts').select('*').eq('name', prompt_name).execute()
            
            if response.data:
                return response.data[0]
            else:
                return None
                
        except Exception as e:
            logger.error(f"프롬프트 조회 실패: {e}")
            return None
    
    async def list_all_prompts(self) -> List[Dict[str, Any]]:
        """모든 프롬프트 목록 조회 (새로운 스키마 사용)"""
        try:
            if not self.is_connected():
                return []
            
            response = self.client.table('prompts').select('id, name, description, created_at').order('created_at', desc=True).execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"프롬프트 목록 조회 실패: {e}")
            return []
    
    def _get_local_ai_settings(self) -> Dict[str, Any]:
        """로컬 파일에서 AI 설정 조회"""
        try:
            local_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'ai_settings.json')
            if os.path.exists(local_file):
                with open(local_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"로컬 AI 설정 조회 실패: {e}")
        
        return self._get_default_ai_settings()
    
    def _get_default_ai_settings(self) -> Dict[str, Any]:
        """기본 AI 설정 반환"""
        return {
            'provider': 'openai',
            'openai_model': 'gpt-4',
            'gemini_model': 'gemini-1.5-flash',
            'temperature': 0.7,
            'max_tokens': 2000
        }
    
    def _update_local_ai_settings(self, settings_data: Dict[str, Any]) -> bool:
        """로컬 파일에 AI 설정 저장"""
        try:
            local_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'ai_settings.json')
            os.makedirs(os.path.dirname(local_file), exist_ok=True)
            
            with open(local_file, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, ensure_ascii=False, indent=2)
            
            logger.info("로컬 AI 설정 업데이트 완료")
            return True
            
        except Exception as e:
            logger.error(f"로컬 AI 설정 업데이트 실패: {e}")
            return False
    
    def _get_local_prompt(self, prompt_type: str) -> str:
        """로컬 파일에서 프롬프트 조회"""
        try:
            local_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'prompts.json')
            if os.path.exists(local_file):
                with open(local_file, 'r', encoding='utf-8') as f:
                    prompts = json.load(f)
                    return prompts.get(prompt_type, self._get_default_prompt(prompt_type))
        except Exception as e:
            logger.error(f"로컬 프롬프트 조회 실패: {e}")
        
        return self._get_default_prompt(prompt_type)
    
    def _get_default_prompt(self, prompt_type: str) -> str:
        """기본 프롬프트 반환"""
        default_prompts = {
            'itinerary_generation': '''너는 10년 경력의 전문 여행 큐레이터 "플랜고 플래너"야. 너의 전문 분야는 사용자가 선택한 장소들을 바탕으로, 가장 효율적인 동선과 감성적인 스토리를 담아 최고의 여행 일정을 기획하는 것이야.

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
            'place_recommendation': '''당신은 여행 전문가입니다. 다음 정보를 바탕으로 {city}에서 방문할 만한 장소들을 추천해주세요.

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
}'''
        }
        
        return default_prompts.get(prompt_type, "기본 프롬프트가 없습니다.")
    
    def _update_local_prompt(self, prompt_type: str, prompt_content: str) -> bool:
        """로컬 파일에 프롬프트 저장"""
        try:
            local_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'prompts.json')
            os.makedirs(os.path.dirname(local_file), exist_ok=True)
            
            # 기존 프롬프트 로드
            prompts = {}
            if os.path.exists(local_file):
                with open(local_file, 'r', encoding='utf-8') as f:
                    prompts = json.load(f)
            
            # 업데이트
            prompts[prompt_type] = prompt_content
            
            # 저장
            with open(local_file, 'w', encoding='utf-8') as f:
                json.dump(prompts, f, ensure_ascii=False, indent=2)
            
            logger.info(f"로컬 프롬프트 업데이트 완료: {prompt_type}")
            return True
            
        except Exception as e:
            logger.error(f"로컬 프롬프트 업데이트 실패: {e}")
            return False


# 전역 Supabase 서비스 인스턴스
supabase_service = SupabaseService()