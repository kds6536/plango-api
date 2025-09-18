"""
최적화된 장소 추천 서비스 (v2.0)
Google Places Autocomplete 전제 - 단순화된 아키텍처
"""

import asyncio
import json
import logging
from string import Template
from typing import Dict, List, Any, Optional
from fastapi import HTTPException

from app.schemas.place import PlaceRecommendationRequest, PlaceRecommendationResponse
from app.services.supabase_service import SupabaseService
from app.services.enhanced_ai_service import EnhancedAIService
from app.services.google_places_service import GooglePlacesService

logger = logging.getLogger(__name__)

class PlaceRecommendationServiceV2:
    """
    최적화된 장소 추천 서비스 (v2.0)
    
    핵심 전제: 프론트엔드에서 항상 Google Places Autocomplete를 통해
    명확한 place_id를 제공한다.
    
    따라서:
    - Geocoding API 호출 불필요
    - 동명지역 처리 불필요  
    - 복잡한 조건 분기 불필요
    - 단일 Plan A만 존재
    """
    
    def __init__(self, supabase: SupabaseService, ai_service: EnhancedAIService, google_places_service: GooglePlacesService):
        self.supabase = supabase
        self.ai_service = ai_service
        self.google_places_service = google_places_service

    async def generate_place_recommendations(self, request: PlaceRecommendationRequest) -> PlaceRecommendationResponse:
        """
        최적화된 추천 생성 메인 함수
        
        흐름:
        1. place_id 검증
        2. 캐시 확인
        3. AI 키워드 생성 (1단계 프롬프트)
        4. Google Places 검색
        5. 결과 저장 & 반환
        """
        try:
            logger.info(f"🚀 [V2_START] 최적화된 추천 생성 시작: {request.city}, {request.country}")
            
            # === 1. place_id 검증 ===
            if not hasattr(request, 'place_id') or not request.place_id:
                raise HTTPException(
                    status_code=400, 
                    detail="place_id가 필요합니다. Google Places Autocomplete를 사용해주세요."
                )
            
            logger.info(f"✅ [PLACE_ID_VERIFIED] place_id 확인: {request.place_id}")
            
            # === 2. 도시 ID 확보 & 캐시 확인 ===
            city_id = await self._get_or_create_city_from_request(request)
            logger.info(f"🏙️ [CITY_ID] 도시 ID: {city_id}")
            
            # 캐시 확인
            cached_recommendations = await self._get_cached_recommendations(city_id)
            if cached_recommendations and len(cached_recommendations) >= 15:
                logger.info(f"✅ [CACHE_HIT] 캐시에서 충분한 데이터 발견: {len(cached_recommendations)}개")
                return self._format_cached_response(city_id, request, cached_recommendations)
            
            logger.info(f"📊 [CACHE_MISS] 캐시 부족, 새로운 추천 생성 필요")
            
            # === 3. AI 키워드 생성 ===
            ai_keywords = await self._generate_ai_keywords(request, city_id)
            logger.info(f"🤖 [AI_KEYWORDS] 생성된 검색 키워드: {ai_keywords}")
            
            # === 4. Google Places 검색 ===
            categorized_places = await self._search_places_with_keywords(ai_keywords, request)
            logger.info(f"🔍 [PLACES_FOUND] 검색 결과: {[(k, len(v)) for k, v in categorized_places.items()]}")
            
            # === 5. 결과 저장 & 반환 ===
            if categorized_places:
                await self._save_to_cache(city_id, categorized_places)
                logger.info(f"💾 [CACHE_SAVED] 결과 캐시 저장 완료")
            
            total_new_places = sum(len(places) for places in categorized_places.values())
            
            return PlaceRecommendationResponse(
                success=True,
                city_id=city_id,
                city_name=request.city,
                country_name=request.country,
                main_theme="V2 최적화된 추천",
                recommendations=categorized_places,
                previously_recommended_count=len(cached_recommendations) if cached_recommendations else 0,
                newly_recommended_count=total_new_places
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ [V2_ERROR] 추천 생성 실패: {e}", exc_info=True)
            raise Exception(f"추천 생성 중 오류가 발생했습니다: {str(e)}")

    async def _get_or_create_city_from_request(self, request: PlaceRecommendationRequest) -> int:
        """place_id 기반으로 도시 ID 확보"""
        try:
            # 국가/지역/도시 ID 생성 (기존 로직 유지)
            country_id = await self.supabase.get_or_create_country(request.country)
            region_id = await self.supabase.get_or_create_region(country_id, "")  # region 정보 없으므로 빈 문자열
            city_id = await self.supabase.get_or_create_city(region_id, request.city)
            
            return city_id
            
        except Exception as e:
            logger.error(f"❌ [CITY_ID_ERROR] 도시 ID 생성 실패: {e}")
            raise Exception(f"도시 정보 처리 실패: {str(e)}")

    async def _get_cached_recommendations(self, city_id: int) -> List[Dict[str, Any]]:
        """캐시된 추천 데이터 조회"""
        try:
            return await self.supabase.get_all_cached_places_by_city(city_id)
        except Exception as e:
            logger.warning(f"⚠️ [CACHE_ERROR] 캐시 조회 실패: {e}")
            return []

    async def _generate_ai_keywords(self, request: PlaceRecommendationRequest, city_id: int) -> Dict[str, str]:
        """AI를 사용하여 맞춤형 검색 키워드 생성"""
        try:
            # 1단계 프롬프트 로드
            prompt_template = await self.supabase.get_master_prompt('search_strategy_v1')
            if not prompt_template:
                logger.warning("⚠️ [PROMPT_FALLBACK] 1단계 프롬프트를 찾을 수 없어 기본 키워드 사용")
                return self._get_default_keywords(request.city)
            
            # 기존 장소 목록 조회 (중복 방지용)
            existing_places = await self.supabase.get_existing_place_names(city_id)
            
            # 프롬프트 템플릿 완성
            template = Template(prompt_template)
            ai_prompt = template.safe_substitute(
                city=request.city,
                country=request.country,
                total_duration=request.total_duration,
                travelers_count=request.travelers_count,
                budget_range=getattr(request, 'budget_range', 'medium'),
                travel_style=", ".join(request.travel_style) if request.travel_style else "관광",
                special_requests=getattr(request, 'special_requests', None) or "다양한 명소와 맛집 포함",
                existing_places=", ".join(existing_places[:10]) if existing_places else "없음"  # 처음 10개만
            )
            
            # AI 호출
            logger.info("🤖 [AI_CALL] AI 키워드 생성 시작")
            ai_response = await asyncio.wait_for(
                self.ai_service.generate_response(ai_prompt, max_tokens=1200),
                timeout=60.0
            )
            
            # AI 응답 파싱
            try:
                cleaned_response = self._extract_json_from_response(ai_response)
                ai_result = json.loads(cleaned_response)
                
                # search_queries 추출 및 정규화
                raw_queries = ai_result.get('search_queries', {})
                normalized_queries = self._normalize_search_queries(raw_queries)
                
                if not normalized_queries:
                    logger.warning("⚠️ [AI_FALLBACK] AI 키워드가 비어있어 기본 키워드 사용")
                    return self._get_default_keywords(request.city)
                
                return normalized_queries
                
            except Exception as parse_error:
                logger.error(f"❌ [AI_PARSE_ERROR] AI 응답 파싱 실패: {parse_error}")
                logger.error(f"📝 [AI_RAW] 원본 응답: {ai_response}")
                return self._get_default_keywords(request.city)
                
        except asyncio.TimeoutError:
            logger.error("⏰ [AI_TIMEOUT] AI 응답 시간 초과")
            return self._get_default_keywords(request.city)
        except Exception as e:
            logger.error(f"❌ [AI_ERROR] AI 키워드 생성 실패: {e}")
            return self._get_default_keywords(request.city)

    def _get_default_keywords(self, city: str) -> Dict[str, str]:
        """AI 실패 시 사용할 기본 검색 키워드"""
        return {
            "볼거리": f"tourist attractions sightseeing in {city}",
            "먹거리": f"restaurants local food in {city}",
            "즐길거리": f"activities entertainment in {city}",
            "숙소": f"hotels accommodation in {city}"
        }

    def _extract_json_from_response(self, response: str) -> str:
        """AI 응답에서 JSON 부분만 추출"""
        if not response:
            return "{}"
        
        # JSON 블록 찾기
        start_markers = ['```json', '```', '{']
        end_markers = ['```', '}']
        
        for start_marker in start_markers:
            start_idx = response.find(start_marker)
            if start_idx != -1:
                if start_marker == '{':
                    # { 부터 마지막 } 까지
                    brace_count = 0
                    json_start = start_idx
                    for i, char in enumerate(response[start_idx:], start_idx):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                return response[json_start:i+1]
                else:
                    # 마커 이후부터 끝 마커까지
                    content_start = start_idx + len(start_marker)
                    for end_marker in end_markers:
                        end_idx = response.find(end_marker, content_start)
                        if end_idx != -1:
                            return response[content_start:end_idx].strip()
        
        # JSON 블록을 찾지 못한 경우 전체 응답 반환
        return response.strip()

    def _normalize_search_queries(self, raw_queries: Dict[str, Any]) -> Dict[str, str]:
        """AI가 생성한 검색 쿼리를 정규화"""
        normalized = {}
        
        # 표준 카테고리 매핑
        category_mapping = {
            "볼거리": ["볼거리", "관광", "sightseeing", "attractions", "tourist"],
            "먹거리": ["먹거리", "음식", "restaurants", "food", "dining"],
            "즐길거리": ["즐길거리", "액티비티", "activities", "entertainment", "fun"],
            "숙소": ["숙소", "호텔", "hotels", "accommodation", "lodging"]
        }
        
        for standard_category, aliases in category_mapping.items():
            # 원본 키에서 매칭되는 것 찾기
            found_value = None
            for key, value in raw_queries.items():
                if any(alias.lower() in key.lower() for alias in aliases):
                    found_value = str(value).strip()
                    break
            
            if found_value:
                normalized[standard_category] = found_value
            else:
                # 기본값 설정
                city_placeholder = "{city}"  # 나중에 실제 도시명으로 교체
                defaults = {
                    "볼거리": f"tourist attractions in {city_placeholder}",
                    "먹거리": f"restaurants in {city_placeholder}",
                    "즐길거리": f"activities in {city_placeholder}",
                    "숙소": f"hotels in {city_placeholder}"
                }
                normalized[standard_category] = defaults[standard_category]
        
        return normalized

    async def _search_places_with_keywords(self, keywords: Dict[str, str], request: PlaceRecommendationRequest) -> Dict[str, List[Dict[str, Any]]]:
        """키워드를 사용하여 Google Places 검색"""
        try:
            all_results = {}
            
            for category, keyword in keywords.items():
                try:
                    # 키워드에서 {city} 플레이스홀더를 실제 도시명으로 교체
                    search_query = keyword.replace("{city}", request.city)
                    
                    logger.info(f"🔍 [SEARCH] {category}: '{search_query}'")
                    
                    # Google Places API 호출
                    places_result = await self.google_places_service.search_places(search_query)
                    
                    if places_result and len(places_result) > 0:
                        # 10개로 제한
                        limited_results = places_result[:10]
                        all_results[category] = limited_results
                        logger.info(f"✅ [FOUND] {category}: {len(limited_results)}개")
                    else:
                        logger.warning(f"⚠️ [NO_RESULTS] {category}: 결과 없음")
                        all_results[category] = []
                        
                except Exception as e:
                    logger.error(f"❌ [SEARCH_ERROR] {category} 검색 실패: {e}")
                    all_results[category] = []
                    continue
            
            return all_results
            
        except Exception as e:
            logger.error(f"❌ [SEARCH_TOTAL_ERROR] 전체 검색 실패: {e}")
            raise Exception(f"장소 검색 실패: {str(e)}")

    async def _save_to_cache(self, city_id: int, categorized_places: Dict[str, List[Dict[str, Any]]]) -> bool:
        """검색 결과를 캐시에 저장"""
        try:
            return await self.supabase.save_places_to_cache(city_id, categorized_places)
        except Exception as e:
            logger.error(f"❌ [CACHE_SAVE_ERROR] 캐시 저장 실패: {e}")
            return False

    def _format_cached_response(self, city_id: int, request: PlaceRecommendationRequest, cached_places: List[Dict[str, Any]]) -> PlaceRecommendationResponse:
        """캐시된 데이터를 응답 형식으로 변환"""
        # 카테고리별로 분류
        categorized = {}
        for place in cached_places:
            category = place.get('category', '기타')
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(place)
        
        # 각 카테고리당 10개로 제한
        for category in categorized:
            if len(categorized[category]) > 10:
                categorized[category] = categorized[category][:10]
        
        return PlaceRecommendationResponse(
            success=True,
            city_id=city_id,
            city_name=request.city,
            country_name=request.country,
            main_theme="캐시된 데이터",
            recommendations=categorized,
            previously_recommended_count=len(cached_places),
            newly_recommended_count=0
        )