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
                # GeminiHandler는 GenerativeModel 인스턴스 또는 genai 모듈을 받아 동작하도록 수정됨
                self.gemini_handler = GeminiHandler(genai, 'gemini-1.5-flash')
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
            
            # AI 핸들러의 get_completion 메서드 사용
            if hasattr(handler, 'get_completion'):
                return await handler.get_completion(prompt)
            else:
                logger.error(f"핸들러 {type(handler).__name__}에 get_completion 메서드가 없습니다.")
                raise ValueError(f"AI 핸들러 {type(handler).__name__}가 올바르지 않습니다.")
                
        except Exception as e:
            logger.error(f"AI 응답 생성 실패: {e}")
            raise
    
    async def generate_itinerary_with_master_prompt(self, user_data: Dict[str, Any]) -> str:
        """마스터 프롬프트를 사용한 일정 생성"""
        try:
            # Supabase에서 마스터 프롬프트 가져오기
            # 고정 프롬프트: itinerary_generation
            master_prompt = await supabase_service.get_master_prompt('itinerary_generation')
            
            # 입력 데이터를 JSON 문자열로 변환
            input_data_json = json.dumps(user_data, ensure_ascii=False, indent=2)
            
            # 프롬프트에 실제 데이터 주입
            final_prompt = master_prompt.replace('{input_data}', input_data_json)
            
            logger.info("마스터 프롬프트를 사용하여 일정 생성 시작")
            logger.debug(f"최종 프롬프트 길이: {len(final_prompt)} 문자")
            
            # AI로 응답 생성
            response = await self.generate_response(final_prompt)
            
            # JSON 응답 검증 및 정제
            try:
                # 1차 시도: 원본 그대로 파싱
                json.loads(response)
                logger.info("✅ 일정 생성 완료 - 유효한 JSON 응답")
                return response
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ 1차 JSON 파싱 실패: {e}")
                logger.info("🔧 JSON 정제 시도 중...")
                
                try:
                    # 2차 시도: JSON 정제 후 파싱
                    cleaned_response = self._clean_json_response(response)
                    json.loads(cleaned_response)  # 정제된 응답 검증
                    logger.info("✅ JSON 정제 성공 - 유효한 응답 생성")
                    return cleaned_response
                except (json.JSONDecodeError, ValueError) as clean_error:
                    logger.error(f"❌ JSON 정제도 실패: {clean_error}")
                    logger.error(f"📝 AI 원본 응답 (처음 1000자): {response[:1000]}...")
                    
                    # 최후 수단: 기본 응답 구조 반환
                    fallback_response = {
                        "travel_plan": {
                            "total_days": 1,
                            "daily_start_time": "09:00",
                            "daily_end_time": "22:00",
                            "days": []
                        }
                    }
                    logger.info("🔄 폴백 응답 사용")
                    return json.dumps(fallback_response, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"마스터 프롬프트 일정 생성 실패: {e}")
            raise
    
    def _clean_json_response(self, response: str) -> str:
        """AI 응답에서 JSON 부분만 추출하고 정리 - 강화된 버전"""
        try:
            logger.info(f"🔧 JSON 정제 시작 - 원본 길이: {len(response)}")
            
            # 1단계: Markdown 코드 블록 제거
            if '```json' in response:
                start = response.find('```json') + 7
                end = response.find('```', start)
                if end != -1:
                    response = response[start:end].strip()
                    logger.info("✅ Markdown JSON 블록 추출 완료")
            elif '```' in response:
                start = response.find('```') + 3
                end = response.find('```', start)
                if end != -1:
                    response = response[start:end].strip()
                    logger.info("✅ Markdown 코드 블록 추출 완료")
            
            # 2단계: 첫 번째 { 부터 마지막 } 까지 추출 (중괄호 균형 맞추기)
            start_brace = response.find('{')
            if start_brace == -1:
                raise ValueError("JSON 시작 중괄호를 찾을 수 없습니다")
            
            # 중괄호 균형을 맞춰서 올바른 JSON 끝 지점 찾기
            brace_count = 0
            end_brace = start_brace
            
            for i in range(start_brace, len(response)):
                if response[i] == '{':
                    brace_count += 1
                elif response[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_brace = i
                        break
            
            if brace_count != 0:
                # 균형이 맞지 않으면 마지막 } 사용
                end_brace = response.rfind('}')
                logger.warning("⚠️ 중괄호 균형이 맞지 않음, 마지막 }를 사용")
            
            if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
                cleaned = response[start_brace:end_brace + 1]
                logger.info(f"✅ JSON 추출 완료 - 정제된 길이: {len(cleaned)}")
                
                # 3단계: 기본적인 JSON 구조 검증
                if cleaned.count('{') == 0 or cleaned.count('}') == 0:
                    raise ValueError("유효한 JSON 구조가 아닙니다")
                
                return cleaned.strip()
            else:
                raise ValueError("유효한 JSON 범위를 찾을 수 없습니다")
            
        except Exception as e:
            logger.error(f"❌ JSON 정리 실패: {e}")
            logger.error(f"📝 원본 응답 (처음 500자): {response[:500]}...")
            # 정제 실패 시 원본 반환 (상위에서 다시 에러 처리)
            return response
    
    async def get_master_prompt(self, prompt_type: str = 'itinerary_generation') -> str:
        """마스터 프롬프트 조회: 매핑/폴백 없이 지정 명칭 그대로 사용"""
        return await supabase_service.get_master_prompt(prompt_type)
    
    async def update_master_prompt(self, prompt_type: str, prompt_content: str) -> bool:
        """마스터 프롬프트 업데이트 - 현재는 지원하지 않음 (관리자 전용 기능)"""
        raise NotImplementedError("프롬프트 업데이트는 관리자 인터페이스를 통해서만 가능합니다.")
    
    async def get_prompt_history(self, prompt_type: str):
        """프롬프트 히스토리 조회 - 현재는 지원하지 않음"""
        raise NotImplementedError("프롬프트 히스토리 조회는 현재 지원하지 않습니다.")


# 전역 강화된 AI 서비스 인스턴스
enhanced_ai_service = EnhancedAIService()