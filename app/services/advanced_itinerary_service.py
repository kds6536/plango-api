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
    TravelPlan, DayPlan, ActivityDetail, PlaceData, ActivityItem,
    ItineraryRequest, RecommendationResponse
)
from app.services.google_places_service import GooglePlacesService
from app.services.ai_handlers import OpenAIHandler, GeminiHandler
from app.utils.logger import get_logger
from app.services.enhanced_ai_service import enhanced_ai_service
from fastapi import HTTPException
from string import Template  # string.Template을 사용합니다.

logger = get_logger(__name__)


class AdvancedItineraryService:
    """고급 여행 일정 생성 서비스"""
    
    def __init__(self, ai_service=None, google_service=None):
        # 서비스 초기화
        from app.config import settings
        import openai
        import google.generativeai as genai
        self.settings = settings
        self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.gemini_client = genai if settings.GEMINI_API_KEY else None
        self.model_name_openai = getattr(settings, "openai_model", "gpt-3.5-turbo")
        self.model_name_gemini = getattr(settings, "gemini_model", "gemini-1.5-flash")
        self.google_places = google_service or GooglePlacesService()
        self.ai_service = ai_service
        logger.info("AdvancedItineraryService 초기화 완료 - AI 핸들러 패턴 적용")

    async def _get_ai_handler(self):
        """Enhanced AI Service를 통해 활성화된 AI 핸들러 가져오기"""
        try:
            return await enhanced_ai_service.get_active_handler()
        except Exception as e:
            logger.error(f"Enhanced AI handler 가져오기 실패: {e}")
            # 폴백으로 기존 방식 사용
            settings_dict = {
                "default_provider": "openai",
                "openai_model_name": "gpt-4",
                "gemini_model_name": "gemini-1.5-flash"
            }
            provider = settings_dict.get("default_provider", "openai").lower()
            openai_model = settings_dict.get("openai_model_name", "gpt-4")
            gemini_model = settings_dict.get("gemini_model_name", "gemini-1.5-flash")
            if provider == "gemini" and self.gemini_client:
                return GeminiHandler(self.gemini_client, gemini_model)
            else:
                return OpenAIHandler(self.openai_client, openai_model)

    async def generate_recommendations_with_details(self, request: ItineraryRequest) -> List[PlaceData]:
        """
        v6.0: 다중 목적지 지원 추천 생성
        """
        try:
            logger.info(f"v6.0 다중 목적지 추천 생성 시작: {len(request.destinations)}개 목적지")
            
            all_places = []
            
            for i, destination in enumerate(request.destinations):
                logger.info(f"목적지 {i+1} 처리: {destination.city}, {destination.country}")
                
                # 각 목적지별로 추천 생성
                destination_places = await self._generate_recommendations_for_destination(
                    destination, request, i+1
                )
                
                logger.info(f"목적지 {i+1} 결과: {len(destination_places)}개 장소")
                all_places.extend(destination_places)
            
            logger.info(f"총 {len(all_places)}개의 장소 추천 생성 완료")
            
            if not all_places:
                logger.warning("생성된 장소가 없습니다. 404 오류를 발생시킵니다.")
            
            return all_places
            
        except Exception as e:
            logger.error(f"추천 생성 중 오류: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    async def _generate_recommendations_for_destination(
        self, destination, request: ItineraryRequest, destination_index: int
    ) -> List[PlaceData]:
        """
        단일 목적지에 대한 추천 생성
        """
        try:
            # 기존 로직을 단일 도시용으로 변환
            city = destination.city
            country = destination.country
            
            logger.info(f"목적지 {destination_index} 처리 시작: {city}, {country}")
            
            # AI 브레인스토밍으로 키워드 생성
            logger.info(f"AI 브레인스토밍 시작: {city}")
            keywords_by_category = await self._step2_ai_brainstorming_v6(
                city, country, request, destination_index
            )
            logger.info(f"AI 브레인스토밍 완료: {city}, 키워드 수: {len(keywords_by_category) if keywords_by_category else 0}")
            
            # Google Places API로 장소 정보 강화
            logger.info(f"Google Places API 강화 시작: {city}")
            enhanced_places = await self._step3_enhance_places_v6(
                keywords_by_category, city, country, request.language_code
            )
            logger.info(f"Google Places API 강화 완료: {city}, 카테고리 수: {len(enhanced_places) if enhanced_places else 0}")
            
            # 결과 처리 및 필터링
            logger.info(f"결과 처리 및 필터링 시작: {city}")
            filtered_places = self._step4_process_and_filter_v6(enhanced_places)
            logger.info(f"결과 처리 및 필터링 완료: {city}, 카테고리 수: {len(filtered_places) if filtered_places else 0}")
            
            # PlaceData 형식으로 변환
            place_data_list = []
            for category, places in filtered_places.items():
                for place in places:
                    place_data = PlaceData(
                        place_id=place.get('place_id', ''),
                        name=place.get('name', ''),
                        category=category,
                        lat=place.get('lat', 0.0),
                        lng=place.get('lng', 0.0),
                        rating=place.get('rating'),
                        address=place.get('address'),
                        description=place.get('description', '')
                    )
                    place_data_list.append(place_data)
            
            logger.info(f"목적지 {destination_index} 처리 완료: {city}, 최종 장소 수: {len(place_data_list)}")
            return place_data_list
            
        except Exception as e:
            logger.error(f"목적지 {destination.city} 추천 생성 실패: {e}", exc_info=True)
            return []

    async def _step2_ai_brainstorming_v6(self, city: str, country: str, request: ItineraryRequest, destination_index: int):
        """
        v6.0: AI 브레인스토밍 - 다중 목적지 지원
        """
        try:
            logger.info(f"AI 브레인스토밍 시작: {city}, {country}")
            ai_handler = await self._get_ai_handler()
            logger.info(f"AI 핸들러 가져오기 완료: {type(ai_handler).__name__}")
            
            # 고정 프롬프트 규칙: 검색 전략은 search_strategy_v1, 일정 생성은 itinerary_generation
            from app.services.supabase_service import supabase_service
            prompt_template = await supabase_service.get_master_prompt('search_strategy_v1')
            logger.info("Supabase에서 search_strategy_v1 프롬프트 로드 완료")
            
            # 다중 목적지 컨텍스트 구성
            context = self._build_multi_destination_context(request, destination_index)
            
            prompt = Template(prompt_template).safe_substitute(
                city=city,
                country=country,
                total_duration=request.total_duration,
                travelers_count=request.travelers_count,
                budget_range=request.budget_range,
                travel_style=", ".join(request.travel_style) if request.travel_style else "없음",
                special_requests=request.special_requests or "없음",
                multi_destination_context=context
            )
            
            logger.info(f"AI 호출 시작: {city}")
            response = await ai_handler.get_completion(prompt)
            logger.info(f"AI 응답 수신: {city}, 응답 길이: {len(response) if response else 0}")
            
            # JSON 파싱
            try:
                result = json.loads(response)
                logger.info(f"AI 브레인스토밍 완료: {city}")
                return result
            except json.JSONDecodeError:
                logger.warning(f"JSON 파싱 실패, 텍스트 파싱으로 대체: {city}")
                return self._parse_text_to_keywords(response)
                
        except Exception as e:
            logger.error(f"AI 브레인스토밍 실패: {e}", exc_info=True)
            logger.info(f"폴백 키워드 사용: {city}")
            return self._get_fallback_keywords(city)

    def _build_multi_destination_context(self, request: ItineraryRequest, current_index: int) -> str:
        """
        다중 목적지 컨텍스트 구성
        """
        if len(request.destinations) <= 1:
            return ""
        
        context = f"\n다중 목적지 여행 정보 (총 {len(request.destinations)}개 목적지):"
        for i, dest in enumerate(request.destinations):
            marker = "→" if i < len(request.destinations) - 1 else "🏁"
            context += f"\n{i+1}. {dest.city} ({dest.country}) {marker}"
        
        context += f"\n현재 처리 중인 목적지: {current_index}번째"
        return context

    async def _step3_enhance_places_v6(self, keywords_by_category: Dict, city: str, country: str, language_code: str):
        """
        v6.0: Google Places API 정보 강화 - 다중 목적지 지원
        """
        logger.info(f"Google Places API 강화 시작: {city}, 카테고리 수: {len(keywords_by_category)}")
        enhanced_results = {}
        
        for category, keywords in keywords_by_category.items():
            logger.info(f"카테고리 '{category}' 처리: {len(keywords)}개 키워드")
            enhanced_results[category] = []
            
            for keyword in keywords:
                try:
                    logger.info(f"Google Places API 호출: {keyword} {city}")
                    # Google Places API 호출 (search_places_text 메서드 사용)
                    result = await self.google_places.search_places_text(
                        text_query=f"{keyword} {city}",
                        fields=["places.id", "places.displayName", "places.formattedAddress", "places.rating", "places.userRatingCount", "places.location"],
                        language_code=language_code
                    )
                    
                    places = []
                    if result and "places" in result:
                        for place in result["places"]:
                            place_data = {
                                "place_id": place.get("id"),
                                "name": place.get("displayName", {}).get("text"),
                                "address": place.get("formattedAddress"),
                                "rating": place.get("rating"),
                                "lat": place.get("location", {}).get("latitude", 0.0),
                                "lng": place.get("location", {}).get("longitude", 0.0),
                                "description": f"{keyword} 관련 장소"
                            }
                            places.append(place_data)
                    
                    if places:
                        logger.info(f"Google Places API 결과: {keyword} - {len(places)}개 장소")
                        enhanced_results[category].extend(places)
                    else:
                        logger.warning(f"Google Places API 결과 없음: {keyword}")
                        
                except Exception as e:
                    logger.error(f"Google Places API 호출 실패 ({category} - {keyword}): {e}")
                    continue
        
        logger.info(f"Google Places API 강화 완료: {city}, 카테고리별 결과: {[(k, len(v)) for k, v in enhanced_results.items()]}")
        return enhanced_results

    def _step4_process_and_filter_v6(self, place_results: Dict[str, List[Dict]], max_items: int = 5):
        """
        v6.0: 결과 처리 및 필터링 - 다중 목적지 지원
        """
        logger.info(f"결과 처리 및 필터링 시작: 카테고리 수 {len(place_results)}")
        filtered_results = {}
        
        for category, places in place_results.items():
            logger.info(f"카테고리 '{category}' 처리: {len(places)}개 장소")
            
            # 중복 제거 및 평점 기준 정렬
            unique_places = {}
            for place in places:
                place_id = place.get('place_id')
                if place_id and place_id not in unique_places:
                    unique_places[place_id] = place
            
            logger.info(f"카테고리 '{category}' 중복 제거 후: {len(unique_places)}개 장소")
            
            # 평점 기준으로 정렬 (평점이 높은 순)
            sorted_places = sorted(
                unique_places.values(),
                key=lambda x: x.get('rating', 0) or 0,
                reverse=True
            )
            
            # 상위 N개 선택
            filtered_results[category] = sorted_places[:max_items]
            logger.info(f"카테고리 '{category}' 최종 결과: {len(filtered_results[category])}개 장소")
        
        logger.info(f"결과 처리 및 필터링 완료: 카테고리별 결과 {[(k, len(v)) for k, v in filtered_results.items()]}")
        return filtered_results

    def _parse_text_to_keywords(self, text: str) -> Dict[str, List[str]]:
        """
        텍스트를 키워드로 파싱
        """
        # 간단한 파싱 로직
        categories = {
            "관광지": ["명소", "박물관", "역사"],
            "음식점": ["맛집", "레스토랑", "카페"],
            "활동": ["체험", "엔터테인먼트", "액티비티"],
            "숙박": ["호텔", "게스트하우스", "숙소"]
        }
        
        result = {}
        for category, keywords in categories.items():
            result[category] = keywords
        
        return result

    def _get_fallback_keywords(self, city: str) -> Dict[str, List[str]]:
        """
        폴백 키워드 반환
        """
        return {
            "관광지": [f"{city} 명소", f"{city} 박물관", f"{city} 역사"],
            "음식점": [f"{city} 맛집", f"{city} 레스토랑", f"{city} 카페"],
            "활동": [f"{city} 체험", f"{city} 엔터테인먼트", f"{city} 액티비티"],
            "숙박": [f"{city} 호텔", f"{city} 게스트하우스", f"{city} 숙소"]
        }

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
            # v5.1 로직으로 통합: generate_recommendations 호출
            logger.info("🚀 [PROCESS_REDIRECT] v5.1 추천 생성 로직으로 요청을 전달합니다.")
            
            language_code = getattr(request, 'language_code', 'ko')

            # [수정] generate_recommendations는 main_theme과 recommendations를 포함한 전체 dict를 반환합니다.
            recommendation_data = await self.generate_recommendations(request, language_code)
            
            # [수정] 더 이상 TravelPlan으로 변환하지 않고, 받은 데이터 구조를 그대로 반환합니다.
            # 이로 인해 라우터의 response_model도 변경 필요.
            return {
                "request_id": request_id,
                "generated_at": datetime.now().isoformat(),
                "main_theme": recommendation_data.get("main_theme"),
                "recommendations": recommendation_data.get("recommendations")
            }
            
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
        """Plango v5.1: 1~5단계 전체 추천 생성 프로세스"""
        try:
            # 2. 1차 AI 브레인스토밍
            logger.info("🧠 [STEP 2] 1차 AI 브레인스토밍 시작")
            # [수정] _step2는 main_theme과 recommendations 키를 모두 포함한 dict를 반환해야 합니다.
            ai_brainstorm_result = await self._step2_ai_brainstorming(request, language_code)
            ai_keywords = ai_brainstorm_result.get("recommendations", {})

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
            
            if not final_recommendations:
                logger.warning("모든 카테고리에서 최소 추천 개수를 만족하는 장소를 찾지 못해, 에러를 반환합니다.")
                raise HTTPException(
                    status_code=404, 
                    detail="AI가 추천할 만한 장소를 찾지 못했습니다. 요청사항을 좀 더 구체적으로 작성해보세요."
                )

            # [수정] main_theme과 최종 추천 목록을 함께 묶어 반환합니다.
            return {
                "main_theme": ai_brainstorm_result.get("main_theme"),
                "recommendations": final_recommendations
            }
        except Exception as e:
            logger.error(f"추천 생성 프로세스 실패: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="추천 생성 중 오류 발생")

    async def _step2_ai_brainstorming(self, request, language_code):
        """
        2단계: AI 브레인스토밍 - 장소 후보군 생성 (카테고리별 키워드 요청)
        """
        # [수정] 프롬프트 내용을 v5.1 최종 버전으로 교체합니다.
        prompt_template_str = """
당신은 'Plango AI'라는 이름의 세계 최고의 여행 컨설턴트입니다.
당신의 임무는 사용자의 요청을 분석하여, 4개의 지정된 카테고리에 맞춰 각각 **10개**의 **실제로 검색 가능하며 구체적인** 여행 키워드를 중요도 순서대로 제안하는 것입니다.

**## 지시사항 ##**
1.  **입력 분석:** '사용자 요청 정보'에 제공된 데이터를 완벽하게 분석합니다.
2.  **테마 설정:** 분석 내용을 바탕으로 전체 여행의 컨셉을 `main_theme` 값으로 정의합니다.
3.  **카테고리별 키워드 추출:** 아래 4개 카테고리 각각에 대해, 사용자 요청과 가장 관련성이 높은 키워드를 **10개씩** 제안합니다. 목록의 순서가 중요도 순서가 되도록 배치해주세요.
    -   `accommodations` (숙소): 호텔, 리조트, 펜션 등
    -   `attractions` (볼거리): 명소, 자연경관, 박물관 등
    -   `foods` (먹거리): 맛집, 유명 음식, 특색 있는 카페 등
    -   `activities` (즐길거리): 체험, 액티비티, 쇼핑 등
4.  **키워드 품질 관리:** 생성하는 모든 키워드는 **고유 명사, 지역적 특성, 또는 뚜렷한 특징을 포함**하여 Google 검색에서 쉽게 찾을 수 있도록 구체적으로 만들어야 합니다.

**## 출력 규칙 (매우 중요) ##**
-   응답은 **반드시** 아래 명시된 구조의 **단일 JSON 객체**여야 합니다.
-   **절대 "장소A", "맛집B", "호텔C" 와 같이 일반적이거나 추상적인 더미(dummy) 이름을 사용하지 마세요.**
-   JSON 객체 외에 어떠한 설명, 인사, 추가 텍스트도 포함하지 마세요.
-   Markdown 형식(```json ... ```)을 사용하지 마세요. 순수한 JSON 텍스트만 출력해야 합니다.

**## 최종 출력 JSON 구조 ##**
{
  "main_theme": "string",
  "recommendations": {
    "accommodations": [
      "string (1순위 키워드)",
      "string (2순위 키워드)",
      "string (3순위 키워드)",
      "string (4순위 키워드)",
      "string (5순위 키워드)",
      "string (6순위 키워드)",
      "string (7순위 키워드)",
      "string (8순위 키워드)",
      "string (9순위 키워드)",
      "string (10순위 키워드)"
    ],
    "attractions": [ ... 10 items ... ],
    "foods": [ ... 10 items ... ],
    "activities": [ ... 10 items ... ]
  }
}

**## 사용자 요청 정보 ##**
{user_request_json}
"""
        
        # 사용자 요청 정보를 JSON 문자열로 변환
        user_request_data = {
            "destination": request.city,
            "duration_days": request.duration,
            "budget": request.budget_range,
            "travelers_count": request.travelers_count,
            "travel_style": request.travel_style,
            "special_requests": request.special_requests
        }
        user_request_json = json.dumps(user_request_data, indent=2, ensure_ascii=False)
        
        # 프롬프트에 사용자 요청 정보 삽입
        prompt = prompt_template_str.format(user_request_json=user_request_json)
        
        try:
            handler = self._get_ai_handler()
            logger.info(f"📜 [STEP_2_PROMPT] 2단계 AI에게 보낼 최종 프롬프트:\n{prompt}")
            content = await handler.get_completion(prompt)
            logger.info(f"🤖 [AI_RAW_RESPONSE] 2단계 AI 원본 응답: '{content}'")
            
            if not content or not content.strip():
                logger.error("❌ 2단계 AI 브레인스토밍 실패: AI가 빈 응답을 반환했습니다.")
                raise ValueError("AI returned an empty or whitespace-only response.")
            
            ai_response = json.loads(content)
            
            # [수정] 검증 로직을 새로운 v5.1 구조에 맞게 변경
            if "recommendations" not in ai_response or not isinstance(ai_response["recommendations"], dict):
                raise ValueError("AI response is missing 'recommendations' dictionary.")

            required_categories = ["accommodations", "attractions", "foods", "activities"]
            if not all(k in ai_response["recommendations"] for k in required_categories):
                logger.error(f"❌ 2단계 AI 브레인스토밍 실패: 필수 카테고리가 누락되었습니다. 응답: {ai_response}")
                raise ValueError("AI response is missing one or more required categories.")

            # [수정] 키워드만 추출하는 대신, main_theme을 포함한 전체 응답을 반환합니다.
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

    def _convert_recommendations_to_travel_plan(self, request: GenerateRequest, recommendations: Dict[str, List[Dict]]) -> TravelPlan:
        """추천 목록(v5.0)을 TravelPlan(v4.0) 모델로 변환 (현재 사용되지 않음)"""
        all_places = []
        for category, places in recommendations.items():
            for place in places:
                all_places.append(PlaceData(
                    place_id=place.get("place_id", ""),
                    name=place.get("name", ""),
                    category=category,
                    lat=place.get("lat", 0.0),
                    lng=place.get("lng", 0.0),
                    rating=place.get("rating"),
                    address=place.get("address"),
                    description=place.get("description") # 이 필드가 없을 수 있음
                ))

        # place_pool을 사용하여 DayPlan 생성 (기존 로직 재활용 또는 단순화)
        # 여기서는 간단하게 모든 장소를 첫째 날에 넣는 것으로 단순화
        activities = []
        for place in all_places:
            activities.append(ActivityItem(
                time="미정",
                activity=place.name,
                location=place.address or place.name,
                description=place.description or f"{place.name} 방문",
                duration="1-2시간",
            ))

        daily_plan = DayPlan(
            day=1,
            theme=f"{request.city} 추천 장소 둘러보기",
            activities=activities,
            meals={"breakfast": "자유식", "lunch": "자유식", "dinner": "자유식"},
            transportation=["대중교통", "도보"],
            estimated_cost="사용자 예산에 따라 다름"
        )
        
        # 남은 일수만큼 비어있는 DayPlan 추가
        remaining_days = [
            DayPlan(day=i, theme="자유 일정", activities=[], meals={}, transportation=[], estimated_cost="-")
            for i in range(2, request.duration + 1)
        ]

        return TravelPlan(
            title=f"{request.city} AI 추천 여행",
            concept="AI가 추천한 핵심 장소들을 바탕으로 한 맞춤 여행 계획",
            daily_plans=[daily_plan] + remaining_days,
            places=all_places
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

    async def create_final_itinerary(self, places: List[PlaceData], constraints: Optional[Dict[str, Any]] = None) -> OptimizeResponse:
        """
        v6.0: 선택된 장소들을 Supabase 마스터 프롬프트와 AI로 최적화하여 최종 일정을 생성합니다.
        """
        try:
            logger.info(f"🎯 [OPTIMIZE] 최종 일정 생성 시작: {len(places)}개 장소")
            
            # 기본값/제약 설정
            constraints = constraints or {}
            duration = int(constraints.get("duration") or max(1, len(places) // 3))
            daily_start_time = constraints.get("daily_start_time") or "09:00"
            daily_end_time = constraints.get("daily_end_time") or "22:00"
            
            # v6.0: Enhanced AI Service를 사용한 마스터 프롬프트 기반 일정 생성
            try:
                # 사용자 데이터 구성
                user_data = {
                    "목적지": f"{places[0].address.split()[0] if places and places[0].address else '여행지'}",
                    "여행기간_일": duration,
                    "사용자_선택_장소": [
                        {
                            "장소_id": place.place_id,
                            "이름": place.name,
                            "타입": place.category or "관광",
                            "위도": place.lat or 0,
                            "경도": place.lng or 0,
                            "사전_그룹": 1  # 단순화된 그룹핑
                        }
                        for place in places
                    ]
                }
                
                logger.info("Enhanced AI Service로 일정 생성 시도")
                # 제약 정보를 AI에 전달하여 시간 규칙을 강화
                user_data["일일_시간_제약"] = {
                    "시작": daily_start_time,
                    "종료": daily_end_time,
                    "식사_규칙": {
                        "점심": "12:00-14:00 사이 1회",
                        "저녁": "18:00-20:00 사이 1회",
                        "카페": "15:00-17:00 우선 배치"
                    },
                    "숙소_규칙": "각 일자의 마지막은 숙소 배치, 다음날 첫 장소와 지리적으로 가까운 숙소 선호"
                }
                ai_response = await enhanced_ai_service.generate_itinerary_with_master_prompt(user_data)
                
                # AI 응답을 TravelPlan으로 변환
                optimized_plan = self._convert_ai_response_to_travel_plan(ai_response, places)
                
            except Exception as ai_error:
                logger.warning(f"AI 기반 일정 생성 실패, 폴백 사용: {ai_error}")
                # 폴백으로 간단한 일정 생성
                # 제약을 반영한 폴백 일정 생성
                optimized_plan = self._create_time_constrained_plan(places, duration, daily_start_time, daily_end_time)
            
            return OptimizeResponse(
                optimized_plan=optimized_plan,
                total_distance="약 50km",
                total_duration="약 2시간",
                optimization_details={
                    "algorithm": "enhanced_ai_master_prompt",
                    "places_count": len(places),
                    "days_count": duration,
                    "optimized": True,
                    "supabase_prompt": True,
                    "constraints": {
                        "daily_start_time": daily_start_time,
                        "daily_end_time": daily_end_time
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"최종 일정 생성 실패: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    def _create_optimized_travel_plan(self, places: List[PlaceData], duration: int) -> TravelPlan:
        """
        선택된 장소들을 최적화된 여행 계획으로 변환
        """
        # 장소들을 일자별로 분배
        places_per_day = max(1, len(places) // duration)
        daily_plans = []
        
        for day in range(duration):
            start_idx = day * places_per_day
            end_idx = min((day + 1) * places_per_day, len(places))
            day_places = places[start_idx:end_idx]
            
            if not day_places:
                continue
                
            # 활동 아이템 생성
            activities = []
            for i, place in enumerate(day_places):
                activities.append(ActivityItem(
                    time=f"{9 + i * 2}:00",
                    activity=f"{place.name} 방문",
                    location=place.address or place.name,
                    description=place.description or f"{place.name}에서 즐거운 시간을 보내세요",
                    duration="2시간",
                    cost="개인차이",
                    tips=f"{place.name} 방문 시 추천 포인트"
                ))
            
            daily_plans.append(DayPlan(
                day=day + 1,
                theme=f"Day {day + 1} 여행",
                activities=activities,
                meals={"점심": "현지 맛집", "저녁": "추천 레스토랑"},
                transportation=["도보", "대중교통"],
                estimated_cost=f"{50000 + day * 20000}원"
            ))
        
        return TravelPlan(
            title="AI 최적화 여행 일정",
            concept="선택하신 장소들을 최적의 동선으로 구성한 맞춤 여행 계획",
            daily_plans=daily_plans,
            places=places
        )

    def _create_time_constrained_plan(
        self,
        places: List[PlaceData],
        duration: int,
        daily_start: str,
        daily_end: str,
    ) -> TravelPlan:
        """시간 제약, 식사/숙소 배치 규칙을 적용한 간단한 휴리스틱 일정 생성"""
        # 카테고리 분류 (한글 카테고리 기준)
        foods = [p for p in places if (p.category or "").startswith("먹")]
        accommodations = [p for p in places if (p.category or "").startswith("숙")]
        others = [p for p in places if p not in foods and p not in accommodations]

        # 캐파 계산: 기본 2시간/장소 + 이동 0.5시간 가정
        def time_to_minutes(t: str) -> int:
            h, m = t.split(":")
            return int(h) * 60 + int(m)

        start_min = time_to_minutes(daily_start)
        end_min = time_to_minutes(daily_end)
        available_per_day = max(0, end_min - start_min)
        slot_per_day = max(1, (available_per_day // 150) - 2)  # 점심/저녁 2개 블록 고려

        daily_plans: List[DayPlan] = []
        place_cursor = 0

        # others를 우선 분배, 식사/숙소 규칙 삽입
        others_iter = iter(others)
        lunch_iter = iter(foods)
        dinner_iter = iter(foods)
        accom_iter = iter(accommodations)

        for day in range(1, duration + 1):
            activities: List[ActivityDetail] = []

            # 오전 블록: 시작부터 12:00 전까지 채우기
            current_time = start_min
            def add_activity(place: PlaceData, minutes: int, label: str = "관광"):
                nonlocal current_time, activities
                end_time_min = min(current_time + minutes, end_min)
                start_hh = f"{current_time // 60:02d}:{current_time % 60:02d}"
                activities.append(ActivityDetail(
                    time=f"{start_hh}",
                    place_name=place.name,
                    activity_description=f"{label}",
                    transportation_details="도보/대중교통",
                    place_id=place.place_id,
                    lat=place.lat,
                    lng=place.lng
                ))
                current_time = end_time_min + 30  # 기본 이동 30분

            # 오전 채우기
            while current_time + 120 <= min(end_min, time_to_minutes("12:00")) and slot_per_day > 0:
                try:
                    p = next(others_iter)
                except StopIteration:
                    break
                add_activity(p, 120)

            # 점심
            if current_time < time_to_minutes("14:00"):
                try:
                    p = next(lunch_iter)
                    current_time = max(current_time, time_to_minutes("12:00"))
                    add_activity(p, 60, label="점심")
                except StopIteration:
                    pass

            # 오후 블록 15~17 카페 우선은 foods에서 하나 더 사용
            if current_time < time_to_minutes("17:00"):
                try:
                    p = next(dinner_iter)
                    current_time = max(current_time, time_to_minutes("15:00"))
                    add_activity(p, 45, label="카페/디저트")
                except StopIteration:
                    pass

            # 저녁 전까지 관광 채우기
            while current_time + 120 <= min(end_min, time_to_minutes("18:00")):
                try:
                    p = next(others_iter)
                except StopIteration:
                    break
                add_activity(p, 120)

            # 저녁
            if current_time < time_to_minutes("20:00"):
                try:
                    p = next(dinner_iter)
                    current_time = max(current_time, time_to_minutes("18:00"))
                    add_activity(p, 60, label="저녁")
                except StopIteration:
                    pass

            # 숙소를 마지막에 배치
            try:
                p = next(accom_iter)
                if current_time + 45 <= end_min:
                    add_activity(p, 45, label="체크인/휴식")
            except StopIteration:
                pass

            daily_plans.append(DayPlan(
                day=day,
                theme=f"{day}일차 최적화 일정",
                activities=activities,
                meals={"lunch": "규칙 적용", "dinner": "규칙 적용"},
                transportation=["도보", "대중교통"],
                estimated_cost="-"
            ))

        # TravelPlan places는 입력 전체 유지
        return TravelPlan(
            title="시간 제약 최적화 일정",
            concept="시간 제약, 식사/숙소 규칙을 반영한 자동 구성 일정",
            daily_plans=daily_plans,
            places=places
        )
    
    def _convert_ai_response_to_travel_plan(self, ai_response: str, places: List[PlaceData]) -> TravelPlan:
        """
        AI 응답을 TravelPlan 객체로 변환
        """
        try:
            import json
            ai_data = json.loads(ai_response)
            
            # AI 응답에서 일정 정보 추출
            title = ai_data.get("여행_제목", "AI 생성 여행 일정")
            daily_plans = []
            
            for day_info in ai_data.get("일정", []):
                activities = []
                
                # 시간표를 ActivityItem으로 변환
                for schedule_item in day_info.get("시간표", []):
                    activities.append(ActivityItem(
                        time=schedule_item.get("시작시간", "09:00"),
                        activity=schedule_item.get("활동", "활동"),
                        location=schedule_item.get("장소명", "장소"),
                        description=schedule_item.get("설명", ""),
                        duration=f"{schedule_item.get('소요시간_분', 60)}분",
                        cost="개인차이",
                        tips=schedule_item.get("설명", "")
                    ))
                
                # DayPlan 생성
                daily_plans.append(DayPlan(
                    day=day_info.get("일차", 1),
                    theme=day_info.get("일일_테마", "여행"),
                    activities=activities,
                    meals={"점심": "현지 맛집", "저녁": "추천 레스토랑"},
                    transportation=["도보", "대중교통"],
                    estimated_cost="개인차이"
                ))
            
            return TravelPlan(
                title=title,
                concept="AI가 최적화한 맞춤형 여행 계획",
                daily_plans=daily_plans,
                places=places
            )
            
        except Exception as e:
            logger.error(f"AI 응답 변환 실패: {e}")
            # 폴백으로 기본 계획 반환
            return self._create_optimized_travel_plan(places, len(places) // 3 or 1) 