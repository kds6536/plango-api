"""
새로운 장소 추천 서비스 (v6.0)
새로운 데이터베이스 스키마(countries, cities, cached_places, prompts)에 맞춰 설계된 장소 추천 시스템
"""

import json
import logging
from typing import Dict, List, Any, Optional
from string import Template
from app.services.supabase_service import supabase_service
from app.services.dynamic_ai_service import DynamicAIService
from app.services.google_places_service import GooglePlacesService
from fastapi import HTTPException
from app.schemas.place import PlaceRecommendationRequest, PlaceRecommendationResponse
from app.utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)


class PlaceRecommendationService:
    """새로운 장소 추천 서비스"""
    
    def __init__(self):
        self.supabase = supabase_service
        self.ai_service = DynamicAIService()
        from app.services.google_places_service import GooglePlacesService
        self.google_places_service = GooglePlacesService()
    
    async def generate_place_recommendations(
        self, 
        request: PlaceRecommendationRequest
    ) -> PlaceRecommendationResponse:
        """
        메인 장소 추천 함수
        1순위: Supabase 기존 데이터 조회
        2순위: Plan A (search_strategy_v1)
        3순위: Plan B (place_recommendation_v1)
        """
        try:
            logger.info(f"🚀 [REQUEST_START] 장소 추천 요청: {request.city}, {request.country}")
            
            # === 0단계: 도시명 표준화 및 중복 확인 ===
            logger.info("🔍 [STEP_0] 도시명 표준화 및 중복 확인 시작")
            standardized_result = await self._standardize_and_check_city(request)
            
            if standardized_result.get('status') == 'AMBIGUOUS':
                logger.info("⚠️ [AMBIGUOUS_CITY] 동일 이름 도시 발견, 사용자 선택 필요")
                return PlaceRecommendationResponse(
                    success=True,
                    city_id=0,
                    main_theme='AMBIGUOUS',
                    recommendations={},
                    previously_recommended_count=0,
                    newly_recommended_count=0,
                    status='AMBIGUOUS',
                    options=standardized_result.get('options', []),
                    message="동일한 이름의 도시가 여러 개 있습니다. 정확한 도시를 선택해주세요."
                )
            
            # 표준화된 정보 사용
            normalized_country = standardized_result['country']
            normalized_city = standardized_result['city']
            city_id = standardized_result['city_id']
            
            logger.info(f"✅ [STANDARDIZED] 표준화 완료: {normalized_country}/{normalized_city} (ID: {city_id})")
            
            # === 1단계: Supabase 기존 데이터 우선 조회 ===
            logger.info("📋 [STEP_1] Supabase 기존 데이터 우선 조회")
            existing_recommendations = await self._get_existing_recommendations_from_cache(city_id)
            
            if existing_recommendations and len(existing_recommendations) >= 20:  # 충분한 데이터가 있으면
                logger.info(f"✅ [CACHE_HIT] 충분한 기존 데이터 발견: {len(existing_recommendations)}개")
                categorized_cache = self._categorize_cached_places(existing_recommendations)
                
                return PlaceRecommendationResponse(
                    success=True,
                    city_id=city_id,
                    main_theme="기존 데이터 활용",
                    recommendations=categorized_cache,
                    previously_recommended_count=len(existing_recommendations),
                    newly_recommended_count=0
                )
            
            logger.info(f"📊 [CACHE_INSUFFICIENT] 기존 데이터 부족: {len(existing_recommendations) if existing_recommendations else 0}개, 새로운 추천 진행")
            
            # === 2단계: Plan A 시도 ===
            logger.info("🧠 [PLAN_A_START] Plan A 시작: search_strategy_v1")
            try:
                return await self._execute_plan_a(request, normalized_country, normalized_city, city_id)
            except Exception as e:
                logger.error(f"❌ [PLAN_A_FAIL] Plan A 실패: {e}")
                await self._notify_admin_plan_a_failure("Plan A 전체 실패", str(e))
                
                # === 3단계: Plan B 폴백 ===
                logger.info("🔄 [PLAN_B_START] Plan A 실패로 인한 Plan B 전환")
                return await self._fallback_to_legacy_recommendation(request)

            template = Template(prompt_template)
            ai_prompt = template.safe_substitute(
                city=request.city,
                country=request.country,
                total_duration=request.total_duration,
                travelers_count=request.travelers_count,
                budget_range=request.budget_range,
                travel_style=", ".join(request.travel_style) if request.travel_style else "없음",
                special_requests=getattr(request, 'special_requests', None) or "없음",
                existing_places=""
            )
            # 디버깅: AI에 전달되는 최종 프롬프트 전체 기록
            try:
                logger.info("[AI_REQUEST_PROMPT] 프롬프트 전송 (요약) - city=%s, country=%s, region=%s, length=%d", getattr(request, 'city', ''), getattr(request, 'country', ''), getattr(request, 'region', ''), len(ai_prompt))
                logger.debug(f"[AI_REQUEST_PROMPT] {ai_prompt}")
            except Exception:
                pass

            ai_raw = await self.ai_service.generate_text(ai_prompt, max_tokens=1200)
            logger.info("🤖 [AI] search_strategy_v1 응답 수신")
            
            # AI 응답 검증
            if not ai_raw or not isinstance(ai_raw, str):
                logger.error("AI가 빈 응답 또는 잘못된 형식을 반환했습니다.")
                raise HTTPException(status_code=500, detail="AI 응답이 올바르지 않습니다.")
            
            # 디버깅: AI 원본 응답 전체 기록 (파싱 전)
            try:
                trimmed = (ai_raw[:1000] + "…") if len(ai_raw) > 1000 else ai_raw
                logger.info("[AI_RESPONSE_RAW] 원본 응답(요약): %s", trimmed)
                logger.debug(f"[AI_RESPONSE_RAW] {ai_raw}")
            except Exception:
                pass
            try:
                cleaned = self._extract_json_from_response(ai_raw)
                if not cleaned or not cleaned.strip():
                    raise ValueError("정제된 응답이 비어있습니다.")
                ai_result = json.loads(cleaned)
            except Exception as parse_err:
                # 에러: JSON 파싱 실패 시 원본 응답도 함께 기록
                try:
                    logger.error("❌ [PLAN_A_PARSE_FAIL] search_strategy_v1 JSON 파싱 실패: %s", parse_err, exc_info=True)
                    logger.error("📝 [PLAN_A_RAW] 원본 AI 응답: %s", ai_raw)
                    logger.error("🔧 [PLAN_A_CLEANED] 정제 시도 문자열: %s", cleaned)
                    logger.error("📊 [PLAN_A_STATS] 응답 길이: %d, 정제 후 길이: %d", len(ai_raw) if ai_raw else 0, len(cleaned) if cleaned else 0)
                except Exception:
                    logger.error("❌ [PLAN_A_LOG_FAIL] Plan A 로깅 중 추가 오류 발생", exc_info=True)
                
                logger.info("🔄 [FALLBACK_TRIGGER] Plan A JSON 파싱 실패로 인한 Plan B 전환")
                await self._notify_admin_plan_a_failure("JSON 파싱 실패", f"파싱 에러: {str(parse_err)}, 원본 응답 길이: {len(ai_raw) if ai_raw else 0}")
                return await self._fallback_to_legacy_recommendation(request)

            status = (ai_result.get('status') or '').upper()
            logger.info(f"🧠 [AI] 상태 판별: {status}")

            # 모달에서 선택된 옵션인지 확인 (region 정보가 명확하게 포함된 경우)
            has_explicit_region = bool(getattr(request, 'region', '').strip())
            logger.info(f"🔍 [FORCE_RESOLVE_CHECK] 명시적 region 존재: {has_explicit_region} (region: '{getattr(request, 'region', '')}')")
            
            # region이 명확하게 포함된 요청이면 AI가 AMBIGUOUS라고 해도 강제로 SUCCESS 처리
            if has_explicit_region and status == 'AMBIGUOUS':
                logger.info(f"⚡ [FORCE_SUCCESS] region이 명시적으로 포함되어 AMBIGUOUS를 SUCCESS로 강제 변경")
                status = 'SUCCESS'
                # AI가 AMBIGUOUS로 판단했지만 standardized_location이 없을 수 있으므로 요청값으로 대체
                if not ai_result.get('standardized_location'):
                    ai_result['standardized_location'] = {
                        'country': getattr(request, 'country', ''),
                        'region': getattr(request, 'region', ''),
                        'city': getattr(request, 'city', '')
                    }
                    logger.info(f"🔧 [STANDARDIZED_FALLBACK] standardized_location을 요청값으로 생성: {ai_result['standardized_location']}")

            # === 1-A. AMBIGUOUS: 즉시 반환 (강제 확정 조건이 아닐 때만)
            if status == 'AMBIGUOUS':
                options = ai_result.get('options') or []
                return PlaceRecommendationResponse(
                    success=True,
                    city_id=0,
                    main_theme='AMBIGUOUS',
                    recommendations={},
                    previously_recommended_count=0,
                    newly_recommended_count=0,
                    status='AMBIGUOUS',
                    options=options,
                    message="입력하신 도시가 모호합니다. 아래 목록에서 정확한 도시를 선택해주세요."
                )

            # === 1-B. SUCCESS: 표준화된 위치 → ID 확정 → 검색전략 실행 ===
            if status == 'SUCCESS':
                std = ai_result.get('standardized_location') or {}
                logger.info(f"🔍 [AI_ANALYSIS] AI 표준화 결과: {std}")
                
                # 표준화: AI가 제공한 영어명을 우선 사용. 없으면 한국어명, 최후엔 요청값
                normalized_country = (
                    std.get('country_en') or 
                    std.get('country_english') or 
                    std.get('country') or 
                    getattr(request, 'country', '')
                ).strip()
                
                normalized_region = (
                    std.get('region_en') or 
                    std.get('region_english') or 
                    std.get('state_en') or 
                    std.get('region') or 
                    std.get('state') or ''
                ).strip()
                
                normalized_city = (
                    std.get('city_en') or 
                    std.get('city_english') or 
                    std.get('city') or 
                    getattr(request, 'city', '')
                ).strip()
                
                logger.info(f"🌐 [STANDARDIZED] Country: {normalized_country}, Region: {normalized_region}, City: {normalized_city}")
                logger.info(f"🔍 [DEBUG] 원본 요청: country={getattr(request, 'country', '')}, city={getattr(request, 'city', '')}")

                # 2. 국가/지역/도시 ID 확보 (region_id 기반 도시 생성)
                logger.info(f"🏗️ [DB_SETUP] 국가/지역/도시 ID 확보 시작")
                try:
                    country_id = await self.supabase.get_or_create_country(normalized_country)
                    logger.info(f"🌍 [COUNTRY_ID] 국가 ID 확보: {country_id} ({normalized_country})")
                    
                    region_id = await self.supabase.get_or_create_region(country_id, normalized_region)
                    logger.info(f"🗺️ [REGION_ID] 지역 ID 확보: {region_id} ({normalized_region})")
                    
                    city_id = await self.supabase.get_or_create_city(region_id=region_id, city_name=normalized_city)
                    logger.info(f"🏙️ [CITY_ID] 도시 ID 확보: {city_id} ({normalized_city})")
                except Exception as db_error:
                    logger.error(f"💥 [DB_ERROR] Supabase ID 확보 실패: {db_error}")
                    raise HTTPException(status_code=500, detail=f"데이터베이스 설정 실패: {str(db_error)}")

                # 3. 기존 추천 장소 이름 목록 조회 (중복 방지용)
                try:
                    existing_place_names = await self.supabase.get_existing_place_names(city_id)
                    logger.info(f"📋 [EXISTING_PLACES] 기존 장소 {len(existing_place_names)}개 발견: {existing_place_names[:5] if existing_place_names else []}")
                except Exception as existing_error:
                    logger.warning(f"⚠️ [EXISTING_PLACES_ERROR] 기존 장소 조회 실패: {existing_error}")
                    existing_place_names = []

                # 4. AI가 제공한 검색전략에서 primary_query 사용
                raw_queries = ai_result.get('search_queries') or {}
                logger.info(f"🔍 [RAW_QUERIES] AI 원본 검색 쿼리: {raw_queries}")
                
                search_queries = self._normalize_search_queries(raw_queries)
                logger.info(f"📋 [SEARCH_STRATEGY] AI 검색 계획 완료(정규화됨): {search_queries}")
                
                # 병렬 Google Places API 호출 + 재시도 로직
                logger.info(f"🚀 [PLAN_A_GOOGLE] Plan A Google Places API 호출 시작")
                logger.info(f"📋 [PLAN_A_QUERIES] 검색 쿼리: {search_queries}")
                try:
                    categorized_places = await self.google_places_service.parallel_search_by_categories(
                        search_queries=search_queries,
                        target_count_per_category=10,
                        city=normalized_city,
                        country=normalized_country,
                        language_code=(getattr(request, 'language_code', None) or 'ko')
                    )
                    logger.info(f"✅ [PLAN_A_GOOGLE_SUCCESS] Plan A Google API 성공: {[(k, len(v)) for k, v in categorized_places.items()]}")
                except Exception as api_error:
                    logger.error(f"❌ [PLAN_A_GOOGLE_FAIL] Plan A Google Places API 실패: {api_error}")
                    logger.info("🔄 [FALLBACK_TRIGGER] Google API 실패로 인한 Plan B 전환")
                    await self._notify_admin_plan_a_failure("Google Places API 호출 실패", str(api_error))
                    return await self._fallback_to_legacy_recommendation(request)
                
                # 결과 데이터 후처리: 카테고리 라벨을 요청 언어로 변환
                recommendations = self._convert_categories_by_language(
                    categorized_places,
                    getattr(request, 'language_code', None) or 'ko'
                )

                # 카테고리별 결과가 10개 미만인 경우, 캐시에서 부족분 보충
                try:
                    for k in list(recommendations.keys()):
                        places = recommendations.get(k, [])
                        if len(places) < 10:
                            needed = 10 - len(places)
                            cached = await self.supabase.get_cached_places_by_category(city_id, k, needed)
                            for c in cached:
                                if all(p.get('place_id') != c.get('place_id') for p in places):
                                    places.append({
                                        'place_id': c.get('place_id'),
                                        'name': c.get('name'),
                                        'category': c.get('category'),
                                        'address': c.get('address'),
                                    })
                            recommendations[k] = places
                except Exception as fill_err:
                    logger.warning(f"캐시 보충 중 경고: {fill_err}")
                
                # 새로운 장소들을 cached_places에 저장
                logger.info(f"💾 [CACHE_SAVE] 캐시 저장 시작: {len(recommendations)}개 카테고리")
                if recommendations:
                    try:
                        save_result = await self._save_new_places(city_id, recommendations)
                        logger.info(f"💾 [CACHE_SAVE] 저장 결과: {save_result}")
                    except Exception as e:
                        logger.error(f"💥 [CACHE_SAVE_ERROR] 캐시 저장 실패: {e}")
                        logger.error(f"💥 [CACHE_SAVE_ERROR] 저장 시도 데이터: city_id={city_id}, categories={list(recommendations.keys())}")
                    logger.info(f"💾 [CACHE_SAVE] 새로운 장소들 캐시 저장 완료")
                
                # 응답 생성
                total_new_places = sum(len(places) for places in recommendations.values())
                logger.info(f"📊 [RESPONSE_PREP] 응답 데이터 준비: {total_new_places}개 신규 장소, {len(existing_place_names)}개 기존 장소")
                
                response = PlaceRecommendationResponse(
                    success=True,
                    city_id=city_id,
                    main_theme="Plan A 성공 (search_strategy_v1)",
                    recommendations=recommendations,
                    previously_recommended_count=len(existing_place_names),
                    newly_recommended_count=total_new_places
                )
                
                logger.info(f"✅ [PLAN_A_SUCCESS] Plan A 완전 성공!")
                logger.info(f"📊 [PLAN_A_RESULT] 도시: {normalized_city}, 신규: {total_new_places}개, 기존: {len(existing_place_names)}개")
                logger.info(f"📋 [PLAN_A_CATEGORIES] 카테고리별 결과: {[(k, len(v)) for k, v in recommendations.items()]}")
                return response

            # === 1-C. 그 외: 예외 처리 ===
            raise HTTPException(status_code=500, detail="AI 응답 상태가 올바르지 않습니다")
            
        except Exception as e:
            logger.error(f"❌ [SYSTEM_ERROR] 전체 시스템 오류: {e}")
            await self._notify_admin_plan_b_failure("전체 시스템 오류", str(e))
            raise HTTPException(status_code=500, detail=f"장소 추천 시스템 오류: {str(e)}")

    async def _standardize_and_check_city(self, request: PlaceRecommendationRequest) -> Dict[str, Any]:
        """도시명 표준화 및 중복 확인"""
        try:
            logger.info(f"🔍 [STANDARDIZE] 도시명 표준화 시작: {request.city}, {request.country}")
            
            # 1. 영문 표준화 (Google Geocoding API 활용)
            standardized_info = await self._get_standardized_location(request.city, request.country)
            
            if not standardized_info:
                logger.warning("⚠️ [STANDARDIZE_FAIL] 표준화 실패, 원본 정보 사용")
                standardized_info = {
                    'country': request.country,
                    'city': request.city
                }
            
            # 2. 동일 이름 도시 확인
            similar_cities = await self._check_duplicate_cities(standardized_info['city'])
            
            if len(similar_cities) > 1:
                logger.info(f"⚠️ [DUPLICATE_CITIES] 동일 이름 도시 {len(similar_cities)}개 발견")
                return {
                    'status': 'AMBIGUOUS',
                    'options': similar_cities
                }
            
            # 3. 국가/도시 ID 확보 (영문 표준화된 이름으로)
            country_id = await self.supabase.get_or_create_country(standardized_info['country'])
            region_id = await self.supabase.get_or_create_region(country_id, "")
            city_id = await self.supabase.get_or_create_city(region_id=region_id, city_name=standardized_info['city'])
            
            return {
                'status': 'SUCCESS',
                'country': standardized_info['country'],
                'city': standardized_info['city'],
                'city_id': city_id
            }
            
        except Exception as e:
            logger.error(f"❌ [STANDARDIZE_ERROR] 표준화 중 오류: {e}")
            # 폴백: 원본 정보로 진행
            country_id = await self.supabase.get_or_create_country(request.country)
            region_id = await self.supabase.get_or_create_region(country_id, "")
            city_id = await self.supabase.get_or_create_city(region_id=region_id, city_name=request.city)
            
            return {
                'status': 'SUCCESS',
                'country': request.country,
                'city': request.city,
                'city_id': city_id
            }

    async def _get_standardized_location(self, city: str, country: str) -> Optional[Dict[str, str]]:
        """Google Geocoding API로 표준화된 영문 지명 획득"""
        try:
            # Google Places API의 geocoding 기능 활용
            geocode_result = await self.google_places_service.geocode_location(f"{city}, {country}")
            
            if geocode_result and 'results' in geocode_result and geocode_result['results']:
                result = geocode_result['results'][0]
                
                # 영문 국가명과 도시명 추출
                country_name = None
                city_name = None
                
                for component in result.get('address_components', []):
                    types = component.get('types', [])
                    if 'country' in types:
                        country_name = component.get('long_name')
                    elif 'locality' in types or 'administrative_area_level_1' in types:
                        city_name = component.get('long_name')
                
                if country_name and city_name:
                    logger.info(f"✅ [GEOCODE_SUCCESS] 표준화 성공: {city_name}, {country_name}")
                    return {
                        'country': country_name,
                        'city': city_name
                    }
            
            logger.warning("⚠️ [GEOCODE_NO_RESULT] Geocoding 결과 없음")
            return None
            
        except Exception as e:
            logger.error(f"❌ [GEOCODE_ERROR] Geocoding 실패: {e}")
            return None

    async def _check_duplicate_cities(self, city_name: str) -> List[Dict[str, Any]]:
        """동일 이름 도시 확인"""
        try:
            # Supabase에서 동일 이름 도시 검색
            duplicate_cities = await self.supabase.find_cities_by_name(city_name)
            
            if len(duplicate_cities) > 1:
                options = []
                for city_info in duplicate_cities:
                    options.append({
                        'display_name': f"{city_info['city_name']}, {city_info['country_name']}",
                        'request_body': {
                            'city': city_info['city_name'],
                            'country': city_info['country_name'],
                            'region': city_info.get('region_name', '')
                        }
                    })
                return options
            
            return duplicate_cities
            
        except Exception as e:
            logger.error(f"❌ [DUPLICATE_CHECK_ERROR] 중복 확인 실패: {e}")
            return []

    async def _get_existing_recommendations_from_cache(self, city_id: int) -> List[Dict[str, Any]]:
        """Supabase 캐시에서 기존 추천 데이터 조회"""
        try:
            cached_places = await self.supabase.get_all_cached_places_by_city(city_id)
            logger.info(f"📋 [CACHE_QUERY] 도시 ID {city_id}에서 {len(cached_places) if cached_places else 0}개 캐시 데이터 조회")
            return cached_places or []
        except Exception as e:
            logger.error(f"❌ [CACHE_ERROR] 캐시 조회 실패: {e}")
            return []

    def _categorize_cached_places(self, cached_places: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """캐시된 장소들을 카테고리별로 분류"""
        categorized = {
            '볼거리': [],
            '먹거리': [],
            '즐길거리': [],
            '숙소': []
        }
        
        for place in cached_places:
            category = place.get('category', '기타')
            if category in categorized:
                categorized[category].append({
                    'place_id': place.get('place_id'),
                    'name': place.get('name'),
                    'category': category,
                    'address': place.get('address'),
                    'rating': place.get('rating'),
                    'photo_url': place.get('photo_url', ''),  # 사진 URL 추가
                    'websiteUri': place.get('website', ''),  # 🔥 수정: website 필드 사용 (supabase_service에서 매핑한 필드명)
                    'lat': place.get('coordinates', {}).get('lat', 0.0),
                    'lng': place.get('coordinates', {}).get('lng', 0.0)
                })
        
        # 각 카테고리별로 최대 10개씩 제한
        for category in categorized:
            categorized[category] = categorized[category][:10]
        
        return categorized

    async def _execute_plan_a(self, request: PlaceRecommendationRequest, country: str, city: str, city_id: int) -> PlaceRecommendationResponse:
        """Plan A 실행"""
        try:
            logger.info("🧠 [PLAN_A_EXECUTE] Plan A 실행 시작")
            
            # search_strategy_v1 프롬프트 로드
            prompt_template = await self.supabase.get_master_prompt('search_strategy_v1')
            logger.info("✅ [PLAN_A_PROMPT] search_strategy_v1 프롬프트 로드 성공")
            
            # 기존 장소 목록 조회
            existing_place_names = await self.supabase.get_existing_place_names(city_id)
            
            # AI 프롬프트 구성 및 호출
            template = Template(prompt_template)
            ai_prompt = template.safe_substitute(
                city=city,
                country=country,
                total_duration=request.total_duration,
                travelers_count=request.travelers_count,
                budget_range=request.budget_range,
                travel_style=", ".join(request.travel_style) if request.travel_style else "없음",
                special_requests=getattr(request, 'special_requests', None) or "없음",
                existing_places=", ".join(existing_place_names) if existing_place_names else "없음",
                daily_start_time=getattr(request, 'daily_start_time', '09:00'),
                daily_end_time=getattr(request, 'daily_end_time', '21:00')
            )
            
            logger.info("🤖 [PLAN_A_AI] AI 호출 시작")
            ai_raw = await self.ai_service.generate_text(ai_prompt, max_tokens=1200)
            
            # AI 응답 검증 강화
            if not ai_raw or not isinstance(ai_raw, str) or not ai_raw.strip():
                raise ValueError("AI가 빈 응답을 반환했습니다.")
            
            logger.info(f"✅ [PLAN_A_AI_SUCCESS] AI 응답 수신: {len(ai_raw)}자")
            
            # JSON 파싱
            cleaned = self._extract_json_from_response(ai_raw)
            ai_result = json.loads(cleaned)
            
            # AI 응답 상태 확인
            status = (ai_result.get('status') or '').upper()
            logger.info(f"🧠 [AI_STATUS] AI 상태 판별: {status}")
            
            if status == 'SUCCESS':
                # 검색 쿼리 정규화
                raw_queries = ai_result.get('search_queries') or {}
                search_queries = self._normalize_search_queries(raw_queries)
                logger.info(f"📋 [SEARCH_QUERIES] 정규화된 검색 쿼리: {search_queries}")
                
                # Google Places API 병렬 호출
                categorized_places = await self.google_places_service.parallel_search_by_categories(
                    search_queries=search_queries,
                    target_count_per_category=10,
                    city=city,
                    country=country,
                    language_code=getattr(request, 'language_code', 'ko')
                )
                
                # 카테고리 라벨 언어 변환
                recommendations = self._convert_categories_by_language(
                    categorized_places,
                    getattr(request, 'language_code', 'ko')
                )
                
                # 새로운 장소들을 캐시에 저장
                if recommendations:
                    await self._save_new_places(city_id, recommendations)
                
                total_new_places = sum(len(places) for places in recommendations.values())
                
                logger.info("✅ [PLAN_A_SUCCESS] Plan A 완료")
                return PlaceRecommendationResponse(
                    success=True,
                    city_id=city_id,
                    main_theme="Plan A 성공 (search_strategy_v1)",
                    recommendations=recommendations,
                    previously_recommended_count=len(existing_place_names),
                    newly_recommended_count=total_new_places
                )
            else:
                raise ValueError(f"AI가 예상치 못한 상태를 반환했습니다: {status}")
            
        except Exception as e:
            logger.error(f"❌ [PLAN_A_ERROR] Plan A 실행 실패: {e}")
            raise

    def _normalize_search_queries(self, raw_queries: Any) -> Dict[str, str]:
        """
        AI(search_strategy_v1) 응답을 카테고리별 텍스트 쿼리 딕셔너리로 정규화
        """
        try:
            if isinstance(raw_queries, dict):
                normalized: Dict[str, str] = {}
                for key, value in raw_queries.items():
                    category = key.lower()
                    # value가 문자열이면 그대로 사용
                    if isinstance(value, str):
                        normalized[category] = value
                    elif isinstance(value, dict):
                        # primary_query, query, text 등 자주 쓰는 키 우선
                        for candidate in ["primary_query", "query", "text", "q"]:
                            if isinstance(value.get(candidate), str) and value.get(candidate).strip():
                                normalized[category] = value.get(candidate).strip()
                                break
                        else:
                            # value의 첫 번째 문자열 값을 사용
                            str_val = next((v for v in value.values() if isinstance(v, str) and v.strip()), None)
                            if str_val:
                                normalized[category] = str_val.strip()
                    # 리스트면 첫 항목 문자열 채택
                    elif isinstance(value, list) and value:
                        first = value[0]
                        if isinstance(first, str):
                            normalized[category] = first
                        elif isinstance(first, dict):
                            str_val = first.get("primary_query") or first.get("query") or first.get("text")
                            if isinstance(str_val, str):
                                normalized[category] = str_val
                
                # 최소한의 기본 카테고리 보장
                return {
                    "tourism": normalized.get("tourism") or normalized.get("attractions") or normalized.get("관광") or "tourist attractions",
                    "food": normalized.get("food") or normalized.get("foods") or normalized.get("먹거리") or "restaurants",
                    "activity": normalized.get("activity") or normalized.get("activities") or normalized.get("즐길거리") or "activities",
                    "accommodation": normalized.get("accommodation") or normalized.get("accommodations") or normalized.get("숙소") or "hotels"
                }
            else:
                # 기본 쿼리 반환
                return {
                    "tourism": "tourist attractions",
                    "food": "restaurants",
                    "activity": "activities",
                    "accommodation": "hotels"
                }
        except Exception as e:
            logger.error(f"❌ [NORMALIZE_QUERIES_ERROR] 쿼리 정규화 실패: {e}")
            return {
                "tourism": "tourist attractions",
                "food": "restaurants", 
                "activity": "activities",
                "accommodation": "hotels"
            }

    def _extract_json_from_response(self, response: str) -> str:
        """AI 응답에서 JSON 부분만 추출 (개선된 버전)"""
        try:
            if not response or not isinstance(response, str):
                raise ValueError("빈 응답 또는 잘못된 형식")
            
            response = response.strip()
            
            # 1. 완전한 JSON 객체 찾기 (중괄호 매칭)
            brace_count = 0
            start_idx = -1
            
            for i, char in enumerate(response):
                if char == '{':
                    if start_idx == -1:
                        start_idx = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_idx != -1:
                        # 완전한 JSON 객체 발견
                        json_str = response[start_idx:i + 1]
                        try:
                            # 유효성 검사
                            json.loads(json_str)
                            logger.info(f"✅ [JSON_EXTRACT] 완전한 JSON 추출 성공: {len(json_str)}자")
                            return json_str
                        except json.JSONDecodeError:
                            continue
            
            # 2. 배열 형태 JSON 찾기
            if '[' in response and ']' in response:
                start_idx = response.find('[')
                end_idx = response.rfind(']')
                if end_idx > start_idx:
                    json_str = response[start_idx:end_idx + 1]
                    try:
                        json.loads(json_str)
                        logger.info(f"✅ [JSON_EXTRACT] 배열 JSON 추출 성공: {len(json_str)}자")
                        return json_str
                    except json.JSONDecodeError:
                        pass
            
            # 3. 마지막 시도: 첫 번째 { 부터 마지막 } 까지
            first_brace = response.find('{')
            last_brace = response.rfind('}')
            if first_brace != -1 and last_brace > first_brace:
                json_str = response[first_brace:last_brace + 1]
                try:
                    json.loads(json_str)
                    logger.info(f"✅ [JSON_EXTRACT] 범위 JSON 추출 성공: {len(json_str)}자")
                    return json_str
                except json.JSONDecodeError:
                    pass
            
            # 4. 실패 시 원본 반환
            logger.warning(f"⚠️ [JSON_EXTRACT] JSON 추출 실패, 원본 반환: {len(response)}자")
            return response
            
        except Exception as e:
            logger.error(f"❌ [JSON_EXTRACT_ERROR] JSON 추출 중 오류: {e}")
            return response.strip() if response else "{}"

    async def _save_new_places(self, city_id: int, recommendations: Dict[str, List[Dict[str, Any]]]) -> Dict[str, int]:
        """새로운 장소들을 cached_places 테이블에 저장"""
        try:
            save_counts = {}
            
            for category, places in recommendations.items():
                saved_count = 0
                for place in places:
                    try:
                        # 중복 확인
                        existing = await self.supabase.get_cached_place_by_place_id(place.get('place_id'))
                        if existing:
                            continue
                        
                        # 새 장소 저장
                        place_data = {
                            'city_id': city_id,
                            'place_id': place.get('place_id'),
                            'name': place.get('name'),
                            'category': category,
                            'address': place.get('address', ''),
                            'rating': place.get('rating', 0.0),
                            'photo_url': place.get('photo_url', ''),  # 사진 URL 추가
                            'coordinates': {
                                'lat': place.get('lat', 0.0),
                                'lng': place.get('lng', 0.0)
                            }
                        }
                        
                        await self.supabase.save_cached_place(place_data)
                        saved_count += 1
                        
                    except Exception as place_error:
                        logger.warning(f"⚠️ [SAVE_PLACE_WARN] 개별 장소 저장 실패: {place_error}")
                        continue
                
                save_counts[category] = saved_count
            
            logger.info(f"💾 [SAVE_SUCCESS] 카테고리별 저장 결과: {save_counts}")
            return save_counts
            
        except Exception as e:
            logger.error(f"❌ [SAVE_ERROR] 장소 저장 실패: {e}")
            return {}

    async def _fallback_to_legacy_recommendation(self, request: PlaceRecommendationRequest) -> PlaceRecommendationResponse:
        """Plan B: 기존 place_recommendation_v1 프롬프트 사용"""
        try:
            logger.info("🔄 [PLAN_B_START] Plan B 시작: place_recommendation_v1")
            
            # place_recommendation_v1 프롬프트 로드
            prompt_template = await self.supabase.get_master_prompt('place_recommendation_v1')
            if not prompt_template:
                raise ValueError("place_recommendation_v1 프롬프트를 찾을 수 없습니다")
            
            logger.info("✅ [PLAN_B_PROMPT] place_recommendation_v1 프롬프트 로드 성공")
            
            # AI 프롬프트 구성
            template = Template(prompt_template)
            ai_prompt = template.safe_substitute(
                city=request.city,
                country=request.country,
                total_duration=request.total_duration,
                travelers_count=request.travelers_count,
                budget_range=request.budget_range,
                travel_style=", ".join(request.travel_style) if request.travel_style else "없음",
                special_requests=getattr(request, 'special_requests', None) or "없음"
            )
            
            # AI 호출
            logger.info("🤖 [PLAN_B_AI] AI 호출 시작")
            ai_raw = await self.ai_service.generate_text(ai_prompt, max_tokens=1500)
            
            if not ai_raw or not isinstance(ai_raw, str) or not ai_raw.strip():
                raise ValueError("AI가 빈 응답을 반환했습니다")
            
            logger.info(f"✅ [PLAN_B_AI_SUCCESS] AI 응답 수신: {len(ai_raw)}자")
            
            # JSON 파싱
            cleaned = self._extract_json_from_response(ai_raw)
            ai_result = json.loads(cleaned)
            
            # 기본 응답 구조 생성
            recommendations = {
                '볼거리': [],
                '먹거리': [],
                '즐길거리': [],
                '숙소': []
            }
            
            # AI 결과에서 장소 정보 추출
            places = ai_result.get('places', []) or ai_result.get('recommendations', [])
            
            for place in places:
                category = place.get('category', '기타')
                if category in recommendations:
                    recommendations[category].append({
                        'place_id': f"legacy_{hash(place.get('name', ''))}",
                        'name': place.get('name', ''),
                        'category': category,
                        'address': place.get('address', ''),
                        'rating': place.get('rating', 0.0),
                        'lat': 0.0,
                        'lng': 0.0
                    })
            
            total_places = sum(len(places) for places in recommendations.values())
            
            logger.info(f"✅ [PLAN_B_SUCCESS] Plan B 완료: {total_places}개 장소")
            
            return PlaceRecommendationResponse(
                success=True,
                city_id=0,  # Plan B에서는 임시 ID
                main_theme="Plan B 성공 (place_recommendation_v1)",
                recommendations=recommendations,
                previously_recommended_count=0,
                newly_recommended_count=total_places
            )
            
        except Exception as e:
            logger.error(f"❌ [PLAN_B_ERROR] Plan B 실행 실패: {e}")
            await self._notify_admin_plan_b_failure("Plan B 전체 실패", str(e))
            raise HTTPException(status_code=500, detail=f"Plan B 실패: {str(e)}")
    
    def _convert_categories_by_language(self, categorized_places: Dict[str, List[Dict[str, Any]]], language_code: str) -> Dict[str, List[Dict[str, Any]]]:
        """영문 카테고리를 요청 언어에 맞는 라벨로 변환하되, 장소 dict를 그대로 유지합니다."""
        lang = (language_code or 'ko').lower()
        mapping_by_lang = {
            'ko': {
                'tourism': '볼거리', 'food': '먹거리', 'activity': '즐길거리', 'accommodation': '숙소'
            },
            'en': {
                'tourism': 'Tourism', 'food': 'Food', 'activity': 'Activities', 'accommodation': 'Accommodation'
            },
            'ja': {
                'tourism': '観光', 'food': 'グルメ', 'activity': 'アクティビティ', 'accommodation': '宿泊'
            },
            'zh': {
                'tourism': '旅游', 'food': '美食', 'activity': '活动', 'accommodation': '住宿'
            },
            'vi': {
                'tourism': 'Tham quan', 'food': 'Ẩm thực', 'activity': 'Hoạt động', 'accommodation': 'Lưu trú'
            },
            'id': {
                'tourism': 'Wisata', 'food': 'Makanan', 'activity': 'Aktivitas', 'accommodation': 'Akomodasi'
            }
        }
        mapping = mapping_by_lang.get(lang, mapping_by_lang['en'])

        localized: Dict[str, List[Dict[str, Any]]] = {}
        for eng_category, places in categorized_places.items():
            label = mapping.get(eng_category, eng_category)
            out_places: List[Dict[str, Any]] = []
            for p in places:
                q = dict(p)
                q['category'] = label
                out_places.append(q)
            localized[label] = out_places
        return localized
    
    def _normalize_search_queries(self, raw_queries: Any) -> Dict[str, str]:
        """
        AI(search_strategy_v1) 응답을 카테고리별 텍스트 쿼리 딕셔너리로 정규화
        허용 입력 형태:
        - Dict[str, str]: 이미 완성된 쿼리 맵
        - Dict[str, Dict[str, Any]]: {category: {primary_query: str, ...}} 형태
        - 기타: 예외 처리
        """
        try:
            if isinstance(raw_queries, dict):
                normalized: Dict[str, str] = {}
                for key, value in raw_queries.items():
                    category = key.lower()
                    # value가 문자열이면 그대로 사용
                    if isinstance(value, str):
                        normalized[category] = value
                    elif isinstance(value, dict):
                        # primary_query, query, text 등 자주 쓰는 키 우선
                        for candidate in ["primary_query", "query", "text", "q"]:
                            if isinstance(value.get(candidate), str) and value.get(candidate).strip():
                                normalized[category] = value.get(candidate).strip()
                                break
                        else:
                            # value의 첫 번째 문자열 값을 사용
                            str_val = next((v for v in value.values() if isinstance(v, str) and v.strip()), None)
                            if str_val:
                                normalized[category] = str_val.strip()
                    # 리스트면 첫 항목 문자열 채택
                    elif isinstance(value, list) and value:
                        first = value[0]
                        if isinstance(first, str):
                            normalized[category] = first
                        elif isinstance(first, dict):
                            str_val = first.get("primary_query") or first.get("query") or first.get("text")
                            if isinstance(str_val, str):
                                normalized[category] = str_val
                # 최소한의 기본 카테고리 보장
                return {
                    "tourism": normalized.get("tourism") or normalized.get("attractions") or normalized.get("관광") or "tourist attractions",
                    "food": normalized.get("food") or normalized.get("foods") or normalized.get("먹거리") or "restaurants",
                    "activity": normalized.get("activity") or normalized.get("activities") or normalized.get("즐길거리") or "activities",
                    "accommodation": normalized.get("accommodation") or normalized.get("accommodations") or normalized.get("숙소") or "hotels"
                }
            else:
                raise ValueError("AI 검색 전략 응답이 dict 형태가 아닙니다")
        except Exception as e:
            raise ValueError(f"검색 전략 정규화 실패: {e}")
    
    async def _fallback_to_legacy_recommendation(self, request: PlaceRecommendationRequest) -> PlaceRecommendationResponse:
        """Plan B: place_recommendation_v1 프롬프트 기반 폴백"""
        try:
            logger.info(f"🔄 [PLAN_B_START] Plan B 폴백 모드 시작 (place_recommendation_v1)")
            
            # 1) 국가 → 2) 지역(없으면 빈 문자열) → 3) 도시
            country_id = await self.supabase.get_or_create_country(request.country)
            region_id = await self.supabase.get_or_create_region(country_id, "")
            city_id = await self.supabase.get_or_create_city(region_id=region_id, city_name=request.city)
            
            existing_place_names = await self.supabase.get_existing_place_names(city_id)
            logger.info(f"📋 [PLAN_B_EXISTING] 기존 장소 {len(existing_place_names)}개 확인")
            
            # Plan B: place_recommendation_v1 프롬프트 사용
            try:
                prompt_template = await self.supabase.get_master_prompt('place_recommendation_v1')
                logger.info("✅ [PLAN_B_PROMPT] place_recommendation_v1 프롬프트 로드 성공")
            except Exception as e:
                logger.error(f"❌ [PLAN_B_PROMPT_FAIL] place_recommendation_v1 프롬프트 로드 실패: {e}")
                # 내장 폴백 프롬프트 사용
                prompt_template = self._get_fallback_place_recommendation_prompt()
                logger.info("🔧 [PLAN_B_BUILTIN] 내장 폴백 프롬프트 사용")
            
            dynamic_prompt = await self._create_dynamic_prompt_with_template(request, existing_place_names, prompt_template)
            ai_recommendations = await self._get_ai_recommendations(dynamic_prompt)
            
            if not ai_recommendations:
                raise ValueError("Plan B AI 추천 결과가 없습니다.")
            
            # Google Places API로 장소 정보 강화
            enriched_places = await self._enrich_place_data(ai_recommendations, request.city)
            
            if enriched_places:
                await self._save_new_places(city_id, enriched_places)
            
            logger.info(f"✅ [PLAN_B_SUCCESS] Plan B 폴백 성공: {sum(len(places) for places in enriched_places.values())}개 장소")
            
            return PlaceRecommendationResponse(
                success=True,
                city_id=city_id,
                main_theme="Plan B 폴백 (place_recommendation_v1)",
                recommendations=enriched_places,
                previously_recommended_count=len(existing_place_names),
                newly_recommended_count=sum(len(places) for places in enriched_places.values())
            )
            
        except Exception as e:
            logger.error(f"❌ [PLAN_B_FAIL] Plan B 폴백도 실패: {e}")
            await self._notify_admin_plan_b_failure("Plan B 폴백 실행 실패", str(e))
            raise ValueError(f"모든 추천 방식 실패: {str(e)}")

    async def _create_dynamic_prompt(
        self, 
        request: PlaceRecommendationRequest, 
        existing_places: List[str]
    ) -> str:
        """프롬프트 동적 생성 - 폴백용 기본 프롬프트 생성"""
        try:
            logger.warning("⚠️ [DEPRECATED] _create_dynamic_prompt는 더 이상 사용되지 않습니다. _create_dynamic_prompt_with_template을 사용하세요.")
            # 폴백용 기본 프롬프트 생성
            base_prompt = self._get_fallback_place_recommendation_prompt()
            return await self._create_dynamic_prompt_with_template(request, existing_places, base_prompt)
        except Exception as e:
            logger.error(f"동적 프롬프트 생성 실패: {e}")
            raise ValueError(f"프롬프트 생성 중 오류 발생: {str(e)}")

    async def _create_dynamic_prompt_with_template(
        self, 
        request: PlaceRecommendationRequest, 
        existing_places: List[str],
        prompt_template: str
    ) -> str:
        """템플릿 기반 동적 프롬프트 생성"""
        try:
            logger.info(f"📝 [PROMPT_GEN] 템플릿 기반 프롬프트 생성 시작")
            
            # 기존 추천 장소 목록을 문자열로 변환
            if existing_places:
                previously_recommended_text = f"""
이미 추천된 장소들 (중복 금지):
{', '.join(existing_places)}

위 장소들과 중복되지 않는 새로운 장소만 추천해주세요."""
            else:
                previously_recommended_text = "첫 번째 추천이므로 제약 없이 최고의 장소들을 추천해주세요."
            
            # Template.safe_substitute를 사용하여 안전하게 변수 치환
            from string import Template
            template = Template(prompt_template)
            dynamic_prompt = template.safe_substitute(
                city=request.city,
                country=request.country,
                total_duration=request.total_duration,
                travelers_count=request.travelers_count,
                budget_range=request.budget_range,
                travel_style=", ".join(request.travel_style) if request.travel_style else "없음",
                special_requests=request.special_requests or "없음",
                previously_recommended_places=previously_recommended_text,
                daily_start_time=getattr(request, 'daily_start_time', '09:00'),
                daily_end_time=getattr(request, 'daily_end_time', '21:00')
            )
            
            logger.info(f"✅ [PROMPT_GEN] 프롬프트 생성 완료 (기존 장소 {len(existing_places)}개 제외)")
            return dynamic_prompt
            
            # 기존 추천 장소 목록을 문자열로 변환
            if existing_places:
                previously_recommended_text = f"""
이미 추천된 장소들 (중복 금지):
{', '.join(existing_places)}

위 장소들과 중복되지 않는 새로운 장소만 추천해주세요."""
            else:
                previously_recommended_text = "첫 번째 추천이므로 제약 없이 최고의 장소들을 추천해주세요."
            
            # Template.safe_substitute를 사용하여 안전하게 변수 치환
            # 이 방법은 중괄호가 있는 JSON 예시에서도 안전함
            template = Template(base_prompt)
            dynamic_prompt = template.safe_substitute(
                city=request.city,
                country=request.country,
                duration_days=request.total_duration,  # total_duration → duration_days 매핑
                previously_recommended_places=previously_recommended_text
            )
            
            logger.info(f"동적 프롬프트 생성 완료 (기존 장소 {len(existing_places)}개 제외)")
            return dynamic_prompt
            
        except Exception as e:
            logger.error(f"프롬프트 생성 실패: {e}")
            raise ValueError(f"프롬프트 생성 중 오류 발생: {str(e)}")
    
    async def _get_ai_recommendations(self, prompt: str) -> Dict[str, Any]:
        """AI에게 장소 추천 요청"""
        try:
            logger.info("AI 장소 추천 요청 시작")
            
            # DynamicAIService를 통해 AI 요청
            ai_response = await self.ai_service.generate_text(
                prompt=prompt,
                max_tokens=2000
            )
            
            # AI 응답 로깅 (디버깅용)
            logger.info(f"AI 원본 응답: {ai_response[:500]}...")
            
            # JSON 파싱 강화
            try:
                # 응답에서 JSON 부분만 추출 (마크다운 코드 블록 제거)
                cleaned_response = self._extract_json_from_response(ai_response)
                recommendations = json.loads(cleaned_response)
                logger.info(f"AI 추천 결과 파싱 성공: {len(recommendations)}개 카테고리")
                return recommendations
            except json.JSONDecodeError as e:
                logger.error(f"AI 응답 JSON 파싱 실패: {e}")
                logger.error(f"파싱 시도한 응답: {cleaned_response[:200]}...")
                raise ValueError(f"AI 응답 형식 오류: {str(e)}")
                
        except Exception as e:
            logger.error(f"AI 추천 요청 실패: {e}")
            raise ValueError(f"AI 추천 중 오류 발생: {str(e)}")
    
    def _extract_json_from_response(self, response: str) -> str:
        """AI 응답에서 JSON 부분만 추출"""
        try:
            # 마크다운 코드 블록 제거
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end != -1:
                    return response[start:end].strip()
            
            # 일반 JSON 객체 찾기
            if "{" in response and "}" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                return response[start:end].strip()
            
            # 기본값: 전체 응답 반환
            return response.strip()
            
        except Exception as e:
            logger.warning(f"JSON 추출 실패: {e}")
            return response.strip()
    
    async def _enrich_place_data(
        self, 
        ai_recommendations: Dict[str, Any], 
        city: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Google Places API로 장소 정보 강화"""
        try:
            logger.info("Google Places API 장소 정보 강화 시작")
            
            enriched_results = {}
            category_mapping = {
                "tourism": "tourist_attraction",
                "food": "restaurant", 
                "activity": "amusement_park",
                "accommodation": "lodging"
            }
            
            # 카테고리명 한글 변환
            category_translation = {
                "tourism": "볼거리",
                "food": "먹거리",
                "activity": "즐길거리", 
                "accommodation": "숙소"
            }
            
            for category, place_names in ai_recommendations.items():
                if not isinstance(place_names, list):
                    continue
                
                translated_category = category_translation.get(category, category)
                logger.info(f"{translated_category} 카테고리 처리: {len(place_names)}개 장소")
                
                enriched_places = []
                for place_name in place_names:
                    try:
                        # Google Places API 검색
                        places = await self.google_places_service.search_places(
                            query=f"{place_name} {city}",
                            location=city,
                            place_type=category_mapping.get(category)
                        )
                        
                        if places:
                            # 첫 번째 결과를 선택하고 카테고리 정보 추가
                            place = places[0]
                            place['category'] = translated_category
                            enriched_places.append(place)
                            logger.debug(f"{place_name} 정보 강화 완료")
                        else:
                            logger.warning(f"{place_name} 검색 결과 없음")
                            
                    except Exception as e:
                        logger.warning(f"{place_name} 정보 강화 실패: {e}")
                        continue
                
                enriched_results[translated_category] = enriched_places
                logger.info(f"{translated_category} 카테고리 완료: {len(enriched_places)}개 장소")
            
            return enriched_results
            
        except Exception as e:
            logger.error(f"장소 정보 강화 실패: {e}")
            raise ValueError(f"장소 정보 강화 중 오류 발생: {str(e)}")
    
    async def _save_new_places(
        self, 
        city_id: int, 
        enriched_places: Dict[str, List[Dict[str, Any]]]
    ) -> bool:
        """새로운 장소들을 cached_places에 저장"""
        try:
            logger.info("새로운 장소 cached_places에 저장 시작")
            
            # 모든 카테고리의 장소를 하나의 리스트로 합치기
            all_places = []
            for category, places in enriched_places.items():
                all_places.extend(places)
            
            if all_places:
                success = await self.supabase.save_cached_places(city_id, all_places)
                if success:
                    logger.info(f"총 {len(all_places)}개 장소 저장 완료")
                else:
                    logger.warning("장소 저장 실패")
                return success
            else:
                logger.warning("저장할 장소가 없음")
                return False
                
        except Exception as e:
            logger.error(f"장소 저장 실패: {e}")
            return False

    def _get_fallback_place_recommendation_prompt(self) -> str:
        """Supabase 프롬프트 로드 실패 시 사용할 내장 폴백 프롬프트"""
        return """당신은 세계 최고의 여행 전문가 '플랜고 AI'입니다. 사용자의 여행 정보를 바탕으로 맞춤형 장소를 추천해주세요.

**사용자 여행 정보:**
- 도시: $city
- 국가: $country
- 여행 기간: $total_duration일
- 여행자 수: $travelers_count명
- 예산: $budget_range
- 여행 스타일: $travel_style

$previously_recommended_places

**추천 요구사항:**
1. 각 카테고리별로 다양하고 특색 있는 장소 추천
2. 현지인들이 실제로 가는 숨겨진 맛집과 명소 포함
3. 사용자의 예산과 여행 스타일에 맞는 장소 선별
4. 관광지는 유명한 곳과 로컬한 곳을 적절히 조합

**카테고리별 추천 개수 (최소 5개씩):**
- 볼거리(관광지): 8-12개
- 먹거리(음식점): 8-12개  
- 즐길거리(액티비티): 6-10개
- 숙소: 4-8개

**도시별 추천 예시:**
- 도쿄: 시부야, 하라주쿠, 아사쿠사, 긴자, 롯폰기
- 서울: 홍대, 강남, 명동, 이태원, 북촌한옥마을
- 부산: 해운대, 광안리, 태종대, 감천문화마을, 용두산공원

**JSON 출력 형식 (반드시 이 형식으로만):**
{{
  "볼거리": ["장소명1", "장소명2", "장소명3", "장소명4", "장소명5"],
  "먹거리": ["맛집명1", "맛집명2", "맛집명3", "맛집명4", "맛집명5"],
  "즐길거리": ["액티비티명1", "액티비티명2", "액티비티명3", "액티비티명4"],
  "숙소": ["숙소명1", "숙소명2", "숙소명3", "숙소명4"]
}}

⚠️ 중요: 반드시 JSON 형식으로만 답변해주세요. 다른 설명이나 마크다운 문법은 포함하지 마세요."""

    async def _notify_admin_plan_a_failure(self, failure_type: str, error_details: str):
        """Plan A 실패 시 관리자에게 메일 알림"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            import os
            
            # Railway 환경변수에서 메일 설정 가져오기
            mail_server = os.getenv('MAIL_SERVER')
            mail_port = int(os.getenv('MAIL_PORT', '587'))
            mail_username = os.getenv('MAIL_USERNAME')
            mail_password = os.getenv('MAIL_PASSWORD')
            mail_from = os.getenv('MAIL_FROM')
            
            if not all([mail_server, mail_username, mail_password, mail_from]):
                logger.warning("⚠️ [MAIL_CONFIG] 메일 설정이 불완전하여 알림을 보낼 수 없습니다.")
                return
            
            # 메일 내용 구성
            subject = f"🚨 [Plango Alert] Plan A 실패 - {failure_type}"
            body = f"""
🚨 Plango 시스템 Plan A 실패 알림

📅 발생 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (KST)
🌐 환경: Railway Production
🔧 실패 유형: {failure_type}
❌ 오류 상세: {error_details}

📊 시스템 상태:
- Plan A (search_strategy_v1): 실패 ❌
- Plan B (place_recommendation_v1): 자동 전환됨 🔄
- Supabase 연결: {'정상' if self.supabase.is_connected() else '실패'}
- AI 서비스: {'정상' if self.ai_service else '실패'}

💡 권장 조치사항:
1. Supabase prompts 테이블에서 search_strategy_v1 프롬프트 확인
2. Railway 환경변수 SUPABASE_URL, SUPABASE_KEY 점검
3. AI 서비스 (OpenAI/Gemini) API 키 상태 확인
4. 네트워크 연결 상태 점검

🔗 확인 링크:
- Railway 대시보드: https://railway.com/dashboard
- Supabase 대시보드: https://supabase.com/dashboard

⚠️ 이 알림은 시스템 안정성을 위해 자동으로 생성되었습니다.
현재 Plan B로 정상 서비스 중이지만, Plan A 복구가 필요합니다.
            """
            
            # 메일 발송
            msg = MIMEMultipart()
            msg['From'] = mail_from
            msg['To'] = mail_username  # 관리자 본인에게 발송
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(mail_server, mail_port)
            server.starttls()
            server.login(mail_username, mail_password)
            server.send_message(msg)
            server.quit()
            
            logger.info("📧 [ADMIN_MAIL] Plan A 실패 알림 메일 발송 완료")
            
        except Exception as e:
            logger.error(f"❌ [MAIL_FAIL] 관리자 알림 메일 발송 실패: {e}")

    async def _notify_admin_plan_b_failure(self, failure_type: str, error_details: str):
        """Plan B도 실패 시 긴급 관리자 알림"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            import os
            
            # Railway 환경변수에서 메일 설정 가져오기
            mail_server = os.getenv('MAIL_SERVER')
            mail_port = int(os.getenv('MAIL_PORT', '587'))
            mail_username = os.getenv('MAIL_USERNAME')
            mail_password = os.getenv('MAIL_PASSWORD')
            mail_from = os.getenv('MAIL_FROM')
            
            if not all([mail_server, mail_username, mail_password, mail_from]):
                logger.error("❌ [MAIL_CONFIG] 메일 설정이 불완전하여 긴급 알림을 보낼 수 없습니다!")
                return
            
            # 긴급 메일 내용 구성
            subject = f"🚨🚨 [Plango CRITICAL] Plan A & B 모두 실패 - 긴급 조치 필요"
            body = f"""
🚨🚨 Plango 시스템 전체 실패 - 긴급 상황 🚨🚨

📅 발생 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (KST)
🌐 환경: Railway Production
🔧 최종 실패 유형: {failure_type}
❌ 오류 상세: {error_details}

📊 시스템 상태:
- Plan A (search_strategy_v1): 실패 ❌
- Plan B (place_recommendation_v1): 실패 ❌
- 서비스 상태: 중단됨 🛑

⚠️ 긴급 조치 필요:
1. 즉시 Railway 로그 확인
2. Supabase 연결 상태 점검
3. AI API 키 상태 확인
4. 필요시 서비스 재시작

🔗 긴급 확인 링크:
- Railway 대시보드: https://railway.com/dashboard
- Supabase 대시보드: https://supabase.com/dashboard

🚨 현재 사용자에게 서비스를 제공할 수 없는 상태입니다.
즉시 조치가 필요합니다!
            """
            
            # 긴급 메일 발송
            msg = MIMEMultipart()
            msg['From'] = mail_from
            msg['To'] = mail_username
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(mail_server, mail_port)
            server.starttls()
            server.login(mail_username, mail_password)
            server.send_message(msg)
            server.quit()
            
            logger.error("📧 [CRITICAL_MAIL] Plan B 실패 긴급 알림 메일 발송 완료")
            
        except Exception as e:
            logger.error(f"❌ [CRITICAL_MAIL_FAIL] 긴급 알림 메일 발송 실패: {e}")


# 전역 인스턴스
place_recommendation_service = PlaceRecommendationService()