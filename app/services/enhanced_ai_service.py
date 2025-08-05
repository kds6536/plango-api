"""
Enhanced AI Service with Supabase Integration
Supabase에서 AI 설정과 프롬프트를 동적으로 관리하는 AI 서비스
"""

import json
import logging
from typing import Dict, Any, Optional
from app.services.supabase_service import supabase_service
from app.services.ai_handlers import OpenAIHandler, GeminiHandler
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EnhancedAIService:
    """Supabase 연동 강화된 AI 서비스"""
    
    def __init__(self):
        """AI 서비스 초기화"""
        self.openai_handler = None
        self.gemini_handler = None
        self.current_settings = None
        self._initialize_handlers()
    
    def _initialize_handlers(self):
        """AI 핸들러 초기화"""
        try:
            import openai
            import google.generativeai as genai
            
            # OpenAI 핸들러
            if settings.OPENAI_API_KEY:
                openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                self.openai_handler = OpenAIHandler(openai_client, "gpt-4")
                logger.info("OpenAI 핸들러 초기화 완료")
            
            # Gemini 핸들러
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                gemini_model = genai.GenerativeModel('gemini-1.5-flash')
                self.gemini_handler = GeminiHandler(gemini_model, 'gemini-1.5-flash')
                logger.info("Gemini 핸들러 초기화 완료")
                
        except Exception as e:
            logger.error(f"AI 핸들러 초기화 실패: {e}")
    
    async def get_current_ai_settings(self) -> Dict[str, Any]:
        """현재 AI 설정 조회"""
        try:
            settings_data = await supabase_service.get_ai_settings()
            self.current_settings = settings_data
            return settings_data
        except Exception as e:
            logger.error(f"AI 설정 조회 실패: {e}")
            return {
                'provider': 'openai',
                'openai_model': 'gpt-4',
                'gemini_model': 'gemini-1.5-flash',
                'temperature': 0.7,
                'max_tokens': 2000
            }
    
    async def update_ai_settings(self, new_settings: Dict[str, Any]) -> bool:
        """AI 설정 업데이트"""
        try:
            success = await supabase_service.update_ai_settings(new_settings)
            if success:
                self.current_settings = new_settings
                logger.info(f"AI 설정 업데이트 완료: {new_settings['provider']}")
            return success
        except Exception as e:
            logger.error(f"AI 설정 업데이트 실패: {e}")
            return False
    
    async def get_active_handler(self):
        """현재 활성화된 AI 핸들러 반환"""
        if not self.current_settings:
            await self.get_current_ai_settings()
        
        provider = self.current_settings.get('provider', 'openai')
        
        if provider == 'gemini' and self.gemini_handler:
            # Gemini 모델 업데이트
            model_name = self.current_settings.get('gemini_model', 'gemini-1.5-flash')
            self.gemini_handler.model_name = model_name
            return self.gemini_handler
        elif provider == 'openai' and self.openai_handler:
            # OpenAI 모델 업데이트
            model_name = self.current_settings.get('openai_model', 'gpt-4')
            self.openai_handler.model_name = model_name
            return self.openai_handler
        else:
            logger.warning(f"요청된 AI 제공자 '{provider}'를 사용할 수 없습니다. OpenAI로 폴백합니다.")
            return self.openai_handler
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """AI 응답 생성"""
        try:
            handler = await self.get_active_handler()
            if not handler:
                raise ValueError("사용 가능한 AI 핸들러가 없습니다.")
            
            # 현재 설정에서 온도와 토큰 수 가져오기
            if not self.current_settings:
                await self.get_current_ai_settings()
            
            temperature = self.current_settings.get('temperature', 0.7)
            max_tokens = self.current_settings.get('max_tokens', 2000)
            
            # AI 핸들러에 따라 다른 방식으로 호출
            if hasattr(handler, 'generate_response'):
                return await handler.generate_response(
                    prompt, 
                    temperature=temperature, 
                    max_tokens=max_tokens,
                    **kwargs
                )
            else:
                # 기존 방식으로 폴백
                return await handler.ask(prompt)
                
        except Exception as e:
            logger.error(f"AI 응답 생성 실패: {e}")
            raise
    
    async def generate_itinerary_with_master_prompt(self, user_data: Dict[str, Any]) -> str:
        """마스터 프롬프트를 사용한 일정 생성"""
        try:
            # Supabase에서 마스터 프롬프트 가져오기
            master_prompt = await supabase_service.get_master_prompt('itinerary_generation')
            
            # 입력 데이터를 JSON 문자열로 변환
            input_data_json = json.dumps(user_data, ensure_ascii=False, indent=2)
            
            # 프롬프트에 실제 데이터 주입
            final_prompt = master_prompt.replace('{input_data}', input_data_json)
            
            logger.info("마스터 프롬프트를 사용하여 일정 생성 시작")
            logger.debug(f"최종 프롬프트 길이: {len(final_prompt)} 문자")
            
            # AI로 응답 생성
            response = await self.generate_response(final_prompt)
            
            # JSON 응답 검증
            try:
                json.loads(response)  # JSON 파싱 테스트
                logger.info("일정 생성 완료 - 유효한 JSON 응답")
                return response
            except json.JSONDecodeError as e:
                logger.error(f"AI가 유효하지 않은 JSON을 반환했습니다: {e}")
                # 간단한 JSON 정리 시도
                cleaned_response = self._clean_json_response(response)
                json.loads(cleaned_response)  # 다시 검증
                return cleaned_response
                
        except Exception as e:
            logger.error(f"마스터 프롬프트 일정 생성 실패: {e}")
            raise
    
    def _clean_json_response(self, response: str) -> str:
        """AI 응답에서 JSON 부분만 추출하고 정리"""
        try:
            # Markdown 코드 블록 제거
            if '```json' in response:
                start = response.find('```json') + 7
                end = response.find('```', start)
                if end != -1:
                    response = response[start:end].strip()
            elif '```' in response:
                start = response.find('```') + 3
                end = response.find('```', start)
                if end != -1:
                    response = response[start:end].strip()
            
            # 첫 번째 { 부터 마지막 } 까지 추출
            start_brace = response.find('{')
            end_brace = response.rfind('}')
            
            if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
                response = response[start_brace:end_brace + 1]
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"JSON 정리 실패: {e}")
            return response
    
    async def get_master_prompt(self, prompt_type: str = 'itinerary_generation') -> str:
        """마스터 프롬프트 조회"""
        return await supabase_service.get_master_prompt(prompt_type)
    
    async def update_master_prompt(self, prompt_type: str, prompt_content: str) -> bool:
        """마스터 프롬프트 업데이트"""
        return await supabase_service.update_master_prompt(prompt_type, prompt_content)
    
    async def get_prompt_history(self, prompt_type: str):
        """프롬프트 히스토리 조회"""
        return await supabase_service.get_prompt_history(prompt_type)


# 전역 강화된 AI 서비스 인스턴스
enhanced_ai_service = EnhancedAIService()