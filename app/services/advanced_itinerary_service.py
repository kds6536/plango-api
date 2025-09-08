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
    TravelPlan, DayPlan, ActivityDetail, PlaceData,
    ItineraryRequest, RecommendationResponse
)
from app.services.google_places_service import GooglePlacesService
from app.services.google_directions_service import GoogleDirectionsService
from app.utils.logger import get_logger
from fastapi import HTTPException
from string import Template  # string.Template을 사용합니다.

# 조건부 import로 오류 방지
try:
    from app.services.ai_handlers import OpenAIHandler, GeminiHandler
except ImportError as e:
    print(f"Warning: Could not import AI handlers: {e}")
    OpenAIHandler = None
    GeminiHandler = None

try:
    from app.services.enhanced_ai_service import enhanced_ai_service
except ImportError:
    enhanced_ai_service = None

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
        self.google_directions = GoogleDirectionsService()  # Google Directions API 서비스 추가
        self.ai_service = ai_service
        logger.info("AdvancedItineraryService 초기화 완료 - AI 핸들러 패턴 적용")

    async def _get_ai_handler(self):
        """Enhanced AI Service를 통해 활성화된 AI 핸들러 가져오기"""
        logger.info("🔍🔍🔍 [GET_AI_HANDLER_START] AI 핸들러 생성 프로세스 시작")
        print("🔍🔍🔍 [GET_AI_HANDLER_START] AI 핸들러 생성 프로세스 시작")
        
        # ===== 1단계: Enhanced AI Service 시도 =====
        try:
            logger.info("📊 [STEP_1] Enhanced AI Service 확인")
            print("📊 [STEP_1] Enhanced AI Service 확인")
            
            logger.info(f"📊 [ENHANCED_SERVICE_CHECK] enhanced_ai_service 존재: {enhanced_ai_service is not None}")
            logger.info(f"📊 [ENHANCED_SERVICE_TYPE] enhanced_ai_service 타입: {type(enhanced_ai_service)}")
            print(f"📊 [ENHANCED_SERVICE_CHECK] enhanced_ai_service 존재: {enhanced_ai_service is not None}")
            
            if enhanced_ai_service:
                logger.info("🔄 [ENHANCED_CALL] enhanced_ai_service.get_active_handler() 호출 시작")
                print("🔄 [ENHANCED_CALL] enhanced_ai_service.get_active_handler() 호출 시작")
                
                handler = await enhanced_ai_service.get_active_handler()
                
                logger.info(f"✅ [ENHANCED_SUCCESS] Enhanced AI handler 가져오기 성공: {type(handler).__name__ if handler else 'None'}")
                print(f"✅ [ENHANCED_SUCCESS] Enhanced AI handler 가져오기 성공: {type(handler).__name__ if handler else 'None'}")
                
                if handler:
                    logger.info("🎉 [HANDLER_READY] Enhanced AI handler 준비 완료")
                    print("🎉 [HANDLER_READY] Enhanced AI handler 준비 완료")
                    return handler
                else:
                    logger.warning("⚠️ [ENHANCED_NULL] Enhanced AI handler가 None을 반환했습니다")
                    print("⚠️ [ENHANCED_NULL] Enhanced AI handler가 None을 반환했습니다")
            else:
                logger.info("ℹ️ [NO_ENHANCED] enhanced_ai_service가 None입니다. 폴백으로 이동")
                print("ℹ️ [NO_ENHANCED] enhanced_ai_service가 None입니다. 폴백으로 이동")
                
        except Exception as e:
            logger.error(f"❌ [ENHANCED_ERROR] Enhanced AI handler 가져오기 실패: {e}")
            logger.error(f"📊 [ERROR_TYPE] 에러 타입: {type(e).__name__}")
            logger.error(f"📊 [ERROR_MSG] 에러 메시지: {str(e)}")
            logger.error(f"📊 [ERROR_TRACEBACK] 상세 트레이스백:", exc_info=True)
            print(f"❌ [ENHANCED_ERROR] Enhanced AI handler 가져오기 실패: {e}")
        
        # ===== 2단계: 폴백 방식 사용 =====
        logger.info("🔄 [FALLBACK_START] 폴백 AI 핸들러 생성 시작")
        print("🔄 [FALLBACK_START] 폴백 AI 핸들러 생성 시작")
        
        try:
            logger.info("📊 [STEP_2] 폴백 설정 구성")
            print("📊 [STEP_2] 폴백 설정 구성")
            
            settings_dict = {
                "default_provider": "openai",
                "openai_model_name": "gpt-4",
                "gemini_model_name": "gemini-1.5-flash"
            }
            
            provider = settings_dict.get("default_provider", "openai").lower()
            openai_model = settings_dict.get("openai_model_name", "gpt-4")
            gemini_model = settings_dict.get("gemini_model_name", "gemini-1.5-flash")
            
            logger.info(f"📊 [FALLBACK_CONFIG] 선택된 제공자: {provider}")
            logger.info(f"📊 [FALLBACK_CONFIG] OpenAI 모델: {openai_model}")
            logger.info(f"📊 [FALLBACK_CONFIG] Gemini 모델: {gemini_model}")
            print(f"📊 [FALLBACK_CONFIG] 선택된 제공자: {provider}")
            
            # 클라이언트 상태 확인
            logger.info(f"📊 [CLIENT_CHECK] self.openai_client 존재: {self.openai_client is not None}")
            logger.info(f"📊 [CLIENT_CHECK] self.gemini_client 존재: {self.gemini_client is not None}")
            logger.info(f"📊 [CLIENT_CHECK] OpenAIHandler 클래스 존재: {OpenAIHandler is not None}")
            logger.info(f"📊 [CLIENT_CHECK] GeminiHandler 클래스 존재: {GeminiHandler is not None}")
            print(f"📊 [CLIENT_CHECK] OpenAI 클라이언트: {self.openai_client is not None}, Gemini 클라이언트: {self.gemini_client is not None}")
            
            # 핸들러 생성 시도
            if provider == "gemini" and self.gemini_client and GeminiHandler:
                logger.info("🔄 [GEMINI_HANDLER] Gemini 핸들러 생성 시도")
                print("🔄 [GEMINI_HANDLER] Gemini 핸들러 생성 시도")
                
                handler = GeminiHandler(self.gemini_client, gemini_model)
                
                logger.info(f"✅ [GEMINI_SUCCESS] Gemini 핸들러 생성 성공: {type(handler).__name__}")
                print(f"✅ [GEMINI_SUCCESS] Gemini 핸들러 생성 성공")
                return handler
                
            elif self.openai_client and OpenAIHandler:
                logger.info("🔄 [OPENAI_HANDLER] OpenAI 핸들러 생성 시도")
                print("🔄 [OPENAI_HANDLER] OpenAI 핸들러 생성 시도")
                
                handler = OpenAIHandler(self.openai_client, openai_model)
                
                logger.info(f"✅ [OPENAI_SUCCESS] OpenAI 핸들러 생성 성공: {type(handler).__name__}")
                print(f"✅ [OPENAI_SUCCESS] OpenAI 핸들러 생성 성공")
                return handler
                
            else:
                logger.error("❌ [NO_VALID_CLIENT] 유효한 AI 클라이언트나 핸들러 클래스를 찾을 수 없습니다")
                logger.error(f"📊 [CLIENT_DETAILS] OpenAI 클라이언트: {self.openai_client is not None}")
                logger.error(f"📊 [CLIENT_DETAILS] Gemini 클라이언트: {self.gemini_client is not None}")
                logger.error(f"📊 [HANDLER_DETAILS] OpenAIHandler: {OpenAIHandler is not None}")
                logger.error(f"📊 [HANDLER_DETAILS] GeminiHandler: {GeminiHandler is not None}")
                print("❌ [NO_VALID_CLIENT] 유효한 AI 클라이언트를 찾을 수 없습니다")
                return None
                
        except Exception as fallback_error:
            logger.error(f"❌ [FALLBACK_ERROR] 폴백 AI 핸들러 생성 실패: {fallback_error}")
            logger.error(f"📊 [FALLBACK_ERROR_TYPE] 에러 타입: {type(fallback_error).__name__}")
            logger.error(f"📊 [FALLBACK_ERROR_MSG] 에러 메시지: {str(fallback_error)}")
            logger.error(f"📊 [FALLBACK_ERROR_TRACEBACK] 상세 트레이스백:", exc_info=True)
            print(f"❌ [FALLBACK_ERROR] 폴백 AI 핸들러 생성 실패: {fallback_error}")
            return None

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
                logger.warning("생성된 장소가 없습니다. 기본 장소를 생성합니다.")
                # 기본 장소 생성
                default_places = await self._create_default_places(request.destinations[0] if request.destinations else None)
                all_places.extend(default_places)
            
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
                        description=place.get('description', ''),
                        website=place.get('website', '') or place.get('website_url', '')  # 웹사이트 정보 추가
                    )
                    place_data_list.append(place_data)
            
            logger.info(f"목적지 {destination_index} 처리 완료: {city}, 최종 장소 수: {len(place_data_list)}")
            return place_data_list

        except Exception as e:
            logger.error(f"목적지 {destination_index} 처리 중 오류: {e}")
            # 오류 발생 시 기본 장소 반환
            return await self._create_default_places_for_destination(destination)

    async def _create_default_places(self, destination) -> List[PlaceData]:
        """기본 장소 생성 (데이터가 없을 때 사용)"""
        if not destination:
            return []
        
        return await self._create_default_places_for_destination(destination)

    async def _create_default_places_for_destination(self, destination) -> List[PlaceData]:
        """특정 목적지에 대한 기본 장소 생성"""
        try:
            city = destination.city
            country = destination.country
            
            default_places = [
                PlaceData(
                    place_id=f"default_tourism_{city}",
                    name=f"{city} 중심가",
                    category="관광",
                    lat=0.0,
                    lng=0.0,
                    rating=4.0,
                    address=f"{city}, {country}",
                    description=f"{city}의 주요 관광지입니다."
                ),
                PlaceData(
                    place_id=f"default_food_{city}",
                    name=f"{city} 현지 음식점",
                    category="음식",
                    lat=0.0,
                    lng=0.0,
                    rating=4.2,
                    address=f"{city}, {country}",
                    description=f"{city}의 대표적인 현지 음식을 맛볼 수 있는 곳입니다."
                ),
                PlaceData(
                    place_id=f"default_activity_{city}",
                    name=f"{city} 문화 체험",
                    category="액티비티",
                    lat=0.0,
                    lng=0.0,
                    rating=4.1,
                    address=f"{city}, {country}",
                    description=f"{city}에서 즐길 수 있는 문화 체험 활동입니다."
                )
            ]
            
            logger.info(f"기본 장소 {len(default_places)}개 생성: {city}")
            return default_places
            
        except Exception as e:
            logger.error(f"기본 장소 생성 실패: {e}")
            return []

    async def _step2_ai_brainstorming_v6(self, city: str, country: str, request: ItineraryRequest, destination_index: int) -> Dict[str, List[str]]:
        """AI 브레인스토밍으로 카테고리별 키워드 생성"""
        try:
            logger.info(f"AI 브레인스토밍 시작: {city}, {country}")
            
            # AI 서비스 사용 (더 간단한 방법)
            try:
                from app.services.dynamic_ai_service import DynamicAIService
                ai_service = DynamicAIService()
            except Exception as ai_import_error:
                logger.error(f"AI 서비스 import 실패: {ai_import_error}")
                return self._get_default_keywords(city, country)
            
            # 브레인스토밍 프롬프트 구성
            prompt = f"""
다음 도시에 대한 여행 장소를 카테고리별로 추천해주세요:

도시: {city}, {country}
여행 기간: {getattr(request, 'total_duration', 3)}일
여행자 수: {getattr(request, 'travelers_count', 2)}명
예산: {getattr(request, 'budget_range', 'medium')}
여행 스타일: {', '.join(getattr(request, 'travel_style', ['문화', '관광']))}

다음 4개 카테고리별로 각각 5-10개의 구체적인 장소명을 추천해주세요:

1. 관광 (tourist attractions, landmarks, museums)
2. 음식 (restaurants, cafes, local food)
3. 액티비티 (activities, entertainment, experiences)
4. 숙박 (hotels, accommodations)

JSON 형식으로 응답해주세요:
{{
    "관광": ["장소명1", "장소명2", ...],
    "음식": ["장소명1", "장소명2", ...],
    "액티비티": ["장소명1", "장소명2", ...],
    "숙박": ["장소명1", "장소명2", ...]
}}
"""
            
            # AI 호출
            response = await ai_service.generate_text(prompt, max_tokens=1000)
            
            if response:
                # JSON 파싱 시도
                try:
                    import json
                    # JSON 추출
                    json_start = response.find('{')
                    json_end = response.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        json_str = response[json_start:json_end]
                        keywords = json.loads(json_str)
                        logger.info(f"AI 브레인스토밍 성공: {len(keywords)}개 카테고리")
                        return keywords
                except Exception as parse_error:
                    logger.error(f"AI 응답 파싱 실패: {parse_error}")
            
            # 실패 시 기본 키워드 반환
            return self._get_default_keywords(city, country)
            
        except Exception as e:
            logger.error(f"AI 브레인스토밍 실패: {e}")
            return self._get_default_keywords(city, country)

    def _get_default_keywords(self, city: str, country: str) -> Dict[str, List[str]]:
        """기본 키워드 생성"""
        return {
            "관광": [f"{city} 관광명소", f"{city} 박물관", f"{city} 랜드마크", f"{city} 문화유산"],
            "음식": [f"{city} 맛집", f"{city} 현지음식", f"{city} 카페", f"{city} 레스토랑"],
            "액티비티": [f"{city} 체험", f"{city} 액티비티", f"{city} 엔터테인먼트", f"{city} 쇼핑"],
            "숙박": [f"{city} 호텔", f"{city} 숙박", f"{city} 게스트하우스", f"{city} 리조트"]
        }

    async def _step3_enhance_places_v6(self, keywords_by_category: Dict[str, List[str]], city: str, country: str, language_code: str = "ko") -> Dict[str, List[Dict[str, Any]]]:
        """Google Places API로 장소 정보 강화"""
        try:
            logger.info(f"Google Places API 강화 시작: {city}")
            
            enhanced_places = {}
            
            for category, keywords in keywords_by_category.items():
                category_places = []
                
                for keyword in keywords[:3]:  # 각 카테고리당 상위 3개 키워드만 사용
                    try:
                        # Google Places API 검색
                        places = await self.google_places.search_places(
                            query=keyword,
                            location=f"{city}, {country}",
                            language_code=language_code
                        )
                        
                        # 결과 추가 (중복 제거)
                        for place in places[:5]:  # 키워드당 최대 5개
                            if not any(p.get('place_id') == place.get('place_id') for p in category_places):
                                category_places.append(place)
                        
                    except Exception as search_error:
                        logger.warning(f"키워드 '{keyword}' 검색 실패: {search_error}")
                        continue
                
                enhanced_places[category] = category_places
                logger.info(f"카테고리 '{category}': {len(category_places)}개 장소 발견")
            
            return enhanced_places
            
        except Exception as e:
            logger.error(f"Google Places API 강화 실패: {e}")
            return {}

    def _step4_process_and_filter_v6(self, enhanced_places: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """결과 처리 및 필터링"""
        try:
            filtered_places = {}
            
            for category, places in enhanced_places.items():
                # 평점 기준 정렬
                sorted_places = sorted(
                    places, 
                    key=lambda x: (x.get('rating', 0), x.get('user_ratings_total', 0)), 
                    reverse=True
                )
                
                # 상위 10개 선택
                filtered_places[category] = sorted_places[:10]
                
                logger.info(f"카테고리 '{category}': {len(filtered_places[category])}개 장소 필터링 완료")
            
            return filtered_places
            
        except Exception as e:
            logger.error(f"결과 처리 및 필터링 실패: {e}")
            return enhanced_places  # 실패 시 원본 반환

    async def create_final_itinerary(self, places: List[PlaceData], constraints: Dict[str, Any] = None) -> OptimizeResponse:
        """최종 일정 생성"""
        try:
            logger.info("=" * 100)
            logger.info("🚀 [ADVANCED_ITINERARY_SERVICE] AdvancedItineraryService.create_final_itinerary 호출됨!")
            logger.info("🚀 [CREATE_FINAL_START] 최종 일정 생성 시작")
            logger.info(f"📍 [INPUT_PLACES] 입력 장소 수: {len(places)}")
            logger.info(f"📋 [INPUT_CONSTRAINTS] 제약 조건: {constraints}")
            
            # ===== 🚨 [핵심] 입력된 장소들의 상세 정보 로깅 - 안전한 접근 방식 =====
            logger.info("🔍🔍🔍 [DETAILED_PLACES_INFO] 입력된 장소들의 상세 정보:")
            print("🔍🔍🔍 [DETAILED_PLACES_INFO] 입력된 장소들의 상세 정보:")
            
            for i, place in enumerate(places):
                try:
                    logger.info(f"  🔍 [{i+1}] 장소 타입: {type(place)}")
                    print(f"  🔍 [{i+1}] 장소 타입: {type(place)}")
                    
                    # 딕셔너리인 경우
                    if isinstance(place, dict):
                        name = place.get('name', 'Unknown')
                        category = place.get('category', 'Unknown')
                        lat = place.get('lat', 0.0)
                        lng = place.get('lng', 0.0)
                        address = place.get('address', 'Unknown')
                        place_info = f"[{i+1}] {name} - 카테고리: {category}, 위도: {lat}, 경도: {lng}, 주소: {address}"
                    # PlaceData 객체인 경우
                    elif hasattr(place, 'name'):
                        place_info = f"[{i+1}] {place.name} - 카테고리: {place.category}, 위도: {place.lat}, 경도: {place.lng}, 주소: {place.address}"
                    # 문자열인 경우 (이름만)
                    elif isinstance(place, str):
                        place_info = f"[{i+1}] {place} - (문자열 데이터, 위도/경도 없음)"
                    else:
                        place_info = f"[{i+1}] 알 수 없는 데이터 타입: {type(place)} - {str(place)}"
                    
                    logger.info(f"  📍 {place_info}")
                    print(f"  📍 {place_info}")
                    
                except Exception as e:
                    logger.error(f"  ❌ [{i+1}] 장소 정보 접근 실패: {e}")
                    logger.error(f"  📊 [{i+1}] 장소 원본 데이터: {place}")
                    print(f"  ❌ [{i+1}] 장소 정보 접근 실패: {e}")
                    print(f"  📊 [{i+1}] 장소 원본 데이터: {place}")
            
            logger.info("🔍🔍🔍 [DETAILED_PLACES_INFO_END]")
            print("🔍🔍🔍 [DETAILED_PLACES_INFO_END]")
            
            # ===== 🚨 [핵심] 입력 데이터 타입 검증 =====
            logger.info("🔍 [DATA_TYPE_CHECK] 입력 데이터 타입 검증 시작")
            logger.info(f"📊 [PLACES_TYPE] places 타입: {type(places)}")
            logger.info(f"📊 [PLACES_LENGTH] places 길이: {len(places) if places else 0}")
            
            if places and len(places) > 0:
                logger.info(f"📊 [FIRST_PLACE_TYPE] 첫 번째 장소 타입: {type(places[0])}")
                logger.info(f"📊 [FIRST_PLACE_CONTENT] 첫 번째 장소 내용: {places[0]}")
                
                # 첫 번째 장소의 키들 확인
                if hasattr(places[0], '__dict__'):
                    logger.info(f"📊 [FIRST_PLACE_ATTRS] 첫 번째 장소 속성들: {list(places[0].__dict__.keys())}")
                elif isinstance(places[0], dict):
                    logger.info(f"📊 [FIRST_PLACE_KEYS] 첫 번째 장소 키들: {list(places[0].keys())}")
                else:
                    logger.info(f"📊 [FIRST_PLACE_INFO] 첫 번째 장소는 dict도 객체도 아님: {str(places[0])}")
            
            logger.info(f"📊 [CONSTRAINTS_TYPE] constraints 타입: {type(constraints)}")
            logger.info(f"📊 [CONSTRAINTS_KEYS] constraints 키들: {list(constraints.keys()) if isinstance(constraints, dict) else 'Not a dict'}")
            logger.info("=" * 100)
            
            # ===== 🚨 [핵심 수정] PlaceData 객체 안전한 접근 =====
            place_names = []
            try:
                for i, place in enumerate(places):
                    try:
                        # PlaceData는 Pydantic 모델이므로 직접 속성 접근 가능
                        place_name = f"{place.name} ({place.category})"
                        place_names.append(place_name)
                        logger.info(f"  📍 [{i+1}] {place_name}")
                        
                    except Exception as place_error:
                        logger.error(f"❌ [PLACE_ACCESS_ERROR] 장소 {i+1} 접근 실패: {place_error}")
                        logger.error(f"📊 [PLACE_ERROR_TYPE] 에러 타입: {type(place_error).__name__}")
                        logger.error(f"📊 [PLACE_ERROR_MSG] 에러 메시지: {str(place_error)}")
                        place_names.append(f"Error_Place_{i+1}")
                
                logger.info(f"🏛️ [PLACE_LIST_SUCCESS] 장소 목록 생성 완료: {len(place_names)}개")
                
            except Exception as places_error:
                logger.error(f"❌ [PLACES_PROCESSING_ERROR] 장소 목록 처리 실패: {places_error}")
                logger.error(f"📊 [ERROR_TRACEBACK] 전체 트레이스백:", exc_info=True)
            
            if not constraints:
                constraints = {
                    "daily_start_time": "09:00",
                    "daily_end_time": "22:00",
                    "duration": max(1, len(places) // 3)
                }
            
            duration = constraints.get("duration", 3)
            daily_start = constraints.get("daily_start_time", "09:00")
            daily_end = constraints.get("daily_end_time", "22:00")
            
            logger.info(f"⏰ [SCHEDULE_PARAMS] 일정 매개변수: {duration}일, {daily_start}~{daily_end}")
            
            # ===== 🚨 [핵심] AI 핸들러 생성 및 검증 =====
            logger.info("🤖🤖🤖 [AI_HANDLER_PROCESS] AI 핸들러 생성 프로세스 시작")
            print("🤖🤖🤖 [AI_HANDLER_PROCESS] AI 핸들러 생성 프로세스 시작")
            
            ai_handler = await self._get_ai_handler()
            
            logger.info("🔍 [HANDLER_VALIDATION] AI 핸들러 검증 시작")
            print("🔍 [HANDLER_VALIDATION] AI 핸들러 검증 시작")
            
            if not ai_handler:
                logger.error("❌❌❌ [AI_HANDLER_FAIL] AI 핸들러를 가져올 수 없습니다")
                logger.error("📊 [HANDLER_NULL] ai_handler가 None입니다")
                print("❌❌❌ [AI_HANDLER_FAIL] AI 핸들러를 가져올 수 없습니다")
                
                logger.info("🔄 [FALLBACK] 간단한 일정 생성으로 폴백")
                print("🔄 [FALLBACK] 간단한 일정 생성으로 폴백")
                return self._create_simple_itinerary(places, duration, daily_start, daily_end)
            
            logger.info(f"✅✅✅ [AI_HANDLER_SUCCESS] AI 핸들러 준비 완료")
            logger.info(f"📊 [HANDLER_TYPE] 핸들러 타입: {type(ai_handler).__name__}")
            logger.info(f"📊 [HANDLER_METHODS] 핸들러 메서드들: {[method for method in dir(ai_handler) if not method.startswith('_')]}")
            print(f"✅✅✅ [AI_HANDLER_SUCCESS] AI 핸들러 준비 완료: {type(ai_handler).__name__}")
            
            # 핸들러의 generate_text 메서드 존재 확인
            if hasattr(ai_handler, 'generate_text'):
                logger.info("✅ [METHOD_CHECK] generate_text 메서드 존재 확인")
                print("✅ [METHOD_CHECK] generate_text 메서드 존재 확인")
            else:
                logger.error("❌ [METHOD_MISSING] generate_text 메서드가 존재하지 않습니다")
                logger.error(f"📊 [AVAILABLE_METHODS] 사용 가능한 메서드들: {[method for method in dir(ai_handler) if not method.startswith('_')]}")
                print("❌ [METHOD_MISSING] generate_text 메서드가 존재하지 않습니다")
                return self._create_simple_itinerary(places, duration, daily_start, daily_end)
            
            # ===== 🚨 [핵심 수정] 프롬프트 생성 과정을 별도 try-catch로 감싸기 =====
            prompt = None
            try:
                logger.info("📜 [PROMPT_CREATION_START] 최종 프롬프트 생성을 시작합니다")
                print("📜 [PROMPT_CREATION_START] 최종 프롬프트 생성을 시작합니다")
                
                # ===== 🚨 [단계별 디버깅] 각 단계마다 로깅 =====
                logger.info("🔍 [STEP_1] Supabase 프롬프트 템플릿 가져오기 시작")
                print("🔍 [STEP_1] Supabase 프롬프트 템플릿 가져오기 시작")
                
                # ===== 🚨 [핵심 수정] Supabase 프롬프트 로드를 더 안전하게 =====
                prompt_template = None
                try:
                    logger.info("📜 [PROMPT_FETCH] Supabase 서비스 import 시작")
                    print("📜 [PROMPT_FETCH] Supabase 서비스 import 시작")
                    
                    # import 과정을 더 세밀하게 로깅
                    logger.info("📜 [IMPORT_STEP_1] supabase_service import 시도")
                    print("📜 [IMPORT_STEP_1] supabase_service import 시도")
                    
                    from app.services.supabase_service import supabase_service
                    
                    logger.info("✅ [IMPORT_SUCCESS] Supabase 서비스 import 성공")
                    print("✅ [IMPORT_SUCCESS] Supabase 서비스 import 성공")
                    
                    # supabase_service 객체 상태 확인
                    logger.info(f"📊 [SERVICE_CHECK] supabase_service 타입: {type(supabase_service)}")
                    logger.info(f"📊 [SERVICE_CHECK] supabase_service 존재: {supabase_service is not None}")
                    print(f"📊 [SERVICE_CHECK] supabase_service 타입: {type(supabase_service)}")
                    
                    logger.info("📜 [PROMPT_FETCH] get_master_prompt 호출 시작")
                    print("📜 [PROMPT_FETCH] get_master_prompt 호출 시작")
                    
                    # 실제 호출 전에 메서드 존재 확인
                    if hasattr(supabase_service, 'get_master_prompt'):
                        logger.info("✅ [METHOD_CHECK] get_master_prompt 메서드 존재 확인")
                        print("✅ [METHOD_CHECK] get_master_prompt 메서드 존재 확인")
                        
                        logger.info("📜 [ACTUAL_CALL] 실제 get_master_prompt 호출 시작")
                        print("📜 [ACTUAL_CALL] 실제 get_master_prompt 호출 시작")
                        
                        prompt_template = await supabase_service.get_master_prompt('itinerary_generation')
                        
                        logger.info(f"✅ [PROMPT_FETCH_SUCCESS] Supabase 프롬프트 로드 성공")
                        logger.info(f"📊 [PROMPT_LENGTH] 프롬프트 길이: {len(prompt_template) if prompt_template else 0}")
                        logger.info(f"📊 [PROMPT_TYPE] 프롬프트 타입: {type(prompt_template)}")
                        print(f"✅ [PROMPT_FETCH_SUCCESS] Supabase 프롬프트 로드 성공 (길이: {len(prompt_template) if prompt_template else 0})")
                        
                        # 프롬프트 내용 미리보기
                        if prompt_template:
                            preview = prompt_template[:200] + "..." if len(prompt_template) > 200 else prompt_template
                            logger.info(f"📝 [PROMPT_PREVIEW] 프롬프트 미리보기: {preview}")
                        
                    else:
                        logger.error("❌ [METHOD_NOT_FOUND] get_master_prompt 메서드가 존재하지 않습니다")
                        print("❌ [METHOD_NOT_FOUND] get_master_prompt 메서드가 존재하지 않습니다")
                        raise AttributeError("get_master_prompt 메서드가 존재하지 않음")
                    
                except Exception as prompt_error:
                    logger.error("❌ [PROMPT_FETCH_FAIL] Supabase 프롬프트 로드 실패")
                    logger.error(f"📊 [ERROR_TYPE] 에러 타입: {type(prompt_error).__name__}")
                    logger.error(f"📊 [ERROR_MSG] 에러 메시지: {str(prompt_error)}")
                    logger.error(f"📊 [ERROR_TRACEBACK] 상세 트레이스백:", exc_info=True)
                    
                    print(f"❌ [PROMPT_FETCH_FAIL] Supabase 프롬프트 로드 실패: {prompt_error}")
                    print(f"📊 [ERROR_TYPE] 에러 타입: {type(prompt_error).__name__}")
                    
                    logger.info("🔄 [FALLBACK_PROMPT] 기본 프롬프트 사용")
                    print("🔄 [FALLBACK_PROMPT] 기본 프롬프트 사용")
                    prompt_template = self._get_default_itinerary_prompt()
                
                # 프롬프트 템플릿 최종 검증
                if not prompt_template or not prompt_template.strip():
                    logger.error("❌ [EMPTY_TEMPLATE] 프롬프트 템플릿이 비어있습니다")
                    print("❌ [EMPTY_TEMPLATE] 프롬프트 템플릿이 비어있습니다")
                    logger.info("🔄 [EMERGENCY_FALLBACK] 긴급 기본 프롬프트 사용")
                    print("🔄 [EMERGENCY_FALLBACK] 긴급 기본 프롬프트 사용")
                    prompt_template = self._get_default_itinerary_prompt()
                
                logger.info(f"✅ [TEMPLATE_READY] 프롬프트 템플릿 준비 완료 (길이: {len(prompt_template)})")
                print(f"✅ [TEMPLATE_READY] 프롬프트 템플릿 준비 완료 (길이: {len(prompt_template)})")
                
                logger.info("🔍 [STEP_2] 장소 정보 구성 시작")
                print("🔍 [STEP_2] 장소 정보 구성 시작")
                
                # ===== 🚨 [핵심 수정] PlaceData 객체 정보 구성 - JSON 변환 테스트 포함 =====
                logger.info("📍 [PLACES_INFO] 장소 정보 구성 시작 (위도/경도 포함)")
                print("📍 [PLACES_INFO] 장소 정보 구성 시작 (위도/경도 포함)")
                
                # ===== 🚨 [핵심 추가] JSON 변환 테스트 - 에러 원인 찾기 =====
                logger.info("🧪 [JSON_TEST_START] PlaceData 객체 JSON 변환 테스트 시작")
                print("🧪 [JSON_TEST_START] PlaceData 객체 JSON 변환 테스트 시작")
                
                try:
                    # 각 PlaceData 객체를 dict로 변환 테스트
                    places_dict_list = []
                    for i, place in enumerate(places):
                        try:
                            logger.info(f"🧪 [JSON_TEST_{i+1}] 장소 {i+1} JSON 변환 테스트: {place.name}")
                            print(f"🧪 [JSON_TEST_{i+1}] 장소 {i+1} JSON 변환 테스트: {place.name}")
                            
                            # PlaceData를 dict로 변환 시도
                            if hasattr(place, 'dict'):
                                place_dict = place.dict()
                                logger.info(f"✅ [DICT_SUCCESS_{i+1}] place.dict() 성공")
                            elif hasattr(place, '__dict__'):
                                place_dict = place.__dict__
                                logger.info(f"✅ [DICT_SUCCESS_{i+1}] place.__dict__ 사용")
                            else:
                                place_dict = {
                                    'name': place.name,
                                    'category': place.category,
                                    'lat': place.lat,
                                    'lng': place.lng,
                                    'address': place.address
                                }
                                logger.info(f"✅ [DICT_SUCCESS_{i+1}] 수동 dict 생성")
                            
                            # JSON 직렬화 테스트
                            json_test = json.dumps(place_dict, ensure_ascii=False)
                            logger.info(f"✅ [JSON_SUCCESS_{i+1}] JSON 직렬화 성공 (길이: {len(json_test)})")
                            places_dict_list.append(place_dict)
                            
                        except Exception as json_test_error:
                            logger.error(f"❌ [JSON_TEST_FAIL_{i+1}] 장소 {i+1} JSON 변환 실패: {json_test_error}")
                            logger.error(f"📊 [JSON_ERROR_TYPE_{i+1}] 에러 타입: {type(json_test_error).__name__}")
                            logger.error(f"📊 [JSON_ERROR_MSG_{i+1}] 에러 메시지: {str(json_test_error)}")
                            logger.error(f"📊 [JSON_ERROR_TRACEBACK_{i+1}]", exc_info=True)
                            print(f"❌ [JSON_TEST_FAIL_{i+1}] 장소 {i+1} JSON 변환 실패: {json_test_error}")
                            
                            # 실패한 객체의 상세 정보
                            logger.error(f"📊 [FAILED_OBJECT_{i+1}] 실패한 객체 타입: {type(place)}")
                            logger.error(f"📊 [FAILED_OBJECT_{i+1}] 실패한 객체 속성: {dir(place)}")
                            if hasattr(place, '__dict__'):
                                logger.error(f"📊 [FAILED_OBJECT_{i+1}] __dict__ 내용: {place.__dict__}")
                            
                            # 폴백 dict 생성
                            fallback_dict = {
                                'name': f'Error_Place_{i+1}',
                                'category': 'Unknown',
                                'lat': 0.0,
                                'lng': 0.0,
                                'address': 'Error accessing place data'
                            }
                            places_dict_list.append(fallback_dict)
                    
                    # 전체 places 리스트 JSON 변환 테스트
                    logger.info("🧪 [FULL_JSON_TEST] 전체 places 리스트 JSON 변환 테스트")
                    print("🧪 [FULL_JSON_TEST] 전체 places 리스트 JSON 변환 테스트")
                    
                    full_json_test = json.dumps(places_dict_list, ensure_ascii=False)
                    logger.info(f"✅ [FULL_JSON_SUCCESS] 전체 JSON 변환 성공 (길이: {len(full_json_test)})")
                    print(f"✅ [FULL_JSON_SUCCESS] 전체 JSON 변환 성공 (길이: {len(full_json_test)})")
                    
                    # constraints dict JSON 변환 테스트
                    logger.info("🧪 [CONSTRAINTS_JSON_TEST] constraints JSON 변환 테스트")
                    print("🧪 [CONSTRAINTS_JSON_TEST] constraints JSON 변환 테스트")
                    
                    constraints_json_test = json.dumps(constraints, ensure_ascii=False)
                    logger.info(f"✅ [CONSTRAINTS_JSON_SUCCESS] constraints JSON 변환 성공 (길이: {len(constraints_json_test)})")
                    print(f"✅ [CONSTRAINTS_JSON_SUCCESS] constraints JSON 변환 성공")
                    
                except Exception as json_test_global_error:
                    logger.error("❌❌❌ [JSON_TEST_GLOBAL_FAIL] 전체 JSON 테스트 실패")
                    logger.error(f"📊 [GLOBAL_ERROR_TYPE] 에러 타입: {type(json_test_global_error).__name__}")
                    logger.error(f"📊 [GLOBAL_ERROR_MSG] 에러 메시지: {str(json_test_global_error)}")
                    logger.error(f"📊 [GLOBAL_ERROR_TRACEBACK]", exc_info=True)
                    print(f"❌❌❌ [JSON_TEST_GLOBAL_FAIL] 전체 JSON 테스트 실패: {json_test_global_error}")
                    
                    # JSON 변환 실패 시 즉시 폴백
                    logger.info("🔄 [JSON_FAIL_IMMEDIATE_FALLBACK] JSON 변환 실패로 즉시 폴백")
                    print("🔄 [JSON_FAIL_IMMEDIATE_FALLBACK] JSON 변환 실패로 즉시 폴백")
                    return self._create_simple_itinerary(places, duration, daily_start, daily_end)
                
                logger.info("✅ [JSON_TEST_COMPLETE] JSON 변환 테스트 완료 - 모든 객체 변환 가능")
                print("✅ [JSON_TEST_COMPLETE] JSON 변환 테스트 완료 - 모든 객체 변환 가능")
                
                # 기존 places_info 구성 로직
                places_info = []
                for i, place in enumerate(places):
                    try:
                        # PlaceData는 Pydantic 모델이므로 직접 속성 접근
                        place_name = place.name
                        place_category = place.category
                        place_address = place.address or 'Unknown Address'
                        place_lat = place.lat if hasattr(place, 'lat') else 0.0
                        place_lng = place.lng if hasattr(place, 'lng') else 0.0
                        
                        # ===== 🚨 [핵심] 위도/경도 정보를 포함한 장소 정보 생성 =====
                        place_info = f"- {place_name} ({place_category}): {place_address} [위도: {place_lat}, 경도: {place_lng}]"
                        places_info.append(place_info)
                        
                        logger.info(f"  📍 [{i+1}] {place_name} - 위도: {place_lat}, 경도: {place_lng}")
                        print(f"  📍 [{i+1}] {place_name} - 위도: {place_lat}, 경도: {place_lng}")
                        
                        # 위도/경도 유효성 검증
                        if place_lat == 0.0 and place_lng == 0.0:
                            logger.warning(f"⚠️ [MISSING_COORDS] {place_name}의 위도/경도가 0,0입니다")
                            print(f"⚠️ [MISSING_COORDS] {place_name}의 위도/경도가 0,0입니다")
                        
                    except Exception as place_info_error:
                        logger.error(f"❌ [PLACE_INFO_ERROR] 장소 {i+1} 정보 구성 실패: {place_info_error}")
                        logger.error(f"📊 [PLACE_INFO_ERROR_TYPE] 에러 타입: {type(place_info_error).__name__}")
                        logger.error(f"📊 [PLACE_INFO_ERROR_MSG] 에러 메시지: {str(place_info_error)}")
                        print(f"❌ [PLACE_INFO_ERROR] 장소 {i+1} 정보 구성 실패: {place_info_error}")
                        
                        # 에러 발생 시 기본값 사용
                        fallback_info = f"- Place_{i+1} (Unknown): Error accessing place data [위도: 0.0, 경도: 0.0]"
                        places_info.append(fallback_info)
                        logger.info(f"  📍 [{i+1}] {fallback_info} (fallback)")
                        print(f"  📍 [{i+1}] {fallback_info} (fallback)")
                
                logger.info(f"✅ [PLACES_INFO_SUCCESS] {len(places_info)}개 장소 정보 구성 완료")
                print(f"✅ [PLACES_INFO_SUCCESS] {len(places_info)}개 장소 정보 구성 완료")
                
                # 날짜별 시간 제약 조건 처리
                logger.info("🔍 [STEP_3] 시간 제약 조건 처리 시작")
                print("🔍 [STEP_3] 시간 제약 조건 처리 시작")
                time_constraints_info = ""
                if constraints.get("time_constraints"):
                    time_constraints_info = "\n날짜별 시간 제약 조건:"
                    for tc in constraints["time_constraints"]:
                        day = tc.get("day", 1)
                        start = tc.get("startTime", daily_start)
                        end = tc.get("endTime", daily_end)
                        time_constraints_info += f"\n- {day}일차: {start} ~ {end}"
                    logger.info(f"⏰ [TIME_CONSTRAINTS] 개별 시간 제약: {constraints['time_constraints']}")
                else:
                    time_constraints_info = f"\n전체 일정 시간: {daily_start} ~ {daily_end}"
                    logger.info(f"⏰ [TIME_CONSTRAINTS] 전체 시간 제약: {daily_start} ~ {daily_end}")
                
                logger.info("✅ [TIME_CONSTRAINTS_SUCCESS] 시간 제약 조건 처리 완료")
                print("✅ [TIME_CONSTRAINTS_SUCCESS] 시간 제약 조건 처리 완료")
                
                # 프롬프트 템플릿 변수 치환
                logger.info("🔍 [STEP_4] 프롬프트 템플릿 변수 치환 시작")
                print("🔍 [STEP_4] 프롬프트 템플릿 변수 치환 시작")
                logger.info("📜 [TEMPLATE_IMPORT] string.Template import 시작")
                print("📜 [TEMPLATE_IMPORT] string.Template import 시작")
                
                from string import Template
                logger.info("✅ [TEMPLATE_IMPORT_SUCCESS] Template import 성공")
                print("✅ [TEMPLATE_IMPORT_SUCCESS] Template import 성공")
                
                logger.info("📜 [TEMPLATE_CREATE] Template 객체 생성 시작")
                print("📜 [TEMPLATE_CREATE] Template 객체 생성 시작")
                
                template = Template(prompt_template)
                logger.info("✅ [TEMPLATE_CREATE_SUCCESS] Template 객체 생성 성공")
                print("✅ [TEMPLATE_CREATE_SUCCESS] Template 객체 생성 성공")
                
                # 변수 치환 전에 각 변수 값 로깅
                logger.info("📊 [TEMPLATE_VARS] 템플릿 변수 값 확인:")
                logger.info(f"  - places_list 길이: {len(places_info)}")
                logger.info(f"  - duration: {duration}")
                logger.info(f"  - daily_start_time: {daily_start}")
                logger.info(f"  - daily_end_time: {daily_end}")
                logger.info(f"  - total_places: {len(places)}")
                logger.info(f"  - time_constraints_info 길이: {len(time_constraints_info)}")
                
                print("📊 [TEMPLATE_VARS] 템플릿 변수 값 확인 완료")
                
                logger.info("📜 [TEMPLATE_SUBSTITUTE] safe_substitute 호출 시작")
                print("📜 [TEMPLATE_SUBSTITUTE] safe_substitute 호출 시작")
                
                prompt = template.safe_substitute(
                    places_list=chr(10).join(places_info),
                    duration=duration,
                    daily_start_time=daily_start,
                    daily_end_time=daily_end,
                    total_places=len(places),
                    time_constraints_info=time_constraints_info
                )
                
                logger.info("✅ [TEMPLATE_SUBSTITUTE_SUCCESS] safe_substitute 성공")
                print("✅ [TEMPLATE_SUBSTITUTE_SUCCESS] safe_substitute 성공")
                
                logger.info("✅ [PROMPT_CREATION_SUCCESS] 최종 프롬프트 생성 완료")
                logger.info(f"📊 [FINAL_PROMPT_LENGTH] 최종 프롬프트 길이: {len(prompt)} 문자")
                
            except Exception as prompt_creation_error:
                # 프롬프트 생성 과정에서 발생한 정확한 에러를 로깅
                logger.error("❌ [PROMPT_CREATION_FAIL] 최종 프롬프트 생성 중 심각한 오류 발생")
                logger.error(f"🚨 [ERROR_TYPE] 에러 타입: {type(prompt_creation_error).__name__}")
                logger.error(f"📝 [ERROR_MESSAGE] 에러 메시지: {str(prompt_creation_error)}")
                logger.error(f"📊 [ERROR_TRACEBACK] 전체 트레이스백:", exc_info=True)
                
                # 프롬프트 생성 실패 시 폴백으로 간단한 일정 생성
                logger.info("🔄 [PROMPT_FAIL_FALLBACK] 프롬프트 생성 실패로 인한 폴백")
                return self._create_simple_itinerary(places, duration, daily_start, daily_end)
            
            # 프롬프트가 성공적으로 생성되었는지 최종 확인
            if not prompt or not prompt.strip():
                logger.error("❌ [EMPTY_PROMPT] 프롬프트가 비어있습니다")
                logger.info("🔄 [EMPTY_PROMPT_FALLBACK] 빈 프롬프트로 인한 폴백")
                return self._create_simple_itinerary(places, duration, daily_start, daily_end)
            
            # ===== 🚨 [핵심] AI에게 전달되는 최종 프롬프트 완전 로깅 =====
            logger.info("📜 [COMPLETE_PROMPT_DEBUG] AI에게 전달되는 최종 프롬프트 전체:")
            logger.info("=" * 100)
            logger.info(f"📊 [PROMPT_LENGTH] 프롬프트 총 길이: {len(prompt)} 문자")
            logger.info("📝 [COMPLETE_PROMPT_CONTENT] AI에게 전달되는 최종 프롬프트 전체 내용:")
            logger.info(prompt)
            logger.info("=" * 100)
            logger.info("📜 [COMPLETE_PROMPT_DEBUG] 최종 프롬프트 로깅 완료")
            
            # 추가로 print도 사용하여 확실히 출력되도록 함
            print("📜 [COMPLETE_PROMPT_DEBUG] AI에게 전달되는 최종 프롬프트 전체:")
            print("=" * 100)
            print(f"📊 [PROMPT_LENGTH] 프롬프트 총 길이: {len(prompt)} 문자")
            print("📝 [COMPLETE_PROMPT_CONTENT] AI에게 전달되는 최종 프롬프트 전체 내용:")
            print(prompt)
            print("=" * 100)
            print("📜 [COMPLETE_PROMPT_DEBUG] 최종 프롬프트 로깅 완료")
            
            # ===== 🚨 [핵심] AI 호출 과정 완전 추적 =====
            logger.info("🤖🤖🤖 [AI_CALL_PROCESS] AI 호출 프로세스 시작")
            print("🤖🤖🤖 [AI_CALL_PROCESS] AI 호출 프로세스 시작")
            
            # AI 호출 직전 최종 상태 확인
            logger.info("🔍 [PRE_CALL_CHECK] AI 호출 직전 상태 확인")
            logger.info(f"📊 [HANDLER_STATUS] ai_handler 타입: {type(ai_handler).__name__}")
            logger.info(f"📊 [PROMPT_STATUS] prompt 길이: {len(prompt)} 문자")
            logger.info(f"📊 [PROMPT_STATUS] prompt 비어있음: {not prompt or not prompt.strip()}")
            print("🔍 [PRE_CALL_CHECK] AI 호출 직전 상태 확인 완료")
            
            try:
                logger.info("🚀 [ACTUAL_AI_CALL] 실제 AI generate_text 호출 시작")
                print("🚀 [ACTUAL_AI_CALL] 실제 AI generate_text 호출 시작")
                
                # 호출 파라미터 로깅
                logger.info("📊 [CALL_PARAMS] 호출 파라미터:")
                logger.info(f"  - max_tokens: 2000")
                logger.info(f"  - prompt 첫 100자: {prompt[:100]}...")
                print("📊 [CALL_PARAMS] max_tokens=2000으로 AI 호출")
                
                # 실제 AI 호출
                response = await ai_handler.generate_text(prompt, max_tokens=2000)
                
                logger.info("✅ [AI_CALL_RETURNED] AI 호출이 반환되었습니다")
                logger.info(f"📊 [RESPONSE_INITIAL_CHECK] 응답 타입: {type(response)}")
                logger.info(f"📊 [RESPONSE_INITIAL_CHECK] 응답 길이: {len(response) if response else 0}")
                logger.info(f"📊 [RESPONSE_INITIAL_CHECK] 응답이 None: {response is None}")
                logger.info(f"📊 [RESPONSE_INITIAL_CHECK] 응답이 빈 문자열: {response == '' if response is not None else 'N/A'}")
                
                print(f"✅ [AI_CALL_RETURNED] AI 호출 완료 (응답 길이: {len(response) if response else 0})")
                
                if response:
                    logger.info(f"📝 [RESPONSE_PREVIEW] 응답 미리보기 (첫 200자): {response[:200]}...")
                else:
                    logger.warning("⚠️ [EMPTY_RESPONSE] AI가 빈 응답을 반환했습니다")
                    print("⚠️ [EMPTY_RESPONSE] AI가 빈 응답을 반환했습니다")
                
            except Exception as ai_error:
                logger.error("❌❌❌ [AI_CALL_EXCEPTION] AI 호출 중 예외 발생")
                logger.error(f"📊 [AI_ERROR_TYPE] 예외 타입: {type(ai_error).__name__}")
                logger.error(f"📊 [AI_ERROR_MSG] 예외 메시지: {str(ai_error)}")
                logger.error(f"📊 [AI_ERROR_TRACEBACK] 상세 트레이스백:", exc_info=True)
                
                print(f"❌❌❌ [AI_CALL_EXCEPTION] AI 호출 실패: {ai_error}")
                print(f"📊 [AI_ERROR_TYPE] 예외 타입: {type(ai_error).__name__}")
                
                # 특정 에러 타입별 추가 정보
                if hasattr(ai_error, 'response'):
                    logger.error(f"📊 [API_RESPONSE] API 응답: {ai_error.response}")
                if hasattr(ai_error, 'status_code'):
                    logger.error(f"📊 [STATUS_CODE] 상태 코드: {ai_error.status_code}")
                
                logger.info("🔄 [AI_ERROR_FALLBACK] AI 호출 실패로 인한 폴백")
                print("🔄 [AI_ERROR_FALLBACK] AI 호출 실패로 인한 폴백")
                return self._create_simple_itinerary(places, duration, daily_start, daily_end)
            
            # ===== 🚨 [핵심 수정] AI 응답 검증 및 파싱 강화 =====
            if not response or not response.strip():
                logger.error("❌ [AI_EMPTY_RESPONSE] AI가 빈 응답을 반환했습니다")
                logger.info("🔄 [FALLBACK] 간단한 일정 생성으로 폴백")
                return self._create_simple_itinerary(places, duration, daily_start, daily_end)
            
            # ===== 🚨 [핵심] AI 원본 응답 완전 로깅 =====
            logger.info("🤖 [AI_RAW_RESPONSE_DEBUG] AI 원본 응답 전체:")
            logger.info("=" * 100)
            logger.info(f"📊 [RESPONSE_TYPE] 응답 타입: {type(response)}")
            logger.info(f"📊 [RESPONSE_LENGTH] 응답 길이: {len(response) if response else 0}")
            logger.info("📝 [COMPLETE_RESPONSE_CONTENT] AI 원본 응답 전체 내용:")
            logger.info(response if response else "None 또는 빈 응답")
            logger.info("=" * 100)
            logger.info("🤖 [AI_RAW_RESPONSE_DEBUG] AI 원본 응답 로깅 완료")
            
            # 추가로 print도 사용
            print("🤖 [AI_RAW_RESPONSE_DEBUG] AI 원본 응답 전체:")
            print("=" * 100)
            print(f"📊 [RESPONSE_TYPE] 응답 타입: {type(response)}")
            print(f"📊 [RESPONSE_LENGTH] 응답 길이: {len(response) if response else 0}")
            print("📝 [COMPLETE_RESPONSE_CONTENT] AI 원본 응답 전체 내용:")
            print(response if response else "None 또는 빈 응답")
            print("=" * 100)
            print("🤖 [AI_RAW_RESPONSE_DEBUG] AI 원본 응답 로깅 완료")
            
            try:
                import json
                logger.info("🔧 [JSON_PARSING] JSON 파싱 시작")
                
                # JSON 추출 개선 - 여러 패턴 시도
                json_str = None
                
                # 패턴 1: 일반적인 JSON 블록
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    logger.info(f"🔧 [JSON_PATTERN_1] 일반 JSON 패턴 발견 (길이: {len(json_str)})")
                else:
                    # 패턴 2: 코드 블록 내 JSON
                    import re
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                        logger.info(f"🔧 [JSON_PATTERN_2] 코드 블록 JSON 패턴 발견 (길이: {len(json_str)})")
                    else:
                        # 패턴 3: 마크다운 없는 JSON
                        json_match = re.search(r'(\{[^{}]*"travel_plan"[^{}]*\{.*?\}.*?\})', response, re.DOTALL)
                        if json_match:
                            json_str = json_match.group(1)
                            logger.info(f"🔧 [JSON_PATTERN_3] travel_plan 키워드 기반 JSON 발견 (길이: {len(json_str)})")
                
                if not json_str:
                    logger.error("❌ [JSON_EXTRACTION_FAIL] 모든 패턴에서 JSON 추출 실패")
                    raise ValueError("JSON 추출 실패")
                
                logger.info(f"📝 [JSON_PREVIEW] JSON 미리보기 (처음 500자): {json_str[:500]}...")
                
                # JSON 파싱 시도
                try:
                    itinerary_data = json.loads(json_str)
                    logger.info("✅ [JSON_PARSE_SUCCESS] JSON 파싱 성공")
                    logger.info(f"📊 [PARSED_KEYS] 파싱된 최상위 키들: {list(itinerary_data.keys())}")
                except json.JSONDecodeError as json_error:
                    logger.error(f"❌ [JSON_DECODE_ERROR] JSON 디코딩 실패: {json_error}")
                    logger.error(f"📝 [FAILED_JSON_SAMPLE] 실패한 JSON 샘플: {json_str[:200]}...")
                    raise ValueError(f"JSON 디코딩 실패: {json_error}")
                
                # ===== 🚨 [핵심 수정] AI 응답 구조 유연 처리 =====
                logger.info(f"🔍 [AI_RESPONSE_KEYS] AI 응답 최상위 키들: {list(itinerary_data.keys())}")
                
                # 여러 가능한 키를 순서대로 확인하여 실제 일정 데이터를 찾는다
                travel_plan = None
                days_data = []
                
                # 1순위: 'travel_plan' 키 확인
                if "travel_plan" in itinerary_data:
                    travel_plan = itinerary_data["travel_plan"]
                    days_data = travel_plan.get("days", [])
                    logger.info("✅ [FOUND_TRAVEL_PLAN] 'travel_plan' 키 발견")
                
                # 2순위: 'itinerary' 키 확인 (AI가 자주 사용하는 키)
                elif "itinerary" in itinerary_data:
                    itinerary_list = itinerary_data["itinerary"]
                    if isinstance(itinerary_list, list):
                        days_data = itinerary_list
                        # travel_plan 구조로 변환
                        travel_plan = {
                            "total_days": len(days_data),
                            "daily_start_time": "09:00",
                            "daily_end_time": "22:00",
                            "days": days_data
                        }
                        logger.info("✅ [FOUND_ITINERARY] 'itinerary' 키 발견하여 travel_plan으로 변환")
                    else:
                        logger.warning("⚠️ [INVALID_ITINERARY] 'itinerary' 키가 배열이 아닙니다")
                
                # 3순위: 'daily_plans' 키 확인
                elif "daily_plans" in itinerary_data:
                    days_data = itinerary_data["daily_plans"]
                    travel_plan = {
                        "total_days": len(days_data),
                        "daily_start_time": "09:00", 
                        "daily_end_time": "22:00",
                        "days": days_data
                    }
                    logger.info("✅ [FOUND_DAILY_PLANS] 'daily_plans' 키 발견하여 travel_plan으로 변환")
                
                # 4순위: 최상위가 배열인 경우 (직접 일정 데이터)
                elif isinstance(itinerary_data, list):
                    days_data = itinerary_data
                    travel_plan = {
                        "total_days": len(days_data),
                        "daily_start_time": "09:00",
                        "daily_end_time": "22:00", 
                        "days": days_data
                    }
                    logger.info("✅ [FOUND_ARRAY] 최상위 배열을 travel_plan으로 변환")
                
                # 모든 키를 찾지 못한 경우
                if not travel_plan or not days_data:
                    logger.error(f"❌ [NO_VALID_STRUCTURE] AI 응답에서 유효한 일정 구조를 찾을 수 없습니다")
                    logger.error(f"📝 [AVAILABLE_KEYS] 사용 가능한 키들: {list(itinerary_data.keys())}")
                    raise ValueError("AI 응답에서 유효한 일정 구조를 찾을 수 없음")
                logger.info(f"🔍 [DAYS_CHECK] days 배열 길이: {len(days_data)}")
                
                if not days_data or len(days_data) == 0:
                    logger.error("❌ [EMPTY_DAYS] AI 응답의 days 배열이 비어있습니다")
                    raise ValueError("days 배열이 비어있음")
                
                # 각 날짜별 활동 검증
                total_activities = 0
                for i, day_data in enumerate(days_data):
                    activities = day_data.get("activities", [])
                    activity_count = len(activities)
                    total_activities += activity_count
                    logger.info(f"🔍 [DAY_{i+1}_ACTIVITIES] {i+1}일차 활동 수: {activity_count}")
                    
                    if activity_count == 0:
                        logger.warning(f"⚠️ [EMPTY_DAY] {i+1}일차에 활동이 없습니다")
                
                logger.info(f"🔍 [TOTAL_ACTIVITIES] 전체 활동 수: {total_activities}")
                
                # 🚨 [핵심] 모든 날짜가 비어있는 경우 에러 발생
                if total_activities == 0:
                    logger.error("❌ [ALL_DAYS_EMPTY] AI가 유효한 일정을 생성하지 못했습니다 (모든 날짜의 활동이 비어있음)")
                    raise ValueError("AI가 빈 일정을 반환했습니다")
                
                # DayPlan 객체들 생성
                logger.info("🏗️ [BUILD_DAY_PLANS] DayPlan 객체 생성 시작")
                day_plans = []
                for day_data in days_data:
                    activities = []
                    for activity_data in day_data.get("activities", []):
                        activity = ActivityDetail(
                            time=activity_data.get("time", "09:00"),
                            place_name=activity_data.get("place_name", ""),
                            category=activity_data.get("category", "관광"),
                            duration_minutes=activity_data.get("duration_minutes", 120),
                            description=activity_data.get("description", "")
                        )
                        activities.append(activity)
                    
                    day_plan = DayPlan(
                        day=day_data.get("day", 1),
                        date=day_data.get("date", "2024-01-01"),
                        activities=activities
                    )
                    day_plans.append(day_plan)
                
                logger.info(f"✅ [BUILD_DAY_PLANS_SUCCESS] {len(day_plans)}개 DayPlan 객체 생성 완료")
                
                # ===== 🚗 실제 이동 시간 계산 추가 =====
                logger.info("🚗 [DIRECTIONS_API_START] Google Directions API로 이동 시간 재계산 시작")
                day_plans = await self._calculate_real_travel_times(day_plans, places)
                logger.info("🚗 [DIRECTIONS_API_SUCCESS] 실제 이동 시간 계산 완료")
                
                final_plan = TravelPlan(
                    total_days=travel_plan.get("total_days", duration),
                    daily_start_time=travel_plan.get("daily_start_time", daily_start),
                    daily_end_time=travel_plan.get("daily_end_time", daily_end),
                    days=day_plans
                )
                
                logger.info(f"✅ [AI_ITINERARY_SUCCESS] AI 일정 생성 성공: {len(day_plans)}일 일정, 총 {total_activities}개 활동")
                return OptimizeResponse(travel_plan=final_plan)
                        
            except (json.JSONDecodeError, ValueError) as parse_error:
                logger.error(f"❌ [AI_PARSE_FAIL] AI 응답 파싱 또는 구조 검증 실패: {parse_error}")
                logger.error(f"📝 [FAILED_JSON] 파싱 실패한 JSON: {json_str if 'json_str' in locals() else 'N/A'}")
                logger.info("🔄 [FALLBACK] 간단한 일정 생성으로 폴백")
            
            # 실패 시 간단한 일정 생성
            return self._create_simple_itinerary(places, duration, daily_start, daily_end)
            
        except Exception as e:
            logger.error(f"❌ [CREATE_FINAL_ERROR] 최종 일정 생성 실패: {e}")
            logger.error(f"📊 [ERROR_TRACEBACK] {traceback.format_exc()}")
            logger.info("🔄 [FINAL_FALLBACK] 최종 폴백: 간단한 일정 생성")
            return self._create_simple_itinerary(places, duration, daily_start, daily_end)

    def _create_simple_itinerary(self, places: List[PlaceData], duration: int, daily_start: str, daily_end: str) -> OptimizeResponse:
        """간단한 일정 생성 (AI 실패 시 폴백)"""
        try:
            logger.info(f"🔄 [SIMPLE_ITINERARY] 간단한 일정 생성: {len(places)}개 장소, {duration}일")
            
            if not places:
                logger.warning("⚠️ [NO_PLACES] 장소가 없어 기본 일정 생성")
                return OptimizeResponse(
                    travel_plan=TravelPlan(
                        total_days=duration,
                        daily_start_time=daily_start,
                        daily_end_time=daily_end,
                        days=[DayPlan(
                            day=1,
                            date="2024-01-01",
                            activities=[ActivityDetail(
                                time="10:00",
                                place_name="여행 계획을 다시 세워보세요",
                                category="안내",
                                duration_minutes=60,
                                description="장소 정보가 부족합니다. 다른 조건으로 다시 시도해주세요."
                            )]
                        )]
                    )
                )
            
            # 장소를 일수로 나누어 배치 (더 균등하게)
            places_per_day = max(1, len(places) // duration)
            remaining_places = len(places) % duration
            day_plans = []
            place_idx = 0
            
            for day in range(1, duration + 1):
                # 남은 장소를 앞쪽 날짜에 더 배치
                current_day_places = places_per_day + (1 if day <= remaining_places else 0)
                day_places = places[place_idx:place_idx + current_day_places]
                place_idx += current_day_places
                
                logger.info(f"🔄 [DAY_{day}] {day}일차: {len(day_places)}개 장소 배치")
                
                activities = []
                start_hour = int(daily_start.split(':')[0])
                end_hour = int(daily_end.split(':')[0])
                
                for i, place in enumerate(day_places):
                    # 시간 계산 (균등 배치)
                    if len(day_places) > 1:
                        time_slot = (end_hour - start_hour) // len(day_places)
                        hour = start_hour + (i * time_slot)
                    else:
                        hour = start_hour + 1
                    
                    # 시간 범위 체크
                    if hour >= end_hour:
                        hour = end_hour - 2
                    
                    activity = ActivityDetail(
                        time=f"{hour:02d}:00",
                        place_name=place.name,
                        category=place.category,
                        duration_minutes=min(120, (time_slot * 60) if len(day_places) > 1 else 120),
                        description=f"{place.name}에서의 {place.category} 활동"
                    )
                    activities.append(activity)
                    logger.info(f"  - {hour:02d}:00 {place.name} ({place.category})")
                
                # 활동이 없는 날은 기본 활동 추가
                if not activities:
                    activities.append(ActivityDetail(
                        time=f"{start_hour + 1:02d}:00",
                        place_name="자유 시간",
                        category="휴식",
                        duration_minutes=120,
                        description="개인 시간 또는 추가 탐방"
                    ))
                
                day_plan = DayPlan(
                    day=day,
                    date=f"2024-01-{day:02d}",
                    activities=activities
                )
                day_plans.append(day_plan)
            
            travel_plan = TravelPlan(
                total_days=duration,
                daily_start_time=daily_start,
                daily_end_time=daily_end,
                days=day_plans
            )
            
            total_activities = sum(len(day.activities) for day in day_plans)
            logger.info(f"✅ [SIMPLE_ITINERARY_SUCCESS] 간단한 일정 생성 완료: {len(day_plans)}일, 총 {total_activities}개 활동")
            return OptimizeResponse(travel_plan=travel_plan)
            
        except Exception as e:
            logger.error(f"❌ [SIMPLE_ITINERARY_ERROR] 간단한 일정 생성 실패: {e}")
            logger.error(f"📊 [ERROR_TRACEBACK] {traceback.format_exc()}")
            # 최소한의 응답 반환
            logger.info("🔄 [MINIMAL_FALLBACK] 최소한의 응답 반환")
            return OptimizeResponse(
                travel_plan=TravelPlan(
                    total_days=max(1, duration),
                    daily_start_time=daily_start,
                    daily_end_time=daily_end,
                    days=[DayPlan(
                        day=1,
                        date="2024-01-01",
                        activities=[ActivityDetail(
                            time="10:00",
                            place_name="시스템 오류",
                            category="안내",
                            duration_minutes=60,
                            description="일정 생성 중 오류가 발생했습니다. 다시 시도해주세요."
                        )]
                    )]
                )
            )

    async def _calculate_real_travel_times(self, day_plans: List[DayPlan], places: List[PlaceData]) -> List[DayPlan]:
        """
        실제 Google Directions API를 사용하여 장소 간 이동 시간을 계산하고 업데이트
        """
        try:
            logger.info("🚗 [DIRECTIONS_API_START] Google Directions API로 이동 시간 재계산 시작")
            
            # 장소명으로 PlaceData 매핑 생성
            place_map = {place.name: place for place in places}
            total_legs = 0
            
            for day_plan in day_plans:
                logger.info(f"🚗 [DAY_{day_plan.day}] {day_plan.day}일차 이동 시간 계산")
                activities = day_plan.activities
                
                # 하루 일정의 마지막 장소를 제외하고 반복
                for i in range(len(activities) - 1):
                    try:
                        current_activity = activities[i]
                        next_activity = activities[i + 1]
                        
                        # 현재 장소와 다음 장소의 PlaceData 찾기
                        current_place = place_map.get(current_activity.place_name)
                        next_place = place_map.get(next_activity.place_name)
                        
                        if not current_place or not next_place:
                            logger.warning(f"⚠️ [PLACE_NOT_FOUND] 장소 정보 없음: {current_activity.place_name} -> {next_activity.place_name}")
                            # 기본값 15분 유지
                            if not hasattr(current_activity, 'travel_time_minutes'):
                                current_activity.travel_time_minutes = 15
                            continue
                        
                        # place_id가 있는 경우 사용, 없으면 좌표 사용
                        if current_place.place_id and next_place.place_id:
                            origin = f"place_id:{current_place.place_id}"
                            destination = f"place_id:{next_place.place_id}"
                        else:
                            origin = f"{current_place.lat},{current_place.lng}"
                            destination = f"{next_place.lat},{next_place.lng}"
                        
                        logger.info(f"🚗 [ROUTE_{i+1}] 경로 {i+1}: {current_activity.place_name} -> {next_activity.place_name}")
                        
                        # Google Directions API 호출
                        directions_result = await self.google_directions.get_directions(
                            origin=origin,
                            destination=destination,
                            mode="driving",  # 또는 "transit"
                            language="ko"
                        )
                        
                        if directions_result:
                            # 이동 시간(초)을 분으로 변환
                            duration_seconds = directions_result['duration']['value']
                            duration_minutes = max(1, round(duration_seconds / 60))  # 최소 1분
                            
                            # ActivityDetail에 travel_time_minutes 속성 추가
                            current_activity.travel_time_minutes = duration_minutes
                            
                            distance_km = round(directions_result['distance']['value'] / 1000, 1)
                            total_legs += 1
                            logger.info(f"  - ✅ 경로 {i+1}: {current_activity.place_name} -> {next_activity.place_name} = {duration_minutes}분 ({distance_km}km)")
                        else:
                            logger.warning(f"  - ❌ 경로 {i+1} 계산 실패: Directions API 응답 없음")
                            # 실패 시 기본값 15분
                            current_activity.travel_time_minutes = 15
                            
                    except Exception as e:
                        logger.error(f"  - ❌ 경로 {i+1} 계산 실패: {e}")
                        # 에러 발생 시 기본값 15분
                        if not hasattr(activities[i], 'travel_time_minutes'):
                            activities[i].travel_time_minutes = 15
                
                # 마지막 활동은 이동 시간이 없음
                if activities:
                    activities[-1].travel_time_minutes = 0
                
                logger.info(f"✅ [DAY_{day_plan.day}_COMPLETE] {day_plan.day}일차 이동 시간 계산 완료")
            
            logger.info(f"✅ [DIRECTIONS_API_SUCCESS] 총 {total_legs}개 구간의 이동 시간 계산 완료")
            return day_plans
            
        except Exception as e:
            logger.error(f"❌ [DIRECTIONS_API_ERROR] 이동 시간 계산 전체 실패: {e}")
            logger.error(f"📊 [ERROR_TRACEBACK] {traceback.format_exc()}")
            # 실패 시 모든 활동에 기본값 15분 설정
            for day_plan in day_plans:
                for i, activity in enumerate(day_plan.activities):
                    if i < len(day_plan.activities) - 1:  # 마지막이 아닌 경우
                        activity.travel_time_minutes = 15
                    else:  # 마지막 활동
                        activity.travel_time_minutes = 0
            return day_plans

    def _get_default_itinerary_prompt(self) -> str:
        """기본 일정 생성 프롬프트"""
        return """
다음 장소들을 $duration일 일정으로 최적화해서 배치해주세요:

장소 목록:
$places_list

시간 제약 조건:$time_constraints_info

조건:
- 총 $duration일 일정
- 지리적 위치와 카테고리를 고려한 효율적인 배치
- 각 일차별로 3-5개 장소 배치
- 총 $total_places개 장소 활용
- 날짜별 시간 제약을 반드시 준수

다음 JSON 형식 중 하나로 응답해주세요:

형식 1 (권장):
{
    "travel_plan": {
        "total_days": $duration,
        "daily_start_time": "$daily_start_time",
        "daily_end_time": "$daily_end_time",
        "days": [
            {
                "day": 1,
                "date": "2024-01-01",
                "activities": [
                    {
                        "time": "09:00",
                        "place_name": "장소명",
                        "category": "관광",
                        "duration_minutes": 120,
                        "description": "활동 설명"
                    }
                ]
            }
        ]
    }
}

형식 2 (대안):
{
    "itinerary": [
        {
            "day": 1,
            "date": "2024-01-01",
            "activities": [
                {
                    "time": "09:00",
                    "place_name": "장소명",
                    "category": "관광",
                    "duration_minutes": 120,
                    "description": "활동 설명"
                }
            ]
        }
    ]
}
"""

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
                multi_destination_context=context,
                daily_start_time=getattr(request, 'daily_start_time', '09:00'),
                daily_end_time=getattr(request, 'daily_end_time', '21:00')
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
                            # Google Places API에서 photo_url 생성
                            photo_url = ""
                            if place.get("photos") and len(place["photos"]) > 0:
                                photo = place["photos"][0]
                                if photo.get("name"):
                                    photo_url = f"https://places.googleapis.com/v1/{photo['name']}/media?maxHeightPx=400&key={google_service.api_key}"
                            
                            place_data = {
                                "place_id": place.get("id"),
                                "name": place.get("displayName", {}).get("text"),
                                "address": place.get("formattedAddress"),
                                "rating": place.get("rating"),
                                "lat": place.get("location", {}).get("latitude", 0.0),
                                "lng": place.get("location", {}).get("longitude", 0.0),
                                "photo_url": photo_url,  # 사진 URL 추가
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
                    # 평점이 없는 경우 기본값 설정
                    if not place.get('rating'):
                        place['rating'] = 3.5
                    unique_places[place_id] = place
            
            # 평점 기준으로 정렬
            sorted_places = sorted(
                unique_places.values(),
                key=lambda x: (x.get('rating', 0), x.get('user_ratings_total', 0)),
                reverse=True
            )
            
            # 상위 N개 선택
            filtered_results[category] = sorted_places[:max_items]
            logger.info(f"카테고리 '{category}' 필터링 완료: {len(filtered_results[category])}개 장소")
        
        logger.info(f"결과 처리 및 필터링 완료: {[(k, len(v)) for k, v in filtered_results.items()]}")
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
                    description=place.get("description", ""),  # 이 필드가 없을 수 있음
                    website=place.get('website', '') or place.get('website_url', '')  # 웹사이트 정보 추가
                ))

        # place_pool을 사용하여 DayPlan 생성 (기존 로직 재활용 또는 단순화)
        # 여기서는 간단하게 모든 장소를 첫째 날에 넣는 것으로 단순화
        activities = []
        for place in all_places:
            activities.append(ActivityDetail(
                time="미정",
                place_name=place.name,
                category=place.category,
                duration_minutes=120,
                description=place.description or f"{place.name} 방문",
                place_id=place.place_id,
                lat=place.lat,
                lng=place.lng
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
                travel_plan=optimized_plan,
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
                travel_plan=fallback_plan,
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
                description=place.get("description", ""),
                website=place.get('website', '') or place.get('website_url', '')  # 웹사이트 정보 추가
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
            print("🔥🔥🔥 AdvancedItineraryService.create_final_itinerary CALLED! 🔥🔥🔥")
            print(f"🎯 [OPTIMIZE_START] 최종 일정 생성 시작: {len(places)}개 장소")
            print(f"📊 [INPUT_PLACES] 입력 장소 목록: {[place.name for place in places]}")
            
            logger.info(f"🎯 [OPTIMIZE_START] 최종 일정 생성 시작: {len(places)}개 장소")
            logger.info(f"📊 [INPUT_PLACES] 입력 장소 목록: {[place.name for place in places]}")
            
            # 기본값/제약 설정
            constraints = constraints or {}
            duration = int(constraints.get("duration") or max(1, len(places) // 3))
            daily_start_time = constraints.get("daily_start_time") or "09:00"
            daily_end_time = constraints.get("daily_end_time") or "22:00"
            
            logger.info(f"⚙️ [CONSTRAINTS] 제약 조건 - 기간: {duration}일, 시간: {daily_start_time}~{daily_end_time}")
            
            # v6.0: Enhanced AI Service를 사용한 마스터 프롬프트 기반 일정 생성
            try:
                logger.info("🤖 [AI_GENERATION_START] Enhanced AI Service로 일정 생성 시작")
                
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
                
                logger.info(f"📊 [USER_DATA] 사용자 데이터 구성 완료: {len(user_data['사용자_선택_장소'])}개 장소")
                
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
                
                logger.info("=" * 100)
                logger.info("🚨🚨🚨 REAL AI CALL PATH: Enhanced AI Service 호출 시작! 🚨🚨🚨")
                logger.info(f"📊 [USER_DATA_TO_AI] AI에게 전달할 사용자 데이터:")
                logger.info(f"{user_data}")
                logger.info("=" * 100)
                
                ai_response = await enhanced_ai_service.generate_itinerary_with_master_prompt(user_data)
                
                logger.info("=" * 100)
                logger.info("🚨🚨🚨 AI RESPONSE RECEIVED! 🚨🚨🚨")
                logger.info(f"🤖 [AI_RESPONSE_RECEIVED] AI 응답 수신 완료 (길이: {len(ai_response) if ai_response else 0})")
                logger.info(f"📝 [AI_RESPONSE_CONTENT] AI 응답 내용:")
                logger.info(f"{ai_response}")
                logger.info("=" * 100)
                
                if not ai_response or not ai_response.strip():
                    logger.error("❌ [AI_EMPTY_RESPONSE] AI가 빈 응답을 반환했습니다")
                    raise ValueError("AI가 빈 응답을 반환했습니다")
                
                # AI 응답을 TravelPlan으로 변환
                logger.info("🔄 [CONVERSION_START] AI 응답을 TravelPlan으로 변환 시작")
                optimized_plan = self._convert_ai_response_to_travel_plan(ai_response, places)
                logger.info(f"✅ [CONVERSION_SUCCESS] TravelPlan 변환 완료: {len(optimized_plan.daily_plans) if optimized_plan and optimized_plan.daily_plans else 0}일 일정")
                
            except Exception as ai_error:
                logger.error(f"❌ [AI_ERROR] AI 기반 일정 생성 실패: {ai_error}")
                logger.error(f"📊 [AI_ERROR_TRACEBACK] {traceback.format_exc()}")
                logger.info("🔄 [FALLBACK_START] 폴백 일정 생성 시작")
                
                # 폴백으로 간단한 일정 생성
                try:
                    optimized_plan = self._create_time_constrained_plan(places, duration, daily_start_time, daily_end_time)
                    logger.info(f"✅ [FALLBACK_SUCCESS] 폴백 일정 생성 완료: {len(optimized_plan.daily_plans) if optimized_plan and optimized_plan.daily_plans else 0}일 일정")
                except Exception as fallback_error:
                    logger.error(f"❌ [FALLBACK_ERROR] 폴백 일정 생성도 실패: {fallback_error}")
                    # 최후 수단: 기본 일정 생성
                    optimized_plan = self._create_basic_plan(places, duration)
                    logger.info("🆘 [EMERGENCY_PLAN] 기본 일정 생성 완료")
            
            final_plan = self._ensure_schema_compat(optimized_plan)
            
            # 안전장치: final_plan이 None인 경우 기본 계획 생성
            if not final_plan:
                logger.error("❌ [FINAL_PLAN_NULL] final_plan이 None입니다. 기본 계획 생성")
                final_plan = self._create_empty_travel_plan()
            
            return OptimizeResponse(
                travel_plan=final_plan,
                optimized_plan=final_plan,
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

    def _create_basic_plan(self, places: List[PlaceData], duration: int) -> TravelPlan:
        """최후 수단: 기본 일정 생성"""
        try:
            from app.schemas.itinerary import TravelPlan, DayPlan, Activity
            
            daily_plans = []
            places_per_day = max(1, len(places) // duration)
            
            for day in range(duration):
                start_idx = day * places_per_day
                end_idx = min(start_idx + places_per_day, len(places))
                day_places = places[start_idx:end_idx]
                
                activities = []
                for i, place in enumerate(day_places):
                    activity = Activity(
                        time=f"{9 + i * 2:02d}:00",
                        name=place.name,
                        location=place.address or "위치 정보 없음",
                        duration=120,
                        type=place.category or "관광",
                        description=f"{place.name} 방문"
                    )
                    activities.append(activity)
                
                if not activities:  # 활동이 없으면 기본 활동 추가
                    activities.append(Activity(
                        time="09:00",
                        name=f"{day + 1}일차 자유시간",
                        location="여행지",
                        duration=480,
                        type="자유시간",
                        description="자유롭게 여행을 즐겨보세요"
                    ))
                
                day_plan = DayPlan(
                    day=day + 1,
                    date=f"2024-01-{day + 1:02d}",
                    activities=activities,
                    meals={"점심": "현지 맛집", "저녁": "추천 레스토랑"},
                    transportation=["도보", "대중교통"],
                    estimated_cost=f"{50000 + day * 20000}원"
                )
                daily_plans.append(day_plan)
            
            return TravelPlan(
                title="기본 여행 일정",
                concept="선택하신 장소들을 기반으로 한 기본 일정입니다",
                total_days=duration,
                daily_start_time="09:00",
                daily_end_time="22:00",
                daily_plans=daily_plans
            )
            
        except Exception as e:
            logger.error(f"❌ [BASIC_PLAN_ERROR] 기본 일정 생성 실패: {e}")
            # 최후의 최후 수단
            return self._create_empty_travel_plan()

    def _ensure_schema_compat(self, plan: TravelPlan) -> TravelPlan:
        """Pydantic 스키마 적합성 보정: 문자열/누락 필드 보완"""
        try:
            logger.info("🔧 [SCHEMA_COMPAT] 스키마 호환성 검사 시작")
            
            # [핵심 수정] plan이나 daily_plans가 None인 경우 방어
            if not plan:
                logger.error("❌ [SCHEMA_COMPAT] plan 객체가 None입니다")
                return self._create_empty_travel_plan()
            
            # daily_plans 필드 확인 (새로운 스키마에서는 'days' 사용)
            daily_plans_data = getattr(plan, 'daily_plans', None) or getattr(plan, 'days', None)
            if not daily_plans_data:
                logger.warning("⚠️ [SCHEMA_COMPAT] daily_plans/days가 비어있습니다")
                return self._create_empty_travel_plan()
            
            logger.info(f"📊 [SCHEMA_COMPAT] 처리할 일정 수: {len(daily_plans_data)}")
            
            # daily_plans의 activities는 ActivityDetail 목록이어야 하므로, 잘못된 타입을 방지
            sanitized_daily = []
            for day in daily_plans_data:
                # theme 누락/비문자 방어
                theme = day.theme if isinstance(day.theme, str) and day.theme else f"Day {day.day}"
                activities = []
                for a in day.activities:
                    # a가 dict일 가능성도 방어
                    if isinstance(a, ActivityDetail):
                        activities.append(a)
                    elif isinstance(a, dict):
                        activities.append(ActivityDetail(
                            time=str(a.get("time", "09:00")),
                            place_name=str(a.get("place_name", a.get("activity", "장소"))),
                            category=str(a.get("category", "관광")),
                            duration_minutes=int(a.get("duration_minutes", 60)),
                            description=str(a.get("description", a.get("activity_description", ""))),
                            place_id=a.get("place_id"),
                            lat=a.get("lat"),
                            lng=a.get("lng")
                        ))
                    else:
                        # 알 수 없는 타입은 건너뜀
                        continue
                
                sanitized_daily.append(DayPlan(
                    day=day.day,
                    theme=theme,
                    activities=activities,
                    meals=getattr(day, 'meals', {}) if hasattr(day, 'meals') and isinstance(day.meals, dict) else {},
                    transportation=getattr(day, 'transportation', []) if hasattr(day, 'transportation') and isinstance(day.transportation, list) else [],
                    estimated_cost=str(getattr(day, 'estimated_cost', '-')) if hasattr(day, 'estimated_cost') and day.estimated_cost is not None else "-",
                ))

            # places 보정: description/주소 등 문자열화
            sanitized_places = []
            places_data = getattr(plan, 'places', []) or []
            for p in places_data:
                sanitized_places.append(PlaceData(
                    place_id=str(p.place_id),
                    name=str(p.name),
                    category=str(p.category or "관광"),
                    lat=float(p.lat or 0.0),
                    lng=float(p.lng or 0.0),
                    rating=float(p.rating) if p.rating is not None else None,
                    address=str(p.address) if p.address else None,
                    description=str(p.description) if p.description else None,
                    website=str(p.website) if hasattr(p, 'website') and p.website else ""  # 웹사이트 정보 추가
                ))

            # 새로운 TravelPlan 스키마에 맞게 생성
            result_plan = TravelPlan(
                total_days=len(sanitized_daily),
                daily_start_time=getattr(plan, 'daily_start_time', '09:00'),
                daily_end_time=getattr(plan, 'daily_end_time', '21:00'),
                days=sanitized_daily,
                title=getattr(plan, 'title', '여행 일정'),
                concept=getattr(plan, 'concept', 'AI 생성 일정'),
                places=sanitized_places or []
            )
            
            logger.info(f"✅ [SCHEMA_COMPAT] 스키마 호환성 검사 완료: {len(sanitized_daily)}일 일정")
            return result_plan
            
        except Exception as e:
            logger.error(f"❌ [SCHEMA_COMPAT_ERROR] 스키마 호환성 검사 실패: {e}")
            logger.error(f"📊 [ERROR_TRACEBACK] {traceback.format_exc()}")
            return self._create_empty_travel_plan()

    def _create_empty_travel_plan(self) -> TravelPlan:
        """빈 TravelPlan 생성 (에러 발생 시 폴백)"""
        logger.info("🔄 [EMPTY_PLAN] 빈 여행 계획 생성")
        return TravelPlan(
            total_days=1,
            daily_start_time="09:00",
            daily_end_time="21:00",
            days=[],
            title="기본 여행 일정",
            concept="기본 여행 계획",
            places=[]
        )

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
                activities.append(ActivityDetail(
                    time=f"{9 + i * 2}:00",
                    place_name=place.name,
                    category=place.category,
                    duration_minutes=120,
                    description=place.description or f"{place.name}에서 즐거운 시간을 보내세요",
                    place_id=place.place_id,
                    lat=place.lat,
                    lng=place.lng
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
                # ActivityDetail 생성 시 모든 값을 문자열/기본값으로 안전 보정
                activities.append(ActivityDetail(
                    time=str(start_hh),
                    place_name=str(place.name or ""),
                    activity_description=str(label or ""),
                    transportation_details="도보/대중교통",
                    place_id=str(place.place_id or ""),
                    lat=float(place.lat or 0.0),
                    lng=float(place.lng or 0.0)
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

            # DayPlan 생성 전 활동 리스트가 올바른지 검증/보정
            sanitized_activities: List[ActivityDetail] = []
            for a in activities:
                try:
                    # ActivityDetail 객체 그대로 사용
                    if isinstance(a, ActivityDetail):
                        sanitized_activities.append(a)
                    else:
                        # dict나 다른 타입인 경우 ActivityDetail로 변환
                        sanitized_activities.append(ActivityDetail(
                            time=str(getattr(a, 'time', '09:00')),
                            place_name=str(getattr(a, 'place_name', getattr(a, 'activity', '장소'))),
                            category=str(getattr(a, 'category', '관광')),
                            duration_minutes=getattr(a, 'duration_minutes', 120),
                            description=str(getattr(a, 'description', getattr(a, 'activity_description', ''))),
                            place_id=getattr(a, 'place_id', None),
                            lat=getattr(a, 'lat', None),
                            lng=getattr(a, 'lng', None)
                        ))
                except Exception:
                    continue

            daily_plans.append(DayPlan(
                day=int(day),
                theme=str(f"{day}일차 최적화 일정"),
                activities=sanitized_activities,
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
        AI 응답을 TravelPlan 객체로 변환 (새로운 스키마 적용)
        """
        try:
            logger.info("🔄 [CONVERT_START] AI 응답을 TravelPlan으로 변환 시작")
            logger.info(f"📊 [AI_RESPONSE_LENGTH] AI 응답 길이: {len(ai_response)}")
            
            import json
            ai_data = json.loads(ai_response)
            logger.info(f"✅ [JSON_PARSE_SUCCESS] JSON 파싱 성공")
            logger.info(f"🤖 [AI_DATA_STRUCTURE] AI 응답 구조:\n{json.dumps(ai_data, ensure_ascii=False, indent=2)}")
            
            # travel_plan 구조 확인
            if 'travel_plan' in ai_data:
                travel_plan_data = ai_data['travel_plan']
                logger.info(f"📊 [TRAVEL_PLAN_KEYS] travel_plan 키: {list(travel_plan_data.keys())}")
                
                # days 배열 확인
                days_data = travel_plan_data.get('days', [])
                logger.info(f"📊 [DAYS_COUNT] 일정 일수: {len(days_data)}")
                
                # 장소명으로 PlaceData 매핑 생성
                place_map = {place.name: place for place in places}
                logger.info(f"📊 [PLACE_MAP] 장소 매핑: {list(place_map.keys())}")
                
                daily_plans = []
                for i, day_data in enumerate(days_data):
                    logger.info(f"📅 [DAY_{i+1}] {i+1}일차 처리 시작")
                    
                    activities = []
                    activities_data = day_data.get('activities', [])
                    logger.info(f"📊 [DAY_{i+1}_ACTIVITIES] {i+1}일차 활동 수: {len(activities_data)}")
                    
                    for j, activity_data in enumerate(activities_data):
                        place_name = activity_data.get("place_name", "장소")
                        place_data = place_map.get(place_name)
                        
                        # ActivityDetail 객체 생성 (새로운 스키마)
                        activity = ActivityDetail(
                            time=activity_data.get("time", "09:00"),
                            place_name=place_name,
                            category=activity_data.get("category", "관광"),
                            duration_minutes=activity_data.get("duration_minutes", 120),
                            description=activity_data.get("description", f"{place_name}에서의 활동"),
                            travel_time_minutes=activity_data.get("travel_time_minutes", 15),
                            place_id=place_data.place_id if place_data else None,
                            lat=place_data.lat if place_data else None,
                            lng=place_data.lng if place_data else None
                        )
                        activities.append(activity)
                        logger.info(f"✅ [ACTIVITY_{j+1}] {i+1}일차 {j+1}번째 활동 추가: {place_name}")
                    
                    # 새로운 DayPlan 생성
                    day_plan = DayPlan(
                        day=day_data.get("day", i+1),
                        date=day_data.get("date", f"2024-01-{i+1:02d}"),
                        activities=activities,
                        theme=f"{i+1}일차 여행"
                    )
                    daily_plans.append(day_plan)
                    logger.info(f"✅ [DAY_{i+1}_COMPLETE] {i+1}일차 계획 완성: {len(activities)}개 활동")
                
                # 새로운 TravelPlan 생성
                travel_plan = TravelPlan(
                    total_days=travel_plan_data.get("total_days", len(days_data)),
                    daily_start_time=travel_plan_data.get("daily_start_time", "09:00"),
                    daily_end_time=travel_plan_data.get("daily_end_time", "21:00"),
                    days=daily_plans,
                    title=travel_plan_data.get("title", "AI 생성 여행 일정"),
                    concept="AI가 최적화한 맞춤형 여행 계획",
                    places=places
                )
                
                logger.info(f"✅ [CONVERT_SUCCESS] TravelPlan 변환 완료: {len(daily_plans)}일 일정")
                return travel_plan
                
            else:
                # 기존 형식이나 다른 구조 처리 (폴백)
                logger.warning("⚠️ [FALLBACK_FORMAT] 예상치 못한 AI 응답 구조, 폴백 처리")
                logger.info(f"📊 [AVAILABLE_KEYS] 사용 가능한 키: {list(ai_data.keys())}")
                
                # 가능한 키들 확인
                days_data = []
                if 'days' in ai_data:
                    days_data = ai_data['days']
                elif 'itinerary' in ai_data:
                    days_data = ai_data['itinerary']
                elif isinstance(ai_data, list):
                    days_data = ai_data
                
                if not days_data:
                    logger.error("❌ [NO_DAYS_DATA] 일정 데이터를 찾을 수 없음")
                    raise ValueError("AI 응답에서 일정 데이터를 찾을 수 없습니다")
                
                # 폴백 처리
                daily_plans = []
                for i, day_data in enumerate(days_data):
                    activities = []
                    activities_data = day_data.get('activities', day_data.get('schedule', []))
                    
                    for activity_data in activities_data:
                        activity = ActivityDetail(
                            time=activity_data.get("time", activity_data.get("start_time", "09:00")),
                            place_name=activity_data.get("place_name", activity_data.get("location", {}).get("name", "장소")),
                            category=activity_data.get("category", "관광"),
                            duration_minutes=activity_data.get("duration_minutes", 120),
                            description=activity_data.get("description", "활동"),
                            travel_time_minutes=15
                        )
                        activities.append(activity)
                    
                    day_plan = DayPlan(
                        day=i + 1,
                        date=f"2024-01-{i+1:02d}",
                        activities=activities
                    )
                    daily_plans.append(day_plan)
                
                return TravelPlan(
                    total_days=len(daily_plans),
                    daily_start_time="09:00",
                    daily_end_time="21:00",
                    days=daily_plans,
                    title="AI 생성 여행 일정",
                    concept="AI가 최적화한 맞춤형 여행 계획",
                    places=places
                )
            
        except Exception as e:
            logger.error(f"❌ [CONVERT_ERROR] AI 응답 변환 실패: {e}")
            logger.error(f"📊 [ERROR_TRACEBACK] {traceback.format_exc()}")
            logger.error(f"📊 [RAW_RESPONSE] 원본 응답: {ai_response}")
            
            # 최후 폴백: 기본 계획 반환
            logger.info("🔄 [EMERGENCY_FALLBACK] 긴급 폴백 계획 생성")
            return TravelPlan(
                total_days=1,
                daily_start_time="09:00",
                daily_end_time="21:00",
                days=[],
                title="기본 여행 일정",
                concept="기본 여행 계획",
                places=places
            )
    
    def _get_default_itinerary_prompt(self) -> str:
        """기본 일정 생성 프롬프트 (Supabase 실패 시 사용)"""
        return """
당신은 전문 여행 플래너입니다. 주어진 장소들과 제약 조건을 바탕으로 최적의 여행 일정을 생성해주세요.

입력 정보:
- 선택된 장소들: $places_list
- 여행 기간: $duration일
- 일일 시작 시간: $daily_start_time
- 일일 종료 시간: $daily_end_time
- 총 장소 수: $total_places개
$time_constraints_info

다음 JSON 형식으로 응답해주세요:

{
  "travel_plan": {
    "total_days": $duration,
    "daily_start_time": "$daily_start_time",
    "daily_end_time": "$daily_end_time",
    "days": [
      {
        "day": 1,
        "date": "2024-01-01",
        "activities": [
          {
            "time": "09:00",
            "place_name": "장소명",
            "category": "관광",
            "duration_minutes": 120,
            "description": "활동 설명"
          }
        ]
      }
    ]
  }
}

규칙:
1. 각 일차마다 적절한 수의 활동을 배치하세요
2. 이동 시간을 고려하여 현실적인 일정을 만드세요
3. 식사 시간(12:00-13:00, 18:00-19:00)을 고려하세요
4. 모든 선택된 장소를 포함하되, 무리하지 않게 배치하세요
5. 각 활동의 소요 시간을 현실적으로 설정하세요
"""