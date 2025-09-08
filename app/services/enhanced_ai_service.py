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
        logger.info("🔍 [GET_AI_SETTINGS] AI 설정 조회 시작")
        print("🔍 [GET_AI_SETTINGS] AI 설정 조회 시작")
        
        try:
            logger.info("📊 [SUPABASE_CALL] supabase_service.get_ai_settings() 호출 시작")
            print("📊 [SUPABASE_CALL] supabase_service.get_ai_settings() 호출 시작")
            
            # Supabase 서비스 상태 확인
            logger.info(f"📊 [SUPABASE_STATUS] supabase_service 존재: {supabase_service is not None}")
            print(f"📊 [SUPABASE_STATUS] supabase_service 존재: {supabase_service is not None}")
            
            if hasattr(supabase_service, 'get_ai_settings'):
                logger.info("✅ [METHOD_EXISTS] get_ai_settings 메서드 존재 확인")
                print("✅ [METHOD_EXISTS] get_ai_settings 메서드 존재 확인")
            else:
                logger.error("❌ [METHOD_MISSING] get_ai_settings 메서드가 존재하지 않습니다")
                print("❌ [METHOD_MISSING] get_ai_settings 메서드가 존재하지 않습니다")
                raise AttributeError("get_ai_settings 메서드가 존재하지 않음")
            
            logger.info("🚀 [ACTUAL_SUPABASE_CALL] 실제 Supabase 호출 시작")
            print("🚀 [ACTUAL_SUPABASE_CALL] 실제 Supabase 호출 시작")
            
            settings_data = await supabase_service.get_ai_settings()
            
            logger.info("✅ [SUPABASE_SUCCESS] Supabase AI 설정 조회 성공")
            logger.info(f"📊 [SETTINGS_DATA] 조회된 설정: {settings_data}")
            print(f"✅ [SUPABASE_SUCCESS] Supabase AI 설정 조회 성공: {settings_data}")
            
            self.current_settings = settings_data
            return settings_data
            
        except Exception as e:
            logger.error(f"❌ [AI_SETTINGS_ERROR] AI 설정 조회 실패: {e}")
            logger.error(f"📊 [ERROR_TYPE] 에러 타입: {type(e).__name__}")
            logger.error(f"📊 [ERROR_MSG] 에러 메시지: {str(e)}")
            logger.error(f"📊 [ERROR_TRACEBACK] 상세 트레이스백:", exc_info=True)
            print(f"❌ [AI_SETTINGS_ERROR] AI 설정 조회 실패: {e}")
            
            logger.info("🔄 [DEFAULT_SETTINGS] 기본 설정 반환")
            print("🔄 [DEFAULT_SETTINGS] 기본 설정 반환")
            
            default_settings = {
                'provider': 'openai',
                'openai_model': 'gpt-4',
                'gemini_model': 'gemini-1.5-flash',
                'temperature': 0.7,
                'max_tokens': 2000
            }
            
            self.current_settings = default_settings
            return default_settings
    
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
        logger.info("🔍 [GET_ACTIVE_HANDLER] Enhanced AI Service - get_active_handler 시작")
        print("🔍 [GET_ACTIVE_HANDLER] Enhanced AI Service - get_active_handler 시작")
        
        try:
            logger.info(f"📊 [CURRENT_SETTINGS_CHECK] current_settings 상태: {self.current_settings is not None}")
            print(f"📊 [CURRENT_SETTINGS_CHECK] current_settings 상태: {self.current_settings is not None}")
            
            if not self.current_settings:
                logger.info("🔄 [SETTINGS_FETCH] AI 설정을 가져오는 중...")
                print("🔄 [SETTINGS_FETCH] AI 설정을 가져오는 중...")
                
                try:
                    await self.get_current_ai_settings()
                    logger.info("✅ [SETTINGS_FETCH_SUCCESS] AI 설정 가져오기 성공")
                    print("✅ [SETTINGS_FETCH_SUCCESS] AI 설정 가져오기 성공")
                except Exception as settings_error:
                    logger.error(f"❌ [SETTINGS_FETCH_ERROR] AI 설정 가져오기 실패: {settings_error}")
                    logger.error(f"📊 [SETTINGS_ERROR_TYPE] 에러 타입: {type(settings_error).__name__}")
                    logger.error(f"📊 [SETTINGS_ERROR_MSG] 에러 메시지: {str(settings_error)}")
                    print(f"❌ [SETTINGS_FETCH_ERROR] AI 설정 가져오기 실패: {settings_error}")
                    
                    # 설정 가져오기 실패 시 기본값 사용
                    logger.info("🔄 [DEFAULT_SETTINGS] 기본 설정 사용")
                    print("🔄 [DEFAULT_SETTINGS] 기본 설정 사용")
                    self.current_settings = {
                        'provider': 'openai',
                        'openai_model': 'gpt-4',
                        'gemini_model': 'gemini-1.5-flash',
                        'temperature': 0.7,
                        'max_tokens': 2000
                    }
            
            provider = self.current_settings.get('provider', 'openai')
            logger.info(f"📊 [PROVIDER_SELECTED] 선택된 AI 제공자: {provider}")
            print(f"📊 [PROVIDER_SELECTED] 선택된 AI 제공자: {provider}")
            
            # 핸들러 상태 확인
            logger.info(f"📊 [HANDLER_STATUS] OpenAI 핸들러 존재: {self.openai_handler is not None}")
            logger.info(f"📊 [HANDLER_STATUS] Gemini 핸들러 존재: {self.gemini_handler is not None}")
            print(f"📊 [HANDLER_STATUS] OpenAI: {self.openai_handler is not None}, Gemini: {self.gemini_handler is not None}")
            
            if provider == 'gemini' and self.gemini_handler:
                logger.info("🔄 [GEMINI_SELECTED] Gemini 핸들러 선택")
                print("🔄 [GEMINI_SELECTED] Gemini 핸들러 선택")
                
                # Gemini 모델 업데이트
                model_name = self.current_settings.get('gemini_model', 'gemini-1.5-flash')
                self.gemini_handler.model_name = model_name
                logger.info(f"📊 [GEMINI_MODEL] 모델명: {model_name}")
                
                logger.info("✅ [GEMINI_READY] Gemini 핸들러 준비 완료")
                print("✅ [GEMINI_READY] Gemini 핸들러 준비 완료")
                return self.gemini_handler
                
            elif provider == 'openai' and self.openai_handler:
                logger.info("🔄 [OPENAI_SELECTED] OpenAI 핸들러 선택")
                print("🔄 [OPENAI_SELECTED] OpenAI 핸들러 선택")
                
                # OpenAI 모델 업데이트
                model_name = self.current_settings.get('openai_model', 'gpt-4')
                self.openai_handler.model_name = model_name
                logger.info(f"📊 [OPENAI_MODEL] 모델명: {model_name}")
                
                logger.info("✅ [OPENAI_READY] OpenAI 핸들러 준비 완료")
                print("✅ [OPENAI_READY] OpenAI 핸들러 준비 완료")
                return self.openai_handler
                
            else:
                logger.warning(f"⚠️ [FALLBACK_WARNING] 요청된 AI 제공자 '{provider}'를 사용할 수 없습니다")
                logger.warning(f"📊 [FALLBACK_REASON] OpenAI 핸들러: {self.openai_handler is not None}, Gemini 핸들러: {self.gemini_handler is not None}")
                print(f"⚠️ [FALLBACK_WARNING] 요청된 AI 제공자 '{provider}'를 사용할 수 없습니다")
                
                if self.openai_handler:
                    logger.info("🔄 [FALLBACK_OPENAI] OpenAI로 폴백")
                    print("🔄 [FALLBACK_OPENAI] OpenAI로 폴백")
                    return self.openai_handler
                elif self.gemini_handler:
                    logger.info("🔄 [FALLBACK_GEMINI] Gemini로 폴백")
                    print("🔄 [FALLBACK_GEMINI] Gemini로 폴백")
                    return self.gemini_handler
                else:
                    logger.error("❌ [NO_HANDLERS] 사용 가능한 AI 핸들러가 없습니다")
                    print("❌ [NO_HANDLERS] 사용 가능한 AI 핸들러가 없습니다")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ [GET_ACTIVE_HANDLER_ERROR] get_active_handler 실패: {e}")
            logger.error(f"📊 [ERROR_TYPE] 에러 타입: {type(e).__name__}")
            logger.error(f"📊 [ERROR_MSG] 에러 메시지: {str(e)}")
            logger.error(f"📊 [ERROR_TRACEBACK] 상세 트레이스백:", exc_info=True)
            print(f"❌ [GET_ACTIVE_HANDLER_ERROR] get_active_handler 실패: {e}")
            
            # 에러 발생 시 기본 핸들러 반환 시도
            if self.openai_handler:
                logger.info("🔄 [ERROR_FALLBACK_OPENAI] 에러 발생으로 OpenAI 핸들러 반환")
                print("🔄 [ERROR_FALLBACK_OPENAI] 에러 발생으로 OpenAI 핸들러 반환")
                return self.openai_handler
            elif self.gemini_handler:
                logger.info("🔄 [ERROR_FALLBACK_GEMINI] 에러 발생으로 Gemini 핸들러 반환")
                print("🔄 [ERROR_FALLBACK_GEMINI] 에러 발생으로 Gemini 핸들러 반환")
                return self.gemini_handler
            else:
                logger.error("❌ [TOTAL_FAILURE] 모든 핸들러 사용 불가")
                print("❌ [TOTAL_FAILURE] 모든 핸들러 사용 불가")
                return None
    
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
            logger.info("🚀 [ENHANCED_AI_START] Enhanced AI Service - 마스터 프롬프트 일정 생성 시작")
            logger.info(f"📊 [INPUT_DATA] 입력 데이터: {user_data}")
            
            # Supabase에서 마스터 프롬프트 가져오기
            logger.info("📜 [PROMPT_FETCH] Supabase에서 마스터 프롬프트 가져오기 시작")
            master_prompt = await supabase_service.get_master_prompt('itinerary_generation')
            logger.info(f"📜 [PROMPT_FETCHED] 마스터 프롬프트 가져오기 완료 (길이: {len(master_prompt)})")
            
            # 🚨 마스터 프롬프트도 로깅 (디버깅용)
            logger.info("=" * 100)
            logger.info("🚨🚨🚨 [MASTER_PROMPT_DEBUG] Supabase에서 가져온 마스터 프롬프트:")
            logger.info("=" * 100)
            logger.info(master_prompt)
            logger.info("=" * 100)
            logger.info("🚨🚨🚨 [MASTER_PROMPT_DEBUG_END] 마스터 프롬프트 끝")
            logger.info("=" * 100)
            
            # ===== 🚨 [핵심 추가] 입력 데이터 JSON 변환 과정 상세 디버깅 =====
            logger.info("🧪 [JSON_CONVERSION_START] 입력 데이터 JSON 변환 시작")
            print("🧪 [JSON_CONVERSION_START] 입력 데이터 JSON 변환 시작")
            
            # 입력 데이터 타입 및 구조 분석
            logger.info(f"📊 [USER_DATA_TYPE] user_data 타입: {type(user_data)}")
            logger.info(f"📊 [USER_DATA_KEYS] user_data 키들: {list(user_data.keys()) if isinstance(user_data, dict) else 'Not a dict'}")
            print(f"📊 [USER_DATA_TYPE] user_data 타입: {type(user_data)}")
            
            # 각 키별 데이터 타입 확인
            if isinstance(user_data, dict):
                for key, value in user_data.items():
                    logger.info(f"📊 [KEY_ANALYSIS] '{key}': 타입={type(value)}, 길이={len(value) if hasattr(value, '__len__') else 'N/A'}")
                    print(f"📊 [KEY_ANALYSIS] '{key}': 타입={type(value)}")
                    
                    # places 데이터 특별 분석
                    if key == 'places' and isinstance(value, list) and len(value) > 0:
                        logger.info(f"🔍 [PLACES_ANALYSIS] places 배열 첫 번째 요소 타입: {type(value[0])}")
                        print(f"🔍 [PLACES_ANALYSIS] places 배열 첫 번째 요소 타입: {type(value[0])}")
                        
                        # 첫 번째 place 객체 상세 분석
                        first_place = value[0]
                        if hasattr(first_place, '__dict__'):
                            logger.info(f"🔍 [FIRST_PLACE_ATTRS] 첫 번째 place 속성들: {list(first_place.__dict__.keys())}")
                            print(f"🔍 [FIRST_PLACE_ATTRS] 첫 번째 place 속성들: {list(first_place.__dict__.keys())}")
                        elif isinstance(first_place, dict):
                            logger.info(f"🔍 [FIRST_PLACE_KEYS] 첫 번째 place 키들: {list(first_place.keys())}")
                            print(f"🔍 [FIRST_PLACE_KEYS] 첫 번째 place 키들: {list(first_place.keys())}")
                        
                        # 개별 place 객체 JSON 변환 테스트
                        for i, place in enumerate(value[:3]):  # 처음 3개만 테스트
                            try:
                                logger.info(f"🧪 [PLACE_JSON_TEST_{i+1}] place {i+1} JSON 변환 테스트")
                                print(f"🧪 [PLACE_JSON_TEST_{i+1}] place {i+1} JSON 변환 테스트")
                                
                                # PlaceData 객체를 dict로 변환
                                if hasattr(place, 'dict'):
                                    place_dict = place.dict()
                                    logger.info(f"✅ [PLACE_DICT_{i+1}] place.dict() 성공")
                                elif hasattr(place, '__dict__'):
                                    place_dict = place.__dict__
                                    logger.info(f"✅ [PLACE_DICT_{i+1}] place.__dict__ 사용")
                                else:
                                    place_dict = dict(place) if hasattr(place, 'keys') else place
                                    logger.info(f"✅ [PLACE_DICT_{i+1}] dict() 변환 사용")
                                
                                # JSON 직렬화 테스트
                                place_json = json.dumps(place_dict, ensure_ascii=False)
                                logger.info(f"✅ [PLACE_JSON_SUCCESS_{i+1}] place {i+1} JSON 변환 성공 (길이: {len(place_json)})")
                                print(f"✅ [PLACE_JSON_SUCCESS_{i+1}] place {i+1} JSON 변환 성공")
                                
                            except Exception as place_json_error:
                                logger.error(f"❌ [PLACE_JSON_FAIL_{i+1}] place {i+1} JSON 변환 실패: {place_json_error}")
                                logger.error(f"📊 [PLACE_ERROR_TYPE_{i+1}] 에러 타입: {type(place_json_error).__name__}")
                                logger.error(f"📊 [PLACE_ERROR_MSG_{i+1}] 에러 메시지: {str(place_json_error)}")
                                logger.error(f"📊 [PLACE_ERROR_TRACEBACK_{i+1}]", exc_info=True)
                                print(f"❌ [PLACE_JSON_FAIL_{i+1}] place {i+1} JSON 변환 실패: {place_json_error}")
                                
                                # 실패한 객체의 상세 정보
                                logger.error(f"📊 [FAILED_PLACE_{i+1}] 실패한 place 타입: {type(place)}")
                                logger.error(f"📊 [FAILED_PLACE_{i+1}] 실패한 place 내용: {place}")
                                if hasattr(place, '__dict__'):
                                    logger.error(f"📊 [FAILED_PLACE_{i+1}] __dict__ 내용: {place.__dict__}")
                                
                                # 즉시 폴백 처리
                                logger.info("🔄 [PLACE_JSON_FAIL_IMMEDIATE_FALLBACK] place JSON 변환 실패로 즉시 폴백")
                                print("🔄 [PLACE_JSON_FAIL_IMMEDIATE_FALLBACK] place JSON 변환 실패로 즉시 폴백")
                                raise ValueError(f"Place 객체 JSON 변환 실패: {place_json_error}")
            
            # 전체 user_data JSON 변환 시도
            try:
                logger.info("🧪 [FULL_JSON_CONVERSION] 전체 user_data JSON 변환 시도")
                print("🧪 [FULL_JSON_CONVERSION] 전체 user_data JSON 변환 시도")
                
                # 안전한 변환을 위해 places를 dict로 변환
                safe_user_data = user_data.copy()
                if 'places' in safe_user_data and isinstance(safe_user_data['places'], list):
                    safe_places = []
                    for place in safe_user_data['places']:
                        if hasattr(place, 'dict'):
                            safe_places.append(place.dict())
                        elif hasattr(place, '__dict__'):
                            safe_places.append(place.__dict__)
                        elif isinstance(place, dict):
                            safe_places.append(place)
                        else:
                            # 최후 수단: 문자열로 변환
                            safe_places.append(str(place))
                    safe_user_data['places'] = safe_places
                    logger.info(f"✅ [PLACES_CONVERSION] places 배열을 dict로 변환 완료: {len(safe_places)}개")
                    print(f"✅ [PLACES_CONVERSION] places 배열을 dict로 변환 완료: {len(safe_places)}개")
                
                input_data_json = json.dumps(safe_user_data, ensure_ascii=False, indent=2)
                logger.info(f"✅ [JSON_CONVERSION_SUCCESS] 입력 데이터 JSON 변환 완료 (길이: {len(input_data_json)})")
                print(f"✅ [JSON_CONVERSION_SUCCESS] 입력 데이터 JSON 변환 완료 (길이: {len(input_data_json)})")
                
            except Exception as json_conversion_error:
                logger.error("❌❌❌ [JSON_CONVERSION_FAIL] 전체 user_data JSON 변환 실패")
                logger.error(f"📊 [JSON_ERROR_TYPE] 에러 타입: {type(json_conversion_error).__name__}")
                logger.error(f"📊 [JSON_ERROR_MSG] 에러 메시지: {str(json_conversion_error)}")
                logger.error(f"📊 [JSON_ERROR_TRACEBACK]", exc_info=True)
                print(f"❌❌❌ [JSON_CONVERSION_FAIL] 전체 user_data JSON 변환 실패: {json_conversion_error}")
                
                # JSON 변환 실패 시 즉시 에러 발생
                logger.info("🔄 [JSON_FAIL_IMMEDIATE_ERROR] JSON 변환 실패로 즉시 에러 발생")
                print("🔄 [JSON_FAIL_IMMEDIATE_ERROR] JSON 변환 실패로 즉시 에러 발생")
                raise ValueError(f"입력 데이터 JSON 변환 실패: {json_conversion_error}")
            
            logger.info("✅ [JSON_CONVERSION_COMPLETE] JSON 변환 과정 완료")
            print("✅ [JSON_CONVERSION_COMPLETE] JSON 변환 과정 완료")
            
            # 프롬프트에 실제 데이터 주입
            final_prompt = master_prompt.replace('{input_data}', input_data_json)
            
            logger.info(f"📜 [FINAL_PROMPT_ENHANCED] Enhanced AI - 3단계 AI에게 보낼 최종 프롬프트 (길이: {len(final_prompt)}):")
            logger.info("=" * 100)
            logger.info("🚨🚨🚨 [COMPLETE_PROMPT_DEBUG] AI에게 전달되는 최종 프롬프트 전체 내용:")
            logger.info("=" * 100)
            logger.info(final_prompt)
            logger.info("=" * 100)
            logger.info("🚨🚨🚨 [COMPLETE_PROMPT_DEBUG_END] 프롬프트 끝")
            logger.info("=" * 100)
            
            # AI로 응답 생성
            logger.info("🤖 [AI_CALLING] Enhanced AI - AI 호출 시작...")
            response = await self.generate_response(final_prompt)
            logger.info(f"🤖 [AI_RESPONSE_RECEIVED] Enhanced AI - AI 응답 수신 완료 (길이: {len(response) if response else 0})")
            
            # ===== 🔍 AI 원본 응답 상세 로깅 =====
            logger.info("=" * 100)
            logger.info("🚨🚨🚨 [AI_RAW_RESPONSE_DEBUG] AI 원본 응답 전체:")
            logger.info("=" * 100)
            logger.info(f"📊 [RESPONSE_TYPE] 응답 타입: {type(response)}")
            logger.info(f"📊 [RESPONSE_LENGTH] 응답 길이: {len(response) if response else 0}")
            logger.info("📝 [RESPONSE_CONTENT] AI 응답 내용:")
            logger.info(response if response else "❌ 빈 응답")
            logger.info("=" * 100)
            logger.info("🚨🚨🚨 [AI_RAW_RESPONSE_DEBUG_END] AI 응답 끝")
            logger.info("=" * 100)
            
            # 🚨 [긴급 디버깅] AI 응답의 첫 500자와 마지막 500자 별도 로깅
            if response and len(response) > 1000:
                logger.info(f"🔍 [RESPONSE_HEAD] 응답 시작 부분 (500자):\n{response[:500]}")
                logger.info(f"🔍 [RESPONSE_TAIL] 응답 끝 부분 (500자):\n{response[-500:]}")
            
            # 🚨 [긴급 디버깅] JSON 구조 힌트 찾기
            if response:
                structure_hints = []
                if '"travel_plan"' in response:
                    structure_hints.append("travel_plan")
                if '"days"' in response:
                    structure_hints.append("days")
                if '"itinerary"' in response:
                    structure_hints.append("itinerary")
                if '"daily_plans"' in response:
                    structure_hints.append("daily_plans")
                if '"activities"' in response:
                    structure_hints.append("activities")
                
                logger.info(f"✅ [STRUCTURE_HINTS] 응답에서 발견된 구조 키워드: {structure_hints}")
            
            if not response or not response.strip():
                logger.error("=" * 100)
                logger.error("🚨🚨🚨 [EMPTY_RESPONSE_DEBUG] AI 빈 응답 분석:")
                logger.error(f"📊 [RESPONSE_IS_NONE] response is None: {response is None}")
                logger.error(f"📊 [RESPONSE_IS_EMPTY_STRING] response == '': {response == '' if response is not None else 'N/A'}")
                logger.error(f"📊 [RESPONSE_STRIPPED_EMPTY] response.strip() == '': {response.strip() == '' if response else 'N/A'}")
                logger.error(f"📊 [RESPONSE_REPR] repr(response): {repr(response)}")
                logger.error("🚨🚨🚨 [EMPTY_RESPONSE_DEBUG_END]")
                logger.error("=" * 100)
                raise ValueError("AI 응답이 비어있습니다")
            
            # ===== 🚨 [핵심 강화] JSON 응답 검증 및 정제 과정 상세 로깅 =====
            logger.info("🔧 [JSON_PARSING_START] Enhanced AI - JSON 파싱 시작")
            print("🔧 [JSON_PARSING_START] Enhanced AI - JSON 파싱 시작")
            
            try:
                # 1단계: JSON 정제
                logger.info("🔧 [STEP_1] JSON 정제 시작")
                print("🔧 [STEP_1] JSON 정제 시작")
                
                cleaned_response = self._extract_json_only(response)
                
                logger.info(f"✅ [CLEANED_SUCCESS] JSON 정제 완료 (길이: {len(cleaned_response)})")
                logger.info(f"🔧 [CLEANED_PREVIEW] 정제된 JSON 미리보기 (처음 500자): {cleaned_response[:500]}...")
                print(f"✅ [CLEANED_SUCCESS] JSON 정제 완료 (길이: {len(cleaned_response)})")
                
                # 2단계: JSON 파싱
                logger.info("🔧 [STEP_2] JSON 파싱 시작")
                print("🔧 [STEP_2] JSON 파싱 시작")
                
                parsed_json = json.loads(cleaned_response)
                
                logger.info(f"✅ [PARSED_SUCCESS] JSON 파싱 성공")
                logger.info(f"📊 [PARSED_DATA_TYPE] 파싱된 데이터 타입: {type(parsed_json)}")
                print(f"✅ [PARSED_SUCCESS] JSON 파싱 성공")
                
                # 3단계: 데이터 구조 분석
                logger.info("🔧 [STEP_3] 데이터 구조 분석 시작")
                print("🔧 [STEP_3] 데이터 구조 분석 시작")
                
                if isinstance(parsed_json, dict):
                    logger.info(f"📊 [PARSED_KEYS] 파싱된 최상위 키들: {list(parsed_json.keys())}")
                    print(f"📊 [PARSED_KEYS] 파싱된 최상위 키들: {list(parsed_json.keys())}")
                elif isinstance(parsed_json, list):
                    logger.info(f"📊 [PARSED_LIST] 파싱된 데이터는 배열 (길이: {len(parsed_json)})")
                    print(f"📊 [PARSED_LIST] 파싱된 데이터는 배열 (길이: {len(parsed_json)})")
                else:
                    logger.error(f"❌ [INVALID_TYPE] 예상치 못한 데이터 타입: {type(parsed_json)}")
                    print(f"❌ [INVALID_TYPE] 예상치 못한 데이터 타입: {type(parsed_json)}")
                    raise ValueError(f"AI 응답 데이터 타입 오류: {type(parsed_json)}")
                
            except json.JSONDecodeError as json_error:
                logger.error("❌❌❌ [JSON_DECODE_ERROR] JSON 파싱 실패")
                logger.error(f"📊 [JSON_ERROR_MSG] JSON 에러 메시지: {str(json_error)}")
                logger.error(f"📊 [JSON_ERROR_POS] 에러 위치: line {json_error.lineno}, column {json_error.colno}")
                logger.error(f"📊 [JSON_ERROR_DOC] 에러 문서: {json_error.doc[:200] if hasattr(json_error, 'doc') and json_error.doc else 'N/A'}...")
                logger.error(f"📊 [CLEANED_RESPONSE_SAMPLE] 정제된 응답 샘플 (처음 1000자): {cleaned_response[:1000]}...")
                print(f"❌❌❌ [JSON_DECODE_ERROR] JSON 파싱 실패: {json_error}")
                
                # JSON 파싱 실패 시 즉시 폴백
                logger.info("🔄 [JSON_PARSE_FAIL_FALLBACK] JSON 파싱 실패로 폴백 응답 반환")
                print("🔄 [JSON_PARSE_FAIL_FALLBACK] JSON 파싱 실패로 폴백 응답 반환")
                
                fallback_response = {
                    "travel_plan": {
                        "title": "일정 생성 실패",
                        "concept": "AI 응답 파싱 오류로 인한 기본 응답",
                        "total_days": 1,
                        "daily_start_time": "09:00",
                        "daily_end_time": "22:00",
                        "daily_plans": [{
                            "day": 1,
                            "date": "2024-01-01",
                            "activities": [{
                                "time": "09:00",
                                "name": "일정 재생성 필요",
                                "type": "안내",
                                "duration": 60,
                                "description": "AI 응답 파싱에 실패했습니다. 다시 시도해주세요."
                            }]
                        }]
                    }
                }
                return json.dumps(fallback_response, ensure_ascii=False)
                
            except Exception as parsing_error:
                logger.error("❌❌❌ [PARSING_GENERAL_ERROR] JSON 파싱 과정 일반 에러")
                logger.error(f"📊 [PARSING_ERROR_TYPE] 에러 타입: {type(parsing_error).__name__}")
                logger.error(f"📊 [PARSING_ERROR_MSG] 에러 메시지: {str(parsing_error)}")
                logger.error(f"📊 [PARSING_ERROR_TRACEBACK]", exc_info=True)
                print(f"❌❌❌ [PARSING_GENERAL_ERROR] JSON 파싱 과정 일반 에러: {parsing_error}")
                
                # 일반 파싱 에러 시 즉시 폴백
                logger.info("🔄 [PARSING_ERROR_FALLBACK] 파싱 에러로 폴백 응답 반환")
                print("🔄 [PARSING_ERROR_FALLBACK] 파싱 에러로 폴백 응답 반환")
                
                fallback_response = {
                    "travel_plan": {
                        "title": "일정 생성 실패",
                        "concept": "파싱 오류로 인한 기본 응답",
                        "total_days": 1,
                        "daily_start_time": "09:00",
                        "daily_end_time": "22:00",
                        "daily_plans": [{
                            "day": 1,
                            "date": "2024-01-01",
                            "activities": [{
                                "time": "09:00",
                                "name": "일정 재생성 필요",
                                "type": "안내",
                                "duration": 60,
                                "description": f"파싱 오류: {str(parsing_error)}"
                            }]
                        }]
                    }
                }
                return json.dumps(fallback_response, ensure_ascii=False)
            
            # 4단계: 데이터 추출 및 검증
            logger.info("🔧 [STEP_4] 데이터 추출 및 검증 시작")
            print("🔧 [STEP_4] 데이터 추출 및 검증 시작")
            
            # 🚨 [핵심 수정] 직접적인 데이터 추출 및 검증
            logger.info(f"🔍 [DIRECT_EXTRACTION] Enhanced AI - 직접적인 데이터 추출 시작")
            print(f"🔍 [DIRECT_EXTRACTION] Enhanced AI - 직접적인 데이터 추출 시작")
                
                # 1. 기본 타입 검증
                if not isinstance(parsed_json, dict):
                    logger.error(f"❌ [INVALID_TYPE] AI 응답이 딕셔너리가 아닙니다: {type(parsed_json)}")
                    raise ValueError(f"AI 응답 형식 오류: {type(parsed_json)}")
                
                # 2. 직접적인 데이터 추출 - 가능한 모든 키 패턴 확인
                travel_plan_data = None
                found_key = None
                
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
                        found_key = key
                        logger.info(f"✅ [FOUND_DATA] '{key}' 키에서 데이터 발견")
                        break
                
                # 3. 데이터 유효성 검증
                if travel_plan_data is None:
                    logger.error(f"❌ [NO_VALID_DATA] 유효한 여행 계획 데이터를 찾을 수 없습니다. 사용 가능한 키: {list(parsed_json.keys())}")
                    raise ValueError("AI 응답에서 여행 계획 데이터를 찾을 수 없습니다")
                
                # 4. 데이터 구조 정규화 및 검증
                logger.info(f"🔍 [DATA_STRUCTURE] 발견된 데이터 구조 분석: {type(travel_plan_data)}")
                
                if isinstance(travel_plan_data, dict):
                    # 딕셔너리인 경우 - daily_plans 또는 days 키 확인
                    if 'daily_plans' in travel_plan_data:
                        logger.info("✅ [FOUND_DAILY_PLANS] daily_plans 키 발견")
                        final_data = travel_plan_data
                        days_data = travel_plan_data['daily_plans']
                    elif 'days' in travel_plan_data:
                        logger.info("✅ [FOUND_DAYS] days 키 발견, daily_plans로 변환")
                        final_data = travel_plan_data.copy()
                        final_data['daily_plans'] = final_data.pop('days')
                        days_data = final_data['daily_plans']
                    else:
                        logger.warning("⚠️ [NO_DAILY_PLANS] daily_plans나 days 키가 없음, 전체 데이터를 daily_plans로 사용")
                        final_data = {
                            'title': '맞춤형 여행 일정',
                            'concept': 'AI가 생성한 최적화된 여행 계획',
                            'daily_plans': [travel_plan_data] if travel_plan_data else []
                        }
                        days_data = final_data['daily_plans']
                elif isinstance(travel_plan_data, list):
                    # 배열인 경우 - 직접 daily_plans로 사용
                    logger.info("✅ [ARRAY_DATA] 배열 데이터를 daily_plans로 사용")
                    final_data = {
                        'title': '맞춤형 여행 일정',
                        'concept': 'AI가 생성한 최적화된 여행 계획',
                        'daily_plans': travel_plan_data
                    }
                    days_data = travel_plan_data
                else:
                    logger.error(f"❌ [INVALID_DATA_TYPE] 예상치 못한 데이터 타입: {type(travel_plan_data)}")
                    raise ValueError(f"여행 계획 데이터 타입 오류: {type(travel_plan_data)}")
                
                # 5. 최종 검증 - 빈 일정 감지
                if not isinstance(days_data, list):
                    logger.error(f"❌ [INVALID_DAYS_TYPE] days 데이터가 배열이 아닙니다: {type(days_data)}")
                    raise ValueError("days 데이터가 배열 형식이 아닙니다")
                
                logger.info(f"🔍 [DAYS_COUNT] 일정 일수: {len(days_data)}")
                
                # 각 날짜별 활동 수 검증
                total_activities = 0
                for i, day in enumerate(days_data):
                    if isinstance(day, dict):
                        activities = day.get('activities', []) or day.get('schedule', []) or day.get('places', [])
                        activity_count = len(activities) if isinstance(activities, list) else 0
                        total_activities += activity_count
                        logger.info(f"🔍 [DAY_{i+1}_ACTIVITIES] {i+1}일차 활동 수: {activity_count}")
                    else:
                        logger.warning(f"⚠️ [INVALID_DAY_FORMAT] {i+1}일차 데이터가 딕셔너리가 아닙니다: {type(day)}")
                
                logger.info(f"🔍 [TOTAL_ACTIVITIES] 전체 활동 수: {total_activities}")
                
                # 🚨 [핵심] 빈 일정 감지 및 폴백 처리
                if len(days_data) == 0:
                    logger.warning("⚠️ [EMPTY_DAYS] AI가 일정 날짜를 생성하지 못했습니다. 기본 일정 생성")
                    # 기본 1일 일정 생성
                    days_data = [{
                        "day": 1,
                        "date": "2024-01-01",
                        "activities": [{
                            "time": "09:00",
                            "name": "여행 시작",
                            "type": "기타",
                            "duration": 60
                        }]
                    }]
                    final_data['daily_plans'] = days_data
                    total_activities = 1
                
                if total_activities == 0:
                    logger.warning("⚠️ [NO_ACTIVITIES] AI가 유효한 활동을 생성하지 못했습니다. 기본 활동 추가")
                    # 각 날짜에 기본 활동 추가
                    for i, day in enumerate(days_data):
                        if isinstance(day, dict):
                            activities = day.get('activities', [])
                            if not activities:
                                day['activities'] = [{
                                    "time": "09:00",
                                    "name": f"{i+1}일차 여행",
                                    "type": "기타",
                                    "duration": 60
                                }]
                                total_activities += 1
                
                logger.info(f"✅ [VALIDATION_SUCCESS] Enhanced AI - 데이터 검증 통과: {len(days_data)}일, 총 {total_activities}개 활동")
                
                # 최종 결과를 parsed_json에 할당 (기존 코드와의 호환성)
                parsed_json = {'travel_plan': final_data}
                
                # 6. 최종 JSON 반환
                final_response = json.dumps(parsed_json, ensure_ascii=False, indent=2)
                logger.info(f"📊 [FINAL_JSON] Enhanced AI - 최종 JSON 길이: {len(final_response)}")
                logger.info(f"✅ [ENHANCED_AI_SUCCESS] Enhanced AI Service - 일정 생성 완료")
                return final_response
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ [JSON_ERROR] Enhanced AI - JSON 파싱 최종 실패: {e}")
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
                logger.info("🔄 [ENHANCED_AI_FALLBACK] Enhanced AI - 폴백 응답 사용")
                return json.dumps(fallback_response, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"❌ [ENHANCED_AI_ERROR] Enhanced AI Service - 마스터 프롬프트 일정 생성 실패: {e}")
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