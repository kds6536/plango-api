"""
고급 여행 일정 생성 서비스
사용자가 요청한 4단계 프로세스를 구현합니다:
1. AI 브레인스토밍 - 장소 이름 후보군 생성
2. 구글 플레이스 API 정보 강화 - 실제 데이터 부여
3. AI 큐레이션 - 1안/2안 분할 및 상세 일정 구성
4. 최종 JSON 조립 및 반환
"""

import os
import json
import uuid
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

from app.schemas.itinerary import (
    GenerateRequest, GenerateResponse, OptimizeRequest, OptimizeResponse,
    TravelPlan, DayPlan, ActivityDetail, PlaceData, ActivityItem
)
from app.services.google_places_service import GooglePlacesService
from app.services.ai_handlers import OpenAIHandler, GeminiHandler
from app.utils.logger import get_logger
from app.routers.admin import load_ai_settings_from_db, load_prompts_from_db
from fastapi import HTTPException

logger = get_logger(__name__)


class AdvancedItineraryService:
    """고급 여행 일정 생성 서비스"""
    
    def __init__(self):
        # 서비스 초기화
        from app.config import settings
        import openai
        import google.generativeai as genai
        self.settings = settings
        self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.gemini_client = genai if settings.GEMINI_API_KEY else None
        self.model_name_openai = getattr(settings, "OPENAI_MODEL", "gpt-3.5-turbo")
        self.model_name_gemini = getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash")
        self.google_places = GooglePlacesService()
        logger.info("AdvancedItineraryService 초기화 완료 - AI 핸들러 패턴 적용")

    def _get_ai_handler(self):
        settings_dict = load_ai_settings_from_db()
        provider = settings_dict.get("default_provider", "openai").lower()
        openai_model = settings_dict.get("openai_model_name", "gpt-3.5-turbo")
        gemini_model = settings_dict.get("gemini_model_name", "gemini-1.5-flash")
        if provider == "gemini":
            return GeminiHandler(self.gemini_client, gemini_model)
        else:
            return OpenAIHandler(self.openai_client, openai_model)

    async def generate_itinerary(self, request: GenerateRequest) -> GenerateResponse:
        """
        4단계 프로세스로 여행 일정을 생성합니다
        """
        request_id = str(uuid.uuid4())
        raw_response = None
        
        # === 배포 확인용 디버그 메시지 ===
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"🚀 [DEPLOYMENT_CHECK] 새 배포 확인 - {timestamp} - 파싱 로직 수정됨")
        
        # === Railway 로그: 요청 시작 ===
        logger.info("=" * 80)
        logger.info(f"🚀 [REQUEST_START] 여행 일정 생성 요청 시작")
        logger.info(f"📋 [REQUEST_ID] {request_id}")
        logger.info(f"🏙️ [CITY] {request.city}")
        logger.info(f"📅 [DURATION] {request.duration}일")
        logger.info(f"💰 [BUDGET] {request.budget_range}")
        logger.info(f"👥 [TRAVELERS] {request.travelers_count}명")
        logger.info(f"🎨 [STYLE] {request.travel_style}")
        logger.info(f"📝 [REQUESTS] {request.special_requests}")
        logger.info("=" * 80)
        
        try:
            # === 1단계: AI 브레인스토밍 ===
            logger.info(f"🧠 [STEP_1_START] AI 브레인스토밍 시작 - 장소 후보군 생성")
            place_candidates = await self._step1_ai_brainstorming(request)
            logger.info(f"✅ [STEP_1_SUCCESS] AI 브레인스토밍 완료")
            logger.info(f"📊 [STEP_1_RESULT] {len(place_candidates)}개 카테고리의 장소 후보 생성")
            logger.info(f"📝 [STEP_1_CATEGORIES] {list(place_candidates.keys())}")
            
            # === 2단계: 구글 플레이스 API 정보 강화 ===
            logger.info(f"🌍 [STEP_2_START] 구글 플레이스 API 정보 강화 시작")
            place_pool = await self._step2_google_places_enrichment(place_candidates, request.city)
            if not place_pool:
                logger.error("2단계 결과, 유효한 장소를 찾지 못해 3단계를 진행할 수 없습니다.")
                raise ValueError("No valid places found in Step 2")
            logger.info(f"✅ [STEP_2_SUCCESS] 구글 플레이스 API 정보 강화 완료")
            logger.info(f"📊 [STEP_2_RESULT] {len(place_pool)}개 장소 데이터 풀 생성")
            for i, place in enumerate(place_pool[:5]):  # 처음 5개만 로그
                logger.info(f"📍 [STEP_2_PLACE_{i+1}] {place.get('name', 'N/A')} - {place.get('address', 'N/A')}")
            
            # === 3단계: AI 큐레이션 ===
            logger.info(f"🎨 [STEP_3_START] AI 큐레이션 시작 - 1안/2안 분할 및 상세 일정 구성")
            ai_plans = await self._step3_ai_curation(request, place_pool)
            logger.info(f"✅ [STEP_3_SUCCESS] AI 큐레이션 완료")
            logger.info(f"📊 [STEP_3_RESULT] 1안/2안 큐레이션 완료")
            
            # === 4단계: 최종 JSON 조립 ===
            logger.info(f"🔧 [STEP_4_START] 최종 JSON 조립 시작")
            final_response = self._step4_json_assembly(ai_plans, place_pool, request_id)
            logger.info(f"✅ [STEP_4_SUCCESS] 최종 JSON 조립 완료")
            logger.info(f"📊 [STEP_4_RESULT] Plan A: '{final_response.plan_a.title}', Plan B: '{final_response.plan_b.title}'")
            
            # === Railway 로그: 전체 완료 ===
            logger.info("=" * 80)
            logger.info(f"🎉 [REQUEST_SUCCESS] 여행 일정 생성 완료 [{request_id}]")
            logger.info(f"📋 [FINAL_PLAN_A] {final_response.plan_a.title}")
            logger.info(f"📋 [FINAL_PLAN_B] {final_response.plan_b.title}")
            logger.info(f"🏛️ [TOTAL_PLACES] {len(final_response.plan_a.places)}개 장소 포함")
            logger.info("=" * 80)
            
            return final_response
            
        except Exception as e:
            # === Railway 로그: 에러 상세 ===
            logger.error("=" * 80)
            logger.error(f"❌ [REQUEST_ERROR] 여행 일정 생성 실패 [{request_id}]")
            logger.error(f"🚨 [ERROR_TYPE] {type(e).__name__}")
            logger.error(f"📝 [ERROR_MESSAGE] {str(e)}")
            logger.error(f"🔍 [ERROR_TRACEBACK] {traceback.format_exc()}", exc_info=True)
            if 'raw_response' in locals() and raw_response:
                logger.error(f"📝 [AI_RAW_RESPONSE] {raw_response}")
            logger.error("=" * 80)
            # fallback 응답 대신 HTTPException 발생
            raise HTTPException(status_code=500, detail=f"여행 일정 생성 중 오류 발생: {str(e)}")

    async def generate_recommendations(self, request, language_code):
        """Plango v5.0: 1~5단계 전체 추천 생성 프로세스"""
        try:
            # 2. 1차 AI 브레인스토밍
            logger.info("🧠 [STEP 2] 1차 AI 브레인스토밍 시작")
            ai_keywords = await self._step2_ai_brainstorming(request, language_code)

            # 3. 1차 장소 정보 강화
            logger.info("🌍 [STEP 3] 1차 장소 정보 강화 시작")
            place_results = await self._step3_enhance_places(ai_keywords, request.city, language_code)

            # 4. 1차 후처리 및 검증
            logger.info("📊 [STEP 4] 1차 후처리 및 검증 시작")
            final_recommendations = self._step4_process_and_filter(place_results)

            # 5. 재귀적 보완 프로세스 (조건부)
            logger.info("🔄 [STEP 5] 최소 개수 검증 및 보완 프로세스 시작")
            final_recommendations = await self._step5_ensure_minimum_count(
                final_recommendations, request, language_code, ai_keywords
            )
            
            # [추가] 최종 결과가 비어있는지 확인하고, 비어있다면 404 에러를 발생시킵니다.
            if not final_recommendations:
                logger.warning("모든 카테고리에서 최소 추천 개수를 만족하는 장소를 찾지 못해, 에러를 반환합니다.")
                raise HTTPException(
                    status_code=404, 
                    detail="AI가 추천할 만한 장소를 찾지 못했습니다. 요청사항을 좀 더 구체적으로 작성해보세요."
                )

            return final_recommendations
        except Exception as e:
            logger.error(f"추천 생성 프로세스 실패: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="추천 생성 중 오류 발생")

    async def _step1_ai_brainstorming(self, request: GenerateRequest) -> Dict[str, List[str]]:
        """
        1단계: AI 브레인스토밍 - 장소 이름 후보군 생성
        """
        prompts_dict = load_prompts_from_db()
        prompt1 = prompts_dict.get("stage1_destinations_prompt")
        if not prompt1:
            prompt1 = f"당신은 'Plango AI'라는 이름의 세계 최고의 여행 컨설턴트입니다.\n사용자의 요청: {request.city}, {request.duration}일, {getattr(request, 'budget_range', 'medium')}, {getattr(request, 'travel_style', [])}, {request.special_requests or '일반적인 여행'}"
        
        format_dict = {
            "city": request.city,
            "duration": request.duration,
            "budget": getattr(request, 'budget_range', 'medium'),
            "travel_style": getattr(request, 'travel_style', []),
            "special_requests": request.special_requests or '일반적인 여행',
            "main_theme": ""
        }
        
        try:
            prompt1 = prompt1.format(**format_dict)
        except KeyError as e:
            logger.error(f"프롬프트 format KeyError: {e} | 프롬프트: {prompt1[:200]}...", exc_info=True)
            # 에러 발생 시 간단한 대체 프롬프트 사용
            prompt1 = f"당신은 'Plango AI'라는 이름의 세계 최고의 여행 컨설턴트입니다.\n사용자의 요청: {request.city}, {request.duration}일, {getattr(request, 'budget_range', 'medium')}, {getattr(request, 'travel_style', [])}, {request.special_requests or '일반적인 여행'}"
        try:
            handler = self._get_ai_handler()
            raw_response = await handler.get_completion(prompt1)
            logger.info(f"🤖 [AI_RAW_RESPONSE] from {type(handler).__name__}: {raw_response}")
            
            # AI 응답을 JSON으로 파싱
            try:
                ai_response = json.loads(raw_response)
                logger.info(f"✅ [AI_PARSED] AI 응답 파싱 성공: {ai_response}")
            except json.JSONDecodeError:
                logger.warning("AI 응답 JSON 파싱 실패, 하드코딩된 응답 사용")
                ai_response = {
                    "main_theme": f"{request.city} 문화 체험 여행",
                    "recommendations": {
                        "accommodations": ["도쿄역 호텔", "신주쿠 호텔", "시부야 호텔"],
                        "attractions": ["센소지 절", "메이지 신궁", "도쿄 타워", "스카이트리"],
                        "foods": ["스시 맛집", "라멘 맛집", "이자카야", "와규 레스토랑"],
                        "activities": ["온센 체험", "쇼핑", "카라오케", "애니메이션 카페"]
                    }
                }
            
            if not ai_response.get("recommendations"):
                logger.error(f"1단계 결과물에 recommendations가 없어 2단계를 진행할 수 없습니다. 실제 응답: {ai_response}")
                raise HTTPException(status_code=500, detail="[2025-01-11 UPDATED] No recommendations in AI response")
            
            # 새로운 응답 구조에서 카테고리별 키워드 추출
            place_candidates = {}
            recommendations = ai_response["recommendations"]
            
            # 카테고리별로 키워드 리스트 추출
            for category, keywords in recommendations.items():
                if keywords and isinstance(keywords, list):
                    place_candidates[category] = keywords
            
            self.travel_theme = ai_response.get("main_theme", f"{request.city} 여행")
            return place_candidates
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"1단계 AI 브레인스토밍 실패: {e} | 원본 응답: {locals().get('raw_response')}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"AI 브레인스토밍 실패: {e}")

    async def _step2_ai_brainstorming(self, request, language_code, existing_keywords=None):
        """
        2단계: AI 브레인스토밍 - 장소 후보군 생성 (카테고리별 키워드 요청)
        """
        prompts_dict = load_prompts_from_db()
        # [수정] 프롬프트 내용을 조금 더 명확하게 변경하고, 키워드 요청 개수를 7개로 늘립니다.
        prompt_template = prompts_dict.get("stage2_destinations_prompt", """
당신은 'Plango AI'라는 이름의 여행지 추천 전문가입니다. 사용자의 요청사항을 기반으로, 방문할 만한 장소에 대한 키워드를 카테고리별로 추천해주세요.

**사용자 요청:**
- 목적지: {destination}
- 여행 기간: {duration}일
- 예산: {budget}
- 특별 요청사항: {special_requests}

**## 지시사항 ##**
1. **카테고리 분류:** "숙소", "볼거리", "먹거리", "즐길거리" 4가지 카테고리로 나누어 추천합니다.
2. **키워드 생성:** 각 카테고리별로, 연관성이 높은 장소 키워드를 **7개**씩 생성해주세요.
3. **구체적인 이름:** "맛집"이나 "호텔" 같은 일반적인 단어 대신, "현지인들이 자주 가는 파스타 맛집" 또는 "바다 전망이 좋은 부티크 호텔"처럼 구체적인 키워드를 제안해야 합니다.
4. **언어 설정:** 모든 키워드는 "{language}"로 작성해주세요.
5. **JSON 형식 준수:** 답변은 반드시 아래 JSON 형식만 따라야 하며, 다른 설명은 절대 추가하지 마세요.

{{
  "숙소": ["키워드1", "키워드2", ...],
  "볼거리": ["키워드1", "키워드2", ...],
  "먹거리": ["키워드1", "키워드2", ...],
  "즐길거리": ["키워드1", "키워드2", ...]
}}
""")

        language_map = {"ko": "한국어", "en": "영어"}
        prompt = prompt_template.format(
            destination=request.city,
            duration=request.duration,
            budget=request.budget_range,
            special_requests=request.special_requests,
            language=language_map.get(language_code, "한국어")
        )
        
        try:
            handler = self._get_ai_handler()
            logger.info(f"📜 [STEP_2_PROMPT] 2단계 AI에게 보낼 최종 프롬프트:\n{prompt}")
            content = await handler.get_completion(prompt)
            logger.info(f"🤖 [AI_RAW_RESPONSE] 2단계 AI 원본 응답: '{content}'")
            
            if not content or not content.strip():
                logger.error("❌ 2단계 AI 브레인스토밍 실패: AI가 빈 응답을 반환했습니다.")
                raise ValueError("AI returned an empty or whitespace-only response.")
            
            ai_response = json.loads(content)
            
            if not all(k in ai_response for k in ["숙소", "볼거리", "먹거리", "즐길거리"]):
                logger.error(f"❌ 2단계 AI 브레인스토밍 실패: 필수 카테고리가 누락되었습니다. 응답: {ai_response}")
                raise ValueError("AI response is missing one or more required categories.")

            return ai_response
        except json.JSONDecodeError:
            logger.error(f"❌ 2단계 AI 브레인스토밍 실패: AI 응답이 유효한 JSON이 아닙니다. 응답: {content}")
            raise ValueError("AI response was not valid JSON.")
        except Exception as e:
            logger.error(f"❌ 2단계 AI 브레인스토밍 중 예상치 못한 오류 발생: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"AI 브레인스토밍 실패: {e}")

    async def _step3_enhance_places(self, keywords_by_category, city: str, language_code: str):
        """
        3단계: Google Places API 정보 강화 (병렬 호출)
        """
        place_results = {}
        for category, keywords in keywords_by_category.items():
            if not keywords:
                continue
            
            # 카테고리별 결과를 저장할 리스트 초기화
            place_results[category] = []
            
            logger.info(f"🌍 [STEP_3_GOOGLE_CALL] 카테고리 '{category}'에 대한 Google Places API 호출 시작")
            for keyword in keywords:
                try:
                    # get_place_details 호출 시 city 정보 추가
                    place_data = await self.google_places.get_place_details(keyword, city, language_code)
                    if place_data:
                        # 반환된 place_data가 단일 dict이므로, 리스트에 바로 추가
                        place_results[category].append(place_data)
                        logger.info(f"✅ [STEP_3_GOOGLE_SUCCESS] 장소 '{keyword}' 정보 강화 완료")
                    else:
                        logger.warning(f"⚠️ [STEP_3_GOOGLE_WARNING] 장소 '{keyword}' 정보 강화 실패 또는 데이터 없음")
                except Exception as e:
                    logger.error(f"❌ [STEP_3_GOOGLE_ERROR] 장소 '{keyword}' 정보 강화 중 오류 발생: {e}", exc_info=True)
        return place_results

    def _step4_process_and_filter(self, place_results: Dict[str, List[Dict]], max_items: int = 5) -> Dict[str, List[Dict]]:
        """
        4단계: 1차 후처리 및 검증 (중복 제거 및 최소 개수 필터링 강화)
        """
        MINIMUM_ITEMS = 2  # 카테고리별 최소 장소 개수
        
        # 최종 결과를 담을 딕셔너리
        final_results = {}
        # 전체 중복을 확인하기 위한 set
        globally_seen_place_ids = set()

        # 1. 모든 카테고리를 순회하며 사진이 있고 유효한 장소들만 필터링 및 글로벌 중복 제거
        #    (동일 장소가 여러 키워드에 의해 여러 카테고리에서 추천될 수 있으므로, 카테고리별로 먼저 처리)
        categorized_valid_places = defaultdict(list)
        
        for category, places in place_results.items():
            for place in places:
                place_id = place.get("place_id")
                # 사진 URL이 있고, 이전에 다른 카테고리에서도 추가되지 않은 장소만 포함
                if place.get("photo_url") and place_id and place_id not in globally_seen_place_ids:
                    categorized_valid_places[category].append(place)
                    globally_seen_place_ids.add(place_id)

        # 2. 필터링된 목록을 기준으로 최소 개수 검증 및 최종 결과 생성
        for category, places in categorized_valid_places.items():
            if len(places) >= MINIMUM_ITEMS:
                # 개수가 충족되면 최종 결과에 포함 (최대 max_items개)
                final_results[category] = places[:max_items]
                logger.info(
                    f"✅ 카테고리 '{category}'는 {len(places)}개의 유효한 장소를 가져 최종 결과에 포함됩니다. "
                    f"(상위 {len(final_results[category])}개 선택)"
                )
            else:
                # 개수 미달 시, 로그를 남기고 결과에서 제외
                logger.warning(
                    f"⚠️ 카테고리 '{category}'의 유효한 추천 장소가 {len(places)}개로, "
                    f"최소 기준({MINIMUM_ITEMS}개)에 미달하여 최종 결과에서 제외됩니다."
                )
                
        return final_results

    async def _step5_ensure_minimum_count(self, current_recs, request, lang, existing_kws):
        """
        5단계: 최소 개수 검증 및 보완 (조건부 재귀)
        """
        # 카테고리별 최소 2개 요구사항 확인
        categories_with_few_recs = {}
        for category, keywords in existing_kws.items():
            if len(keywords) < 2:
                categories_with_few_recs[category] = keywords

        if not categories_with_few_recs:
            logger.info("최소 개수 검증 완료: 모든 카테고리가 최소 2개 이상의 장소를 가지고 있습니다.")
            return current_recs

        logger.warning(f"최소 개수 검증 실패: 다음 카테고리들이 최소 2개 미만의 장소를 가지고 있습니다: {categories_with_few_recs}")

        # 추가 검색을 위한 새로운 키워드 목록 생성
        new_keywords_by_category = {}
        for category, keywords in categories_with_few_recs.items():
            # 기존 키워드 중 하나를 추가로 요청
            if keywords:
                new_keywords_by_category[category] = [keywords[0]] # 첫 번째 키워드를 추가로 요청

        if not new_keywords_by_category:
            logger.error("추가 검색할 키워드가 없어 최소 개수 보완을 완료할 수 없습니다.")
            return current_recs # 기존 결과 반환

        logger.info(f"추가 검색을 위해 카테고리별 키워드 목록: {new_keywords_by_category}")

        # 2단계 AI 브레인스토밍 호출 (추가 검색)
        new_ai_keywords = await self._step2_ai_brainstorming(request, lang, new_keywords_by_category)

        # 3단계 Google Places API 정보 강화 (추가 검색)
        new_place_results = await self._step3_enhance_places(new_ai_keywords, request.city, lang)

        # 4단계 후처리 및 검증 (추가 검색)
        new_final_recommendations = self._step4_process_and_filter(new_place_results)

        # 기존 결과와 추가 결과 병합
        final_recommendations = current_recs + new_final_recommendations

        # 중복 제거 (place_id 기준)
        seen_place_ids = set()
        unique_recommendations = []
        for rec in final_recommendations:
            if rec.get("place_id") not in seen_place_ids:
                seen_place_ids.add(rec.get("place_id"))
                unique_recommendations.append(rec)

        return unique_recommendations

    async def _step2_google_places_enrichment(
        self, 
        place_candidates: Dict[str, List[str]], 
        city: str
    ) -> List[Dict[str, Any]]:
        """
        2단계: 구글 플레이스 API 정보 강화
        """
        place_pool = []
        
        for category, place_names in place_candidates.items():
            # 카테고리별로 장소 데이터 강화
            enriched_places = await self.google_places.enrich_places_data(place_names, city)
            
            # 카테고리 정보 추가
            for place in enriched_places:
                place['category'] = category
                place_pool.append(place)
        
        # 중복 제거 (place_id 기준)
        seen_ids = set()
        unique_places = []
        for place in place_pool:
            if place.get('place_id') not in seen_ids:
                seen_ids.add(place.get('place_id'))
                unique_places.append(place)
        
        return unique_places

    async def _step3_ai_curation(
        self, 
        request: GenerateRequest, 
        place_pool: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        3단계: AI 큐레이션 - 1안/2안 분할 및 상세 일정 구성
        """
        travel_dates = f"Day 1 to Day {request.duration}"
        
        prompts_dict = load_prompts_from_db()
        prompt2 = prompts_dict.get("stage2_itinerary_prompt")
        if not prompt2:
            prompt2 = f"""당신은 'Plango AI'라는 이름의 최고의 여행 일정 설계 전문가입니다.
당신의 임무는 사전 검증된 장소 목록과 사용자의 원래 요청사항을 바탕으로, 가장 효율적이고 매력적인 일일 여행 계획을 수립하는 것입니다.

**사용자의 원래 요청사항:**
- 목적지: {request.city}
- 여행 기간: {request.duration}일
- 예산: {getattr(request, 'budget_range', 'medium')}
- 여행 스타일: {getattr(request, 'travel_style', [])}
- 특별 요청사항: {request.special_requests or '일반적인 여행'}

**API로 검증된 장소 목록:**
```json
{json.dumps(place_pool, ensure_ascii=False, indent=2)}
```

**## 지시사항 ##**
1. **입력 분석:** 사용자의 원래 요청사항과 API로 검증된 장소 목록을 함께 분석합니다.
2. **동선 최적화:** 각 장소의 위도/경도 정보를 활용하여, 지리적으로 가까운 장소들을 같은 날 일정으로 묶어 이동 시간을 최소화합니다. 이것이 가장 중요한 임무입니다.
3. **논리적 시간 배분:** 활동들을 '오전', '점심', '오후', '저녁' 시간대에 맞게 논리적으로 배치합니다.
4. **사용자 맞춤:** 사용자의 원래 요청(여유롭게, 빡빡하게 등)을 참고하여 하루에 배치할 활동의 개수를 조절합니다.
5. **응답 형식:** 당신의 답변은 **반드시** 아래에 명시된 구조의 **JSON 객체 하나**여야 합니다. 다른 설명은 절대 추가하지 마세요.

**## 핵심 규칙 (매우 중요) ##**
- **데이터 무결성:** 장소 목록에 제공된 `place_id`와 `name`을 절대 변경하거나 누락하지 말고, 그대로 출력 JSON에 포함시켜야 합니다.
- **지리적 클러스터링:** 위도/경도 좌표를 기준으로 가장 가까운 장소들을 묶는 것을 최우선으로 고려하세요.
- **창의적 설명:** 각 날짜의 `theme`과 각 활동의 `activity_description`을 사용자가 기대할 만한 매력적인 문장으로 작성해주세요.

**출력 JSON 구조:**
{{
  "itinerary": {{
    "title": "여행 일정 제목",
    "concept": "여행 컨셉 설명",
    "daily_plans": [
      {{
        "day": 1,
        "theme": "첫째 날 테마",
        "activities": [
          {{
            "time": "09:00 - 11:00",
            "place_name": "장소명",
            "activity_description": "활동 설명",
            "place_id": "선택한 장소의 place_id",
            "lat": 위도,
            "lng": 경도
          }}
        ]
      }}
    ]
  }}
}}"""
        try:
            # Dynamic AI Service 사용 → 1단계와 동일하게 AI 핸들러 사용
            handler = self._get_ai_handler()
            # [디버깅 로그 추가] AI에게 보낼 최종 프롬프트를 정확히 로깅
            logger.info(f"📜 [STEP_3_PROMPT] 3단계 AI에게 보낼 최종 프롬프트:\n{prompt2}")
            content = await handler.get_completion(prompt2)
            # [방어 코드 추가] AI 원본 응답을 먼저 로깅
            logger.info(f"🤖 [AI_RAW_RESPONSE] 3단계 AI 원본 응답: '{content}'")
            # [방어 코드 추가] 응답이 비어있는지 확인
            if not content or not content.strip():
                logger.error("❌ 3단계 AI 큐레이션 실패: AI가 빈 응답을 반환했습니다.")
                raise ValueError("AI returned an empty or whitespace-only response.")
            ai_response = json.loads(content)
            # [방어 코드 추가] 파싱된 결과가 유효한지 확인
            if not ai_response.get("itinerary"):
                logger.error("❌ 3단계 AI 큐레이션 실패: 파싱된 JSON에 'itinerary' 키가 없습니다.")
                raise ValueError("Parsed JSON from AI is missing the 'itinerary' key.")
            # 새로운 응답 구조 처리 (단일 itinerary)
            return ai_response
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"❌ 3단계 AI 큐레이션 실패: {e}", exc_info=False)
            # 기본 계획 반환
            return self._create_basic_plans(request, place_pool)
        except Exception as e:
            logger.error(f"3단계 AI 큐레이션 실패: {str(e)}")
            # 기본 계획 반환
            return self._create_basic_plans(request, place_pool)

    def _step4_json_assembly(
        self, 
        ai_plans: Dict[str, Any], 
        place_pool: List[Dict[str, Any]], 
        request_id: str
    ) -> GenerateResponse:
        """
        4단계: 최종 JSON 조립 및 반환
        """
        def create_travel_plan(plan_data: Dict[str, Any]) -> TravelPlan:
            daily_plans = []
            used_places = []
            
            for day_data in plan_data.get("daily_plans", []):
                activities = []
                for activity_data in day_data.get("activities", []):
                    activity = ActivityDetail(
                        time=activity_data.get("time", "09:00"),
                        place_name=activity_data.get("place_name", ""),
                        activity_description=activity_data.get("activity_description", ""),
                        transportation_details=activity_data.get("transportation_details", ""),
                        place_id=activity_data.get("place_id"),
                        lat=activity_data.get("lat"),
                        lng=activity_data.get("lng")
                    )
                    activities.append(activity)
                    
                    # 사용된 장소 추가
                    if activity_data.get("place_id"):
                        for place in place_pool:
                            if place.get("place_id") == activity_data.get("place_id"):
                                place_data = PlaceData(
                                    place_id=place.get("place_id", ""),
                                    name=place.get("name", ""),
                                    category=place.get("category", ""),
                                    lat=place.get("lat", 0.0),
                                    lng=place.get("lng", 0.0),
                                    rating=place.get("rating"),
                                    address=place.get("address"),
                                    description=place.get("description")
                                )
                                used_places.append(place_data)
                                break
                
                # ActivityDetail → ActivityItem 변환
                activities_item = [
                    ActivityItem(
                        time=getattr(a, "time", "09:00"),
                        activity=getattr(a, "activity_description", getattr(a, "place_name", "")),
                        location=getattr(a, "place_name", ""),
                        description=getattr(a, "activity_description", ""),
                        duration="2시간",  # 기본값 또는 추후 계산
                        cost=None,
                        tips=None
                    ) for a in activities
                ]
                day_plan = DayPlan(
                    day=day_data.get("day", 1),
                    theme=day_data.get("theme", ""),
                    activities=activities_item,
                    meals=day_data.get("meals", {"breakfast": "불포함", "lunch": "불포함", "dinner": "불포함"}),
                    transportation=day_data.get("transportation", ["도보"]),
                    estimated_cost=day_data.get("estimated_cost", "0원")
                )
                daily_plans.append(day_plan)
            
            return TravelPlan(
                title=plan_data.get("title", ""),
                concept=plan_data.get("concept", ""),
                daily_plans=daily_plans,
                places=used_places
            )
        
        # 단일 itinerary 구조 처리
        itinerary_data = ai_plans.get("itinerary", {})
        main_plan = create_travel_plan(itinerary_data)
        
        return GenerateResponse(
            plan_a=main_plan,
            plan_b=main_plan,  # 호환성을 위해 동일한 계획 제공
            request_id=request_id,
            generated_at=datetime.now().isoformat()
        )

    async def optimize_itinerary(self, request: OptimizeRequest) -> OptimizeResponse:
        """
        선택된 장소들을 구글 다이렉션 API로 최적화합니다
        """
        logger.info(f"경로 최적화 시작: {len(request.selected_places)}개 장소")
        
        try:
            # 장소 데이터를 구글 API 형식으로 변환
            places_for_optimization = []
            for place in request.selected_places:
                places_for_optimization.append({
                    "place_id": place.place_id,
                    "name": place.name,
                    "lat": place.lat,
                    "lng": place.lng,
                    "category": place.category
                })
            
            # 구글 다이렉션 API로 경로 최적화
            optimization_result = await self.google_places.optimize_route(
                places_for_optimization, 
                request.start_location
            )
            
            if not optimization_result:
                raise Exception("경로 최적화 실패")
            
            # 최적화된 순서로 일정 재구성
            optimized_places = optimization_result.get("optimized_places", [])
            optimized_plan = self._create_optimized_plan(optimized_places, request.duration)
            
            return OptimizeResponse(
                optimized_plan=optimized_plan,
                total_distance=optimization_result.get("total_distance"),
                total_duration=optimization_result.get("total_duration"),
                optimization_details=optimization_result
            )
            
        except Exception as e:
            logger.error(f"경로 최적화 실패: {str(e)}")
            # 실패 시 원래 순서 유지
            fallback_plan = self._create_optimized_plan(
                [place.dict() for place in request.selected_places], 
                request.duration
            )
            return OptimizeResponse(
                optimized_plan=fallback_plan,
                total_distance="계산 불가",
                total_duration="계산 불가",
                optimization_details={}
            )

    def _create_optimized_plan(self, places: List[Dict[str, Any]], duration: int) -> TravelPlan:
        """최적화된 장소들로 일정을 재구성합니다"""
        daily_plans = []
        places_per_day = max(1, len(places) // duration)
        
        for day in range(1, duration + 1):
            start_idx = (day - 1) * places_per_day
            end_idx = start_idx + places_per_day
            if day == duration:  # 마지막 날은 남은 모든 장소
                end_idx = len(places)
            
            day_places = places[start_idx:end_idx]
            activities = []
            
            for i, place in enumerate(day_places):
                time_slot = f"{9 + i * 2:02d}:00 - {11 + i * 2:02d}:00"
                activity = ActivityDetail(
                    time=time_slot,
                    place_name=place.get("name", ""),
                    activity_description=f"{place.get('name')}에서 여행을 즐겨보세요",
                    transportation_details="최적화된 경로로 이동",
                    place_id=place.get("place_id"),
                    lat=place.get("lat"),
                    lng=place.get("lng")
                )
                activities.append(activity)
            
            day_plan = DayPlan(
                day=day,
                theme=f"{day}일차 최적화된 일정",
                activities=activities
            )
            daily_plans.append(day_plan)
        
        # PlaceData 객체 생성
        place_data_list = []
        for place in places:
            place_data = PlaceData(
                place_id=place.get("place_id", ""),
                name=place.get("name", ""),
                category=place.get("category", ""),
                lat=place.get("lat", 0.0),
                lng=place.get("lng", 0.0),
                rating=place.get("rating"),
                address=place.get("address"),
                description=place.get("description")
            )
            place_data_list.append(place_data)
        
        return TravelPlan(
            title="나만의 맞춤 일정",
            concept="선택하신 장소들을 최적의 동선으로 재조합한 맞춤형 여행 계획",
            daily_plans=daily_plans,
            places=place_data_list
        )

    def _create_fallback_response(self, request: GenerateRequest, request_id: str) -> GenerateResponse:
        """AI 실패 시 기본 응답을 생성합니다"""
        # DayPlan의 필수 필드에 맞게 ActivityItem 타입 dict, meals, transportation, estimated_cost 모두 채움
        basic_activity = {
            "time": "09:00 - 12:00",
            "activity": "대표 관광지 방문",
            "location": f"{request.city} 대표 관광지",
            "description": "현지 주요 명소를 방문합니다",
            "duration": "3시간",
            "cost": None,
            "tips": None
        }
        basic_day = DayPlan(
            day=1,
            theme="기본 여행 일정",
            activities=[basic_activity],
            meals={},
            transportation=[],
            estimated_cost="0원"
        )
        basic_plan = TravelPlan(
            title=f"{request.city} 기본 여행",
            concept="기본적인 여행 계획",
            daily_plans=[basic_day],
            places=[]
        )
        fallback_response = GenerateResponse(
            plan_a=basic_plan,
            plan_b=basic_plan,
            request_id=request_id,
            generated_at=datetime.now().isoformat()
        )
        # fallback 응답에 status, error_message 속성 추가 (Pydantic 모델에 따라 setattr)
        try:
            setattr(fallback_response, 'status', 'fallback')
            setattr(fallback_response, 'error_message', "AI 응답 분석 실패로 기본 응답으로 대체되었습니다.")
        except Exception:
            pass
        return fallback_response

    def _create_basic_plans(self, request: GenerateRequest, place_pool: List[Dict[str, Any]]) -> Dict[str, Any]:
        """기본 계획을 생성합니다"""
        return {
            "itinerary": {
                "title": f"{request.city} 클래식 여행",
                "concept": "전통적인 관광 중심의 여행",
                "daily_plans": [
                    {
                        "day": 1,
                        "theme": "주요 관광지 탐방",
                        "activities": [
                            {
                                "time": "09:00 - 12:00",
                                "place_name": "관광지",
                                "activity_description": "주요 관광지 방문",
                                "transportation_details": "대중교통 이용"
                            }
                        ]
                    }
                ]
            },
            "plan_b": {
                "title": f"{request.city} 모던 여행",
                "concept": "현대적인 액티비티 중심의 여행",
                "daily_plans": [
                    {
                        "day": 1,
                        "theme": "트렌디한 장소 탐방",
                        "activities": [
                            {
                                "time": "09:00 - 12:00",
                                "place_name": "카페/맛집",
                                "activity_description": "현지 트렌드 체험",
                                "transportation_details": "대중교통 이용"
                            }
                        ]
                    }
                ]
            }
        } 