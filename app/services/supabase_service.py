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
            
            # 기존 활성 설정 비활성화
            self.client.table('ai_settings').update({'is_active': False}).eq('is_active', True).execute()
            
            # 새 설정 추가
            response = self.client.table('ai_settings').insert({
                'provider': settings_data.get('provider', 'openai'),
                'openai_model': settings_data.get('openai_model', 'gpt-4'),
                'gemini_model': settings_data.get('gemini_model', 'gemini-1.5-flash'),
                'temperature': settings_data.get('temperature', 0.7),
                'max_tokens': settings_data.get('max_tokens', 2000),
                'is_active': True
            }).execute()
            
            logger.info(f"AI 설정 업데이트 완료: {settings_data}")
            return True
            
        except Exception as e:
            logger.error(f"AI 설정 업데이트 실패: {e}")
            return False
    
    async def get_master_prompt(self, prompt_type: str = 'itinerary_generation') -> str:
        """마스터 프롬프트 조회 (기존 prompts 테이블만 사용)"""
        try:
            if not self.is_connected():
                return self._get_local_prompt(prompt_type)
            
            # 기존 prompts 테이블 사용
            key_mapping = {
                'itinerary_generation': 'stage3_detailed_itinerary_prompt',
                'place_recommendation': 'stage1_destinations_prompt',
                'optimization': 'stage3_detailed_itinerary_prompt'
            }
            
            key = key_mapping.get(prompt_type, 'stage3_detailed_itinerary_prompt')
            response = self.client.table('prompts').select('value').eq('key', key).execute()
            
            if response.data:
                return response.data[0]['value']
            else:
                logger.warning(f"활성화된 {prompt_type} 프롬프트가 없습니다. 기본값을 사용합니다.")
                return self._get_default_prompt(prompt_type)
                
        except Exception as e:
            logger.error(f"마스터 프롬프트 조회 실패: {e}")
            return self._get_local_prompt(prompt_type)
    
    async def update_master_prompt(self, prompt_type: str, prompt_content: str) -> bool:
        """마스터 프롬프트 업데이트"""
        try:
            if not self.is_connected():
                return self._update_local_prompt(prompt_type, prompt_content)
            
            # 기존 활성 프롬프트 비활성화
            self.client.table('master_prompts').update({'is_active': False}).eq('prompt_type', prompt_type).eq('is_active', True).execute()
            
            # 새 프롬프트 추가
            response = self.client.table('master_prompts').insert({
                'prompt_type': prompt_type,
                'prompt_content': prompt_content,
                'is_active': True,
                'version': 1  # 버전 관리
            }).execute()
            
            logger.info(f"마스터 프롬프트 업데이트 완료: {prompt_type}")
            return True
            
        except Exception as e:
            logger.error(f"마스터 프롬프트 업데이트 실패: {e}")
            return False
    
    async def get_prompt_history(self, prompt_type: str) -> List[Dict[str, Any]]:
        """프롬프트 히스토리 조회"""
        try:
            if not self.is_connected():
                return []
            
            response = self.client.table('master_prompts').select('*').eq('prompt_type', prompt_type).order('created_at', desc=True).execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"프롬프트 히스토리 조회 실패: {e}")
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
        if prompt_type == 'itinerary_generation':
            return self._get_default_itinerary_prompt()
        return "기본 프롬프트가 설정되지 않았습니다."
    
    def _get_default_itinerary_prompt(self) -> str:
        """기본 일정 생성 프롬프트"""
        return """너는 10년 경력의 전문 여행 큐레이터 "플랜고 플래너"야. 너의 전문 분야는 사용자가 선택한 장소들을 바탕으로, 가장 효율적인 동선과 감성적인 스토리를 담아 최고의 여행 일정을 기획하는 것이야. 너는 단순한 챗봇이 아니라, 프로페셔널 여행 기획 전문가야.

너의 임무는 사용자가 선택한 장소 목록, 여행 기간, 그리고 사전 그룹핑된 정보를 받아, 완벽하게 최적화된 여행 일정을 생성하는 것이다.

**//-- 절대 규칙 --//**

1. **엄격한 JSON 출력:** 너의 답변은 반드시 유효한 JSON 객체여야만 한다. JSON 블록 앞뒤로 어떠한 설명, 인사말, markdown 문법(`json` 등)도 포함해서는 안 된다. 너의 전체 답변은 순수한 JSON 내용 그 자체여야 한다.
2. **논리적인 동선 구성:** 제공된 `사전_그룹` 정보를 중요한 힌트로 사용하되, 가장 효율적이고 논리적인 일일 경로를 만드는 것이 너의 최우선 목표다. 같은 날에는 지리적으로 가까운 장소들을 묶어 이동 시간을 최소화해야 한다.
3. **현실적인 시간 배분:** 각 활동에 필요한 `소요시간_분`을 합리적으로 할당하고, 활동들 사이의 `이동시간_분`을 반드시 포함하여 현실적인 시간표를 만들어야 한다.
4. **모든 장소 포함:** `사용자_선택_장소` 목록에 있는 모든 장소를 반드시 일정 안에 포함시켜야 한다. 단 하나도 누락해서는 안 된다.
5. **감성적인 콘텐츠 제작:** 각 날짜의 `일일_테마`와 각 활동의 `설명` 부분에는 전문 여행 작가처럼 짧고 매력적인 문구를 작성해야 한다. 각 활동(activity)에는 내용과 어울리는 이모지를 하나씩 추가해야 한다.

**//-- 입력 데이터 (이 부분은 백엔드에서 동적으로 채워집니다) --//**

{input_data}

**//-- 필수 JSON 출력 형식 --//**

{
  "여행_제목": "나만의 맞춤 여행",
  "일정": [
    {
      "일차": 1,
      "날짜": "YYYY-MM-DD",
      "일일_테마": "여행의 시작: 새로운 발견의 시간",
      "숙소": {
        "이름": "숙소명"
      },
      "시간표": [
        {
          "시작시간": "09:00",
          "종료시간": "10:00",
          "활동": "활동명 🎯",
          "장소명": "장소명",
          "설명": "활동에 대한 감성적인 설명",
          "소요시간_분": 60,
          "이동시간_분": 0
        }
      ],
      "일일_요약_팁": "하루 여행에 대한 유용한 팁"
    }
  ]
}"""
    
    def _update_local_prompt(self, prompt_type: str, prompt_content: str) -> bool:
        """로컬 파일에 프롬프트 저장"""
        try:
            local_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'prompts.json')
            os.makedirs(os.path.dirname(local_file), exist_ok=True)
            
            # 기존 프롬프트 읽기
            prompts = {}
            if os.path.exists(local_file):
                with open(local_file, 'r', encoding='utf-8') as f:
                    prompts = json.load(f)
            
            # 새 프롬프트 추가
            prompts[prompt_type] = prompt_content
            
            # 파일에 저장
            with open(local_file, 'w', encoding='utf-8') as f:
                json.dump(prompts, f, ensure_ascii=False, indent=2)
            
            logger.info(f"로컬 프롬프트 업데이트 완료: {prompt_type}")
            return True
            
        except Exception as e:
            logger.error(f"로컬 프롬프트 업데이트 실패: {e}")
            return False


# 전역 Supabase 서비스 인스턴스
supabase_service = SupabaseService()