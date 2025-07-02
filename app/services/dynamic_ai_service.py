"""
동적 AI 서비스
관리자 설정에 따라 OpenAI 또는 Google Gemini를 선택적으로 사용
"""

import os
import json
from typing import Optional, Dict, Any
import openai
import google.generativeai as genai

from app.config import settings
from app.utils.logger import get_logger

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
        """현재 설정된 AI 제공자를 가져오기"""
        try:
            settings_file = "app/data/ai_settings.json"
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings_data = json.load(f)
                    return settings_data.get("provider", "openai")
        except Exception as e:
            logger.error(f"AI 설정 파일 읽기 실패: {e}")
        
        # 기본값은 OpenAI
        return "openai"
    
    async def generate_text(self, prompt: str, max_tokens: int = 2000) -> str:
        """
        현재 설정된 AI 제공자를 사용하여 텍스트 생성
        """
        current_provider = self._get_current_provider()
        logger.info(f"현재 AI 제공자: {current_provider}")
        
        try:
            if current_provider == "gemini":
                return await self._generate_with_gemini(prompt, max_tokens)
            else:
                return await self._generate_with_openai(prompt, max_tokens)
        except Exception as e:
            logger.error(f"{current_provider} AI 생성 실패, 대체 제공자로 시도: {e}")
            
            # 현재 제공자가 실패하면 다른 제공자로 시도
            if current_provider == "gemini":
                return await self._generate_with_openai(prompt, max_tokens)
            else:
                return await self._generate_with_gemini(prompt, max_tokens)
    
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