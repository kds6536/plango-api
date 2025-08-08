"""
동적 AI 서비스
관리자 설정에 따라 OpenAI 또는 Google Gemini를 선택적으로 사용
"""

import os
import json
from typing import Optional, Dict, Any, List
import openai
import google.generativeai as genai

from app.config import settings
from app.utils.logger import get_logger
from app.routers.admin import load_ai_settings_from_db
from app.services.supabase_service import supabase_service

logger = get_logger(__name__)

class DynamicAIService:
    """관리자 설정에 따라 동적으로 AI 제공자를 선택하는 서비스"""
    
    def __init__(self):
        self.openai_client = None
        self.gemini_model = None
        self._setup_clients()
    
    def _setup_clients(self):
        """AI 클라이언트들을 초기화"""
        try:
            # OpenAI 클라이언트 설정
            if settings.OPENAI_API_KEY:
                self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("OpenAI 클라이언트 초기화 완료")
            
            # Gemini 클라이언트 설정
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("Gemini 클라이언트 초기화 완료")
                
        except Exception as e:
            logger.error(f"AI 클라이언트 초기화 실패: {e}")
    
    def _get_current_provider(self) -> str:
        """현재 설정된 AI 제공자를 Supabase DB에서 가져오기"""
        try:
            settings_dict = load_ai_settings_from_db()
            return settings_dict.get("default_provider", "gemini")
        except Exception as e:
            logger.error(f"AI provider DB 조회 실패: {e}")
            return "gemini"
    
    def _create_default_settings_file(self, settings_file: str):
        """기본 AI 설정 파일 생성"""
        try:
            # data 디렉토리가 없으면 생성
            os.makedirs(os.path.dirname(settings_file), exist_ok=True)
            
            default_settings = {
                # 기본 제공자를 'gemini'로 변경
                "provider": "gemini",
                "last_updated": "2025-01-02T00:00:00Z",
                "settings": {
                    "openai": {
                        "model": "gpt-3.5-turbo",
                        "temperature": 0.7,
                        "max_tokens": 2000
                    },
                    "gemini": {
                        "model": "gemini-1.5-flash",
                        "temperature": 0.7,
                        "max_tokens": 2000
                    }
                }
            }
            
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(default_settings, f, indent=2, ensure_ascii=False)
            
            logger.info(f"기본 AI 설정 파일 생성 완료: {settings_file}")
            
        except Exception as e:
            logger.error(f"기본 AI 설정 파일 생성 실패: {e}")
    
    async def generate_text(self, prompt: str, max_tokens: int = 2000) -> str:
        """
        현재 설정된 AI 제공자를 사용하여 텍스트 생성
        """
        # provider를 generate_text 호출 시마다 실시간으로 읽음
        current_provider = self._get_current_provider()
        
        # === Railway 로그: AI 호출 시작 ===
        logger.info(f"🤖 [AI_START] AI 텍스트 생성 시작")
        logger.info(f"🔧 [AI_PROVIDER] 현재 AI 제공자: {current_provider}")
        logger.info(f"📏 [PROMPT_LENGTH] 프롬프트 길이: {len(prompt)} 글자")
        logger.info(f"🎛️ [MAX_TOKENS] 최대 토큰: {max_tokens}")
        logger.info(f"📝 [PROMPT_PREVIEW] 프롬프트 미리보기: {prompt[:200]}...")
        
        try:
            if current_provider == "gemini":
                logger.info(f"🟢 [AI_GEMINI] Google Gemini로 텍스트 생성 시작")
                result = await self._generate_with_gemini(prompt, max_tokens)
            else:
                logger.info(f"🔵 [AI_OPENAI] OpenAI로 텍스트 생성 시작")
                result = await self._generate_with_openai(prompt, max_tokens)
            
            # === Railway 로그: AI 호출 성공 ===
            logger.info(f"✅ [AI_SUCCESS] AI 텍스트 생성 완료")
            logger.info(f"📊 [RESULT_LENGTH] 응답 길이: {len(result)} 글자")
            logger.info(f"📄 [RESULT_PREVIEW] 응답 미리보기: {result[:200]}...")
            
            return result
            
        except Exception as e:
            # === Railway 로그: AI 호출 실패 ===
            logger.error(f"❌ [AI_ERROR] {current_provider} AI 생성 실패")
            logger.error(f"🚨 [ERROR_TYPE] {type(e).__name__}")
            logger.error(f"📝 [ERROR_MESSAGE] {str(e)}")
            # 다른 AI로 재시도하지 않고, 예외를 그대로 올려 fallback 처리
            raise
    
    async def _generate_with_openai(self, prompt: str, max_tokens: int) -> str:
        """OpenAI를 사용하여 텍스트 생성"""
        if not self.openai_client:
            raise Exception("OpenAI 클라이언트가 초기화되지 않았습니다")
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 여행 일정 전문가입니다. 사용자의 요청에 따라 최적의 여행 일정을 생성해주세요."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            result = response.choices[0].message.content.strip()
            logger.info(f"OpenAI 응답 생성 완료 ({len(result)} 글자)")
            return result
            
        except Exception as e:
            logger.error(f"OpenAI API 호출 실패: {e}")
            raise Exception(f"OpenAI 텍스트 생성 실패: {str(e)}")
    
    async def _generate_with_gemini(self, prompt: str, max_tokens: int) -> str:
        """Google Gemini를 사용하여 텍스트 생성"""
        if not self.gemini_model:
            raise Exception("Gemini 모델이 초기화되지 않았습니다")
        
        try:
            # Gemini용 프롬프트 구성
            full_prompt = f"""당신은 여행 일정 전문가입니다. 사용자의 요청에 따라 최적의 여행 일정을 생성해주세요.

사용자 요청:
{prompt}

응답은 정확하고 실용적인 여행 정보를 포함해주세요."""

            response = self.gemini_model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.7,
                )
            )
            
            result = response.text.strip()
            logger.info(f"Gemini 응답 생성 완료 ({len(result)} 글자)")
            return result
            
        except Exception as e:
            logger.error(f"Gemini API 호출 실패: {e}")
            raise Exception(f"Gemini 텍스트 생성 실패: {str(e)}")
    
    async def create_search_queries(self, city: str, country: str, existing_places: List[str] = None) -> Dict[str, str]:
        """
        AI가 중복을 피하는 최적의 검색 쿼리를 4개 카테고리별로 생성
        
        Args:
            city: 도시명
            country: 국가명  
            existing_places: 기존에 추천된 장소 목록 (중복 방지용)
            
        Returns:
            Dict[str, str]: 카테고리별 검색 쿼리
            {
                "tourism": "서울 경복궁 창덕궁 불교 사찰",
                "food": "서울 한식 맛집 갈비 냉면",  
                "activity": "서울 한강 공원 트레킹",
                "accommodation": "서울 호텔 게스트하우스"
            }
        """
        logger.info(f"🔍 [AI_SEARCH_PLAN] AI 검색 계획 수립 시작 - {city}, {country}")
        
        try:
            # Supabase에서 검색 계획 전용 프롬프트 템플릿 조회
            prompt_template = await supabase_service.get_master_prompt("search_strategy_v1")
            
            # 기존 장소 목록을 문자열로 변환
            existing_places_text = ""
            if existing_places:
                existing_places_text = f"""
이미 추천된 장소들 (중복 금지):
{', '.join(existing_places)}

위 장소들과 중복되지 않는 완전히 새로운 장소만 검색해주세요."""
            else:
                existing_places_text = "첫 번째 검색이므로 제약 없이 최고의 장소들을 검색해주세요."
            
            # 프롬프트 템플릿에 데이터 치환
            from string import Template
            template = Template(prompt_template)
            
            search_prompt = template.safe_substitute(
                city=city,
                country=country,
                existing_places=existing_places_text
            )
            
            logger.info(f"📋 [SEARCH_PROMPT] 검색 계획 프롬프트 생성 완료 ({len(search_prompt)} 글자)")
            
            # AI에게 검색 계획 요청
            response = await self.generate_text(search_prompt, max_tokens=1000)
            
            # JSON 응답 파싱
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                search_queries = json.loads(json_match.group())
                logger.info(f"✅ [SEARCH_QUERIES] AI 검색 계획 생성 완료: {search_queries}")
                return search_queries
            else:
                raise ValueError("AI 응답에서 JSON 형태의 검색 계획을 찾을 수 없습니다")
                
        except Exception as e:
            logger.error(f"❌ [SEARCH_PLAN_ERROR] AI 검색 계획 수립 실패: {e}")
            # 폴백: 기본 검색 쿼리 반환
            fallback_queries = {
                "tourism": f"{city} {country} tourist attractions landmarks museums",
                "food": f"{city} {country} restaurants local food specialties",
                "activity": f"{city} {country} activities entertainment sports",
                "accommodation": f"{city} {country} hotels accommodations lodging"
            }
            logger.info(f"🔄 [FALLBACK] 기본 검색 쿼리 사용: {fallback_queries}")
            return fallback_queries

    def get_provider_info(self) -> Dict[str, Any]:
        """현재 AI 제공자 정보 반환"""
        current_provider = self._get_current_provider()
        
        provider_info = {
            "current_provider": current_provider,
            "available_providers": [],
            "provider_status": {}
        }
        
        # OpenAI 상태 확인
        if self.openai_client and settings.OPENAI_API_KEY:
            provider_info["available_providers"].append("openai")
            provider_info["provider_status"]["openai"] = "available"
        else:
            provider_info["provider_status"]["openai"] = "not_configured"
        
        # Gemini 상태 확인
        if self.gemini_model and settings.GEMINI_API_KEY:
            provider_info["available_providers"].append("gemini")
            provider_info["provider_status"]["gemini"] = "available"
        else:
            provider_info["provider_status"]["gemini"] = "not_configured"
        
        return provider_info

# 전역 인스턴스 생성
dynamic_ai_service = DynamicAIService() 