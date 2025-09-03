"""
Enhanced AI Service with Supabase Integration
Supabase에서 AI 설정과 프롬프트를 동적으로 관리하는 AI 서비스
"""

import json
import logging
import traceback
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
            logger.info("🤖 [GENERATE_START] AI 응답 생성 시작")
            
            handler = await self.get_active_handler()
            if not handler:
                logger.error("❌ [HANDLER_ERROR] 사용 가능한 AI 핸들러가 없습니다")
                raise ValueError("사용 가능한 AI 핸들러가 없습니다.")
            
            logger.info(f"🤖 [HANDLER_INFO] 활성 핸들러: {type(handler).__name__}")
            
            # 현재 설정에서 온도와 토큰 수 가져오기
            if not self.current_settings:
                await self.get_current_ai_settings()
            
            temperature = self.current_settings.get('temperature', 0.7)
            max_tokens = self.current_settings.get('max_tokens', 2000)
            
            logger.info(f"🤖 [AI_SETTINGS] 온도: {temperature}, 최대 토큰: {max_tokens}")
            logger.info(f"🤖 [PROMPT_LENGTH] 프롬프트 길이: {len(prompt)}")
            
            # AI 핸들러의 get_completion 메서드 사용
            if hasattr(handler, 'get_completion'):
                logger.info("🤖 [AI_CALL] AI 핸들러 호출 시작")
                response = await handler.get_completion(prompt)
                logger.info(f"🤖 [AI_RESPONSE_RECEIVED] AI 응답 수신 완료 (길이: {len(response) if response else 0})")
                
                if not response:
                    logger.error("❌ [EMPTY_AI_RESPONSE] AI가 빈 응답을 반환했습니다")
                    raise ValueError("AI가 빈 응답을 반환했습니다")
                
                return response
            else:
                logger.error(f"❌ [METHOD_ERROR] 핸들러 {type(handler).__name__}에 get_completion 메서드가 없습니다")
                raise ValueError(f"AI 핸들러 {type(handler).__name__}가 올바르지 않습니다.")
                
        except Exception as e:
            logger.error(f"❌ [GENERATE_ERROR] AI 응답 생성 실패: {e}")
            logger.error(f"📊 [ERROR_TRACEBACK] {traceback.format_exc()}")
            raise
    
    async def generate_itinerary_with_master_prompt(self, user_data: Dict[str, Any]) -> str:
        """마스터 프롬프트를 사용한 일정 생성"""
        try:
            logger.info("🚀 [ITINERARY_START] 마스터 프롬프트를 사용하여 일정 생성 시작")
            logger.info(f"📊 [INPUT_DATA] 입력 데이터: {user_data}")
            
            # Supabase에서 마스터 프롬프트 가져오기
            # 고정 프롬프트: itinerary_generation
            logger.info("📜 [PROMPT_FETCH] Supabase에서 마스터 프롬프트 가져오기 시작")
            master_prompt = await supabase_service.get_master_prompt('itinerary_generation')
            logger.info(f"📜 [PROMPT_FETCHED] 마스터 프롬프트 가져오기 완료 (길이: {len(master_prompt)})")
            
            # 입력 데이터를 JSON 문자열로 변환
            input_data_json = json.dumps(user_data, ensure_ascii=False, indent=2)
            logger.info(f"📊 [JSON_INPUT] 입력 데이터 JSON 변환 완료 (길이: {len(input_data_json)})")
            
            # 프롬프트에 실제 데이터 주입
            final_prompt = master_prompt.replace('{input_data}', input_data_json)
            
            logger.info(f"📜 [FINAL_PROMPT_STEP_3] 3단계 AI에게 보낼 최종 프롬프트 (길이: {len(final_prompt)}):")
            logger.info(f"📜 [PROMPT_CONTENT] {final_prompt}")
            
            # AI로 응답 생성
            logger.info("🤖 [AI_CALLING] AI 호출 시작...")
            response = await self.generate_response(final_prompt)
            logger.info(f"🤖 [AI_RESPONSE] AI 응답 수신 완료 (길이: {len(response) if response else 0})")
            
            # ===== 🔍 AI 원본 응답 상세 로깅 (TypeError 디버깅용) =====
            logger.info("=" * 80)
            logger.info("🤖 [RAW_RESPONSE_STEP_3] 3단계 AI 원본 응답:")
            logger.info(f"📊 [RESPONSE_TYPE] 응답 타입: {type(response)}")
            logger.info(f"📊 [RESPONSE_LENGTH] 응답 길이: {len(response) if response else 0}")
            logger.info("📝 [RESPONSE_CONTENT] 응답 내용:")
            logger.info(response)
            logger.info("=" * 80)
            
            # 🚨 [긴급 디버깅] AI 응답의 첫 500자와 마지막 500자 별도 로깅
            if response and len(response) > 1000:
                logger.info(f"🔍 [RESPONSE_HEAD] 응답 시작 부분 (500자):\n{response[:500]}")
                logger.info(f"🔍 [RESPONSE_TAIL] 응답 끝 부분 (500자):\n{response[-500:]}")
            
            # 🚨 [긴급 디버깅] JSON 구조 힌트 찾기
            if response:
                if '"travel_plan"' in response:
                    logger.info("✅ [STRUCTURE_HINT] 응답에 'travel_plan' 키 발견")
                if '"days"' in response:
                    logger.info("✅ [STRUCTURE_HINT] 응답에 'days' 키 발견")
                if '"itinerary"' in response:
                    logger.info("✅ [STRUCTURE_HINT] 응답에 'itinerary' 키 발견")
                if '"daily_plans"' in response:
                    logger.info("✅ [STRUCTURE_HINT] 응답에 'daily_plans' 키 발견")
            
            if not response or not response.strip():
                logger.error("❌ [EMPTY_RESPONSE] AI 응답이 비어있습니다")
                raise ValueError("AI 응답이 비어있습니다")
            
            # JSON 응답 검증 및 정제 - 간단하고 확실한 방법
            logger.info("🔧 [JSON_PARSING] JSON 파싱 시작")
            
            # 즉시 강력한 정제 적용
            cleaned_response = self._extract_json_only(response)
            logger.info(f"🔧 [CLEANED_JSON] 정제된 JSON (길이: {len(cleaned_response)}): {cleaned_response}")
            
            try:
                # 정제된 응답 파싱 시도
                parsed_json = json.loads(cleaned_response)
                logger.info(f"✅ [PARSED_SUCCESS] JSON 파싱 성공")
                logger.info(f"📊 [PARSED_DATA_TYPE] 파싱된 데이터 타입: {type(parsed_json)}")
                
                # 🚨 [핵심 수정] 복잡한 자동 수정 로직 제거, 직접적인 데이터 추출
                logger.info(f"🔍 [DIRECT_EXTRACTION] 직접적인 데이터 추출 시작")
                logger.info(f"📊 [PARSED_KEYS] 파싱된 최상위 키들: {list(parsed_json.keys())}")
                
                # 1. 기본 타입 검증
                if not isinstance(parsed_json, dict):
                    logger.error(f"❌ [INVALID_TYPE] AI 응답이 딕셔너리가 아닙니다: {type(parsed_json)}")
                    raise ValueError(f"AI 응답 형식 오류: {type(parsed_json)}")
                
                # 2. 직접적인 데이터 추출 - 가능한 모든 키 패턴 확인
                travel_plan_data = None
                
                # 우선순위 순서로 키 확인
                possible_keys = [
                    'travel_plan',      # 표준 키
                    'optimized_plan',   # AI가 사용할 가능성이 높은 키
                    'itinerary',        # 대안 키
                    'plan',             # 대안 키
                    'schedule',         # 대안 키
                    'days'              # 직접 배열인 경우
                ]
                
                for key in possible_keys:
                    if key in parsed_json:
                        travel_plan_data = parsed_json[key]
                        logger.info(f"✅ [FOUND_DATA] '{key}' 키에서 데이터 발견")
                        break
                
                # 3. 데이터 유효성 검증
                if travel_plan_data is None:
                    logger.error(f"❌ [NO_VALID_DATA] 유효한 여행 계획 데이터를 찾을 수 없습니다. 사용 가능한 키: {list(parsed_json.keys())}")
                    raise ValueError("AI 응답에서 여행 계획 데이터를 찾을 수 없습니다")
                
                # 4. 데이터 구조 정규화
                if isinstance(travel_plan_data, dict):
                    # 딕셔너리인 경우 - daily_plans 또는 days 키 확인
                    if 'daily_plans' in travel_plan_data:
                        logger.info("✅ [FOUND_DAILY_PLANS] daily_plans 키 발견")
                        final_data = travel_plan_data
                    elif 'days' in travel_plan_data:
                        logger.info("✅ [FOUND_DAYS] days 키 발견, daily_plans로 변환")
                        final_data = travel_plan_data.copy()
                        final_data['daily_plans'] = final_data.pop('days')
                    else:
                        logger.warning("⚠️ [NO_DAILY_PLANS] daily_plans나 days 키가 없음, 전체 데이터를 daily_plans로 사용")
                        final_data = {
                            'title': '맞춤형 여행 일정',
                            'concept': 'AI가 생성한 최적화된 여행 계획',
                            'daily_plans': [travel_plan_data] if travel_plan_data else []
                        }
                elif isinstance(travel_plan_data, list):
                    # 배열인 경우 - 직접 daily_plans로 사용
                    logger.info("✅ [ARRAY_DATA] 배열 데이터를 daily_plans로 사용")
                    final_data = {
                        'title': '맞춤형 여행 일정',
                        'concept': 'AI가 생성한 최적화된 여행 계획',
                        'daily_plans': travel_plan_data
                    }
                else:
                    logger.error(f"❌ [INVALID_DATA_TYPE] 예상치 못한 데이터 타입: {type(travel_plan_data)}")
                    raise ValueError(f"여행 계획 데이터 타입 오류: {type(travel_plan_data)}")
                
                # 5. 최종 검증
                daily_plans = final_data.get('daily_plans', [])
                if not isinstance(daily_plans, list):
                    logger.error(f"❌ [INVALID_DAILY_PLANS] daily_plans가 배열이 아닙니다: {type(daily_plans)}")
                    raise ValueError("daily_plans가 배열 형식이 아닙니다")
                
                logger.info(f"✅ [EXTRACTION_SUCCESS] 데이터 추출 완료: daily_plans 길이 = {len(daily_plans)}")
                
                # 최종 결과를 parsed_json에 할당 (기존 코드와의 호환성)
                parsed_json = {'travel_plan': final_data}
                
                # 6. 최종 JSON 반환
                final_response = json.dumps(parsed_json, ensure_ascii=False, indent=2)
                logger.info(f"📊 [FINAL_JSON] 최종 JSON 길이: {len(final_response)}")
                logger.info(f"✅ [PROCESSING_COMPLETE] AI 응답 처리 완료")
                return final_response
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ [JSON_ERROR] JSON 파싱 최종 실패: {e}")
                logger.error(f"📝 [CLEANED_RESPONSE] 정제된 응답: {cleaned_response}")
                logger.error(f"📝 [ORIGINAL_RESPONSE] AI 원본 응답: {response}")
                
                # 최후 수단: 기본 응답 구조 반환
                fallback_response = {
                    "travel_plan": {
                        "total_days": 1,
                        "daily_start_time": "09:00",
                        "daily_end_time": "22:00",
                        "days": []
                    }
                }
                logger.info("🔄 [FALLBACK] 폴백 응답 사용")
                return json.dumps(fallback_response, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"❌ [ITINERARY_ERROR] 마스터 프롬프트 일정 생성 실패: {e}")
            logger.error(f"📊 [ERROR_TRACEBACK] {traceback.format_exc()}")
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
    
    def _ultra_clean_json(self, response: str) -> str:
        """최강 JSON 정제 - 모든 방법 동원"""
        try:
            logger.info("🔧 강화 JSON 정제 시작")
            
            # 1. 모든 종류의 코드 블록 제거
            import re
            
            # ```json ... ``` 패턴 추출
            json_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            match = re.search(json_block_pattern, response, re.DOTALL)
            if match:
                response = match.group(1)
                logger.info("✅ 코드 블록에서 JSON 추출")
            
            # 2. 첫 번째 { 찾기
            start = -1
            for i, char in enumerate(response):
                if char == '{':
                    start = i
                    break
            
            if start == -1:
                raise ValueError("JSON 시작점을 찾을 수 없음")
            
            # 3. 균형 맞춘 } 찾기
            count = 0
            end = -1
            in_string = False
            escape_next = False
            
            for i in range(start, len(response)):
                char = response[i]
                
                if escape_next:
                    escape_next = False
                    continue
                    
                if char == '\\':
                    escape_next = True
                    continue
                    
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                    
                if not in_string:
                    if char == '{':
                        count += 1
                    elif char == '}':
                        count -= 1
                        if count == 0:
                            end = i
                            break
            
            if end == -1:
                raise ValueError("JSON 끝점을 찾을 수 없음")
            
            result = response[start:end + 1]
            logger.info(f"✅ 강화 정제 완료 - 길이: {len(result)}")
            return result
            
        except Exception as e:
            logger.error(f"❌ 강화 정제 실패: {e}")
            raise
    
    def _extract_json_only(self, response: str) -> str:
        """가장 간단하고 확실한 JSON 추출 방법"""
        try:
            logger.info("🔧 [EXTRACT_START] 간단 JSON 추출 시작")
            logger.info(f"🔧 [EXTRACT_INPUT] 입력 응답 길이: {len(response)}")
            logger.info(f"🔧 [EXTRACT_PREVIEW] 응답 미리보기 (처음 200자): {response[:200]}...")
            
            # 1. 첫 번째 { 찾기
            start = response.find('{')
            logger.info(f"🔧 [EXTRACT_START_POS] 시작 위치: {start}")
            if start == -1:
                logger.error("❌ [EXTRACT_ERROR] JSON 시작점 없음")
                raise ValueError("JSON 시작점 없음")
            
            # 2. 마지막 } 찾기 (가장 간단한 방법)
            end = response.rfind('}')
            logger.info(f"🔧 [EXTRACT_END_POS] 끝 위치: {end}")
            if end == -1 or end <= start:
                logger.error("❌ [EXTRACT_ERROR] JSON 끝점 없음")
                raise ValueError("JSON 끝점 없음")
            
            # 3. 추출
            result = response[start:end + 1]
            
            logger.info(f"✅ [EXTRACT_SUCCESS] 간단 JSON 추출 완료 - 길이: {len(result)}")
            logger.info(f"🔧 [EXTRACT_RESULT] 추출된 JSON 미리보기 (처음 200자): {result[:200]}...")
            return result
            
        except Exception as e:
            logger.error(f"❌ [EXTRACT_ERROR] 간단 JSON 추출 실패: {e}")
            logger.error(f"🔧 [EXTRACT_FALLBACK] 원본 응답 반환")
            # 실패 시 원본 반환
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