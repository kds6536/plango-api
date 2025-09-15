"""
새로운 장소 추천 서비스 (v6.0) - 수정된 버전
새로운 DB 스키마에 맞춘 장소 추천 로직
"""

import asyncio
import json
import logging
from string import Template
from typing import Dict, List, Any, Optional
from fastapi import HTTPException

from app.schemas.place import PlaceRecommendationRequest, PlaceRecommendationResponse
from app.services.supabase_service import SupabaseService
from app.services.ai_service import AIService
from app.services.enhanced_ai_service import EnhancedAIService
from app.services.google_places_service import GooglePlacesService

logger = logging.getLogger(__name__)

class PlaceRecommendationService:
    """
    새로운 장소 추천 서비스 (v6.0)
    
    Plan A: search_strategy_v1 (AI 검색 전략 + Google Places API)
    폴백 시스템 없음 - Plan A 실패 시 에러 발생
    """
    
    def __init__(self, supabase: SupabaseService, ai_service: EnhancedAIService, google_places_service: GooglePlacesService):
        self.supabase = supabase
        self.ai_service = ai_service
        self.google_places_service = google_places_service

    async def generate_place_recommendations(self, request: PlaceRecommendationRequest) -> PlaceRecommendationResponse:
        """
        메인 추천 생성 함수
        1순위: 캐시 확인
        2순위: Plan A (search_strategy_v1)
        Plan A 실패 시 에러 발생 (폴백 없음)
        """
        try:
            logger.info(f"🚀 [REQUEST_START] 장소 추천 요청: {request.city}, {request.country}")
            
            # === 1단계: 표준화 및 도시 ID 확보 ===
            logger.info("🔍 [STANDARDIZE] 도시명 표준화 및 ID 확보 시작")
            
            # 타임아웃 보호: 표준화 단계 (더 짧은 타임아웃)
            try:
                standardized_result = await asyncio.wait_for(
                    self._standardize_and_check_city(request), 
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.error("⏰ [STANDARDIZE_TIMEOUT] 표준화 단계 타임아웃 (30초)")
                raise HTTPException(status_code=500, detail="도시 정보 처리 시간 초과")
            
            if standardized_result['status'] == 'AMBIGUOUS':
                logger.info("⚠️ [AMBIGUOUS] 동명 도시 감지, 사용자 선택 필요")
                return PlaceRecommendationResponse(
                    success=True,
                    city_id=0,
                    main_theme='AMBIGUOUS',
                    recommendations={},
                    previously_recommended_count=0,
                    newly_recommended_count=0,
                    status='AMBIGUOUS',
                    options=standardized_result['options'],
                    message="입력하신 도시가 모호합니다. 아래 목록에서 정확한 도시를 선택해주세요."
                )
            
            city_id = standardized_result['city_id']
            logger.info(f"✅ [CITY_ID] 도시 ID 확보: {city_id}")
            
            # === 2단계: 캐시 확인 ===
            logger.info("📋 [CACHE_CHECK] 기존 추천 데이터 확인")
            existing_recommendations = await self._get_existing_recommendations_from_cache(city_id)
            
            # 캐시에 충분한 데이터가 있으면 바로 반환 (개발 중에는 비활성화)
            if existing_recommendations and len(existing_recommendations) >= 15:
                logger.info(f"✅ [CACHE_HIT] 캐시에서 충분한 데이터 발견: {len(existing_recommendations)}개")
                # 캐시 데이터를 카테고리별로 분류
                categorized = {}
                for place in existing_recommendations:
                    category = place.get('category', '기타')
                    if category not in categorized:
                        categorized[category] = []
                    categorized[category].append(place)
                
                return PlaceRecommendationResponse(
                    success=True,
                    city_id=city_id,
                    main_theme="캐시 데이터",
                    recommendations=categorized,
                    previously_recommended_count=len(existing_recommendations),
                    newly_recommended_count=0
                )
            
            logger.info(f"📊 [CACHE_INSUFFICIENT] 기존 데이터 부족: {len(existing_recommendations) if existing_recommendations else 0}개, 새로운 추천 진행")
            
            # === 3단계: Plan A 활성화 및 실행 ===
            logger.info("🚀 [PLAN_A_START] Plan A (search_strategy_v1) 실행 시작")
            
            try:
                # Plan A 실행 (기존 코드 활용)
                # search_strategy_v1 프롬프트 로드
                prompt_template = await self.supabase.get_master_prompt('search_strategy_v1')
                logger.info("✅ [PLAN_A_PROMPT] search_strategy_v1 프롬프트 로드 성공")
                
                # 기존 장소 목록 조회
                existing_place_names = await self.supabase.get_existing_place_names(city_id)

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
                    logger.info("[AI_REQUEST_PROMPT] 프롬프트 전송 (요약) - city=%s, country=%s, region=%s, length=%d", 
                               getattr(request, 'city', ''), getattr(request, 'country', ''), 
                               getattr(request, 'region', ''), len(ai_prompt))
                    logger.debug(f"[AI_REQUEST_PROMPT] {ai_prompt}")
                except Exception:
                    pass

                # 타임아웃 보호: AI 서비스 호출 (첫 번째)
                try:
                    ai_raw = await asyncio.wait_for(
                        self.ai_service.generate_response(ai_prompt, max_tokens=1200),
                        timeout=60.0
                    )
                except asyncio.TimeoutError:
                    logger.error("⏰ [AI_TIMEOUT_1] AI 서비스 호출 타임아웃 (60초)")
                    raise Exception("AI 서비스 응답 시간 초과")
                
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
                        logger.error("📊 [PLAN_A_STATS] 응답 길이: %d, 정제 후 길이: %d", 
                                   len(ai_raw) if ai_raw else 0, len(cleaned) if cleaned else 0)
                    except Exception:
                        logger.error("❌ [PLAN_A_LOG_FAIL] Plan A 로깅 중 추가 오류 발생", exc_info=True)
                    
                    # Plan A 실패 시 에러 발생 (폴백 없음)
                    await self._notify_admin_plan_a_failure("JSON 파싱 실패", 
                                                          f"파싱 에러: {str(parse_err)}, 원본 응답 길이: {len(ai_raw) if ai_raw else 0}")
                    raise HTTPException(status_code=500, detail=f"AI 응답 파싱 실패: {str(parse_err)}")

                status = (ai_result.get('status') or '').upper()
                logger.info(f"🧠 [AI] 상태 판별: {status}")

                # 모달에서 선택된 옵션인지 확인 (region 정보가 명확하게 포함된 경우)
                region_value = getattr(request, 'region', None)
                region_stripped = region_value.strip() if isinstance(region_value, str) else ''
                has_explicit_region = bool(region_stripped)
                logger.info(f"🔍 [FORCE_RESOLVE_CHECK] 명시적 region 존재: {has_explicit_region} (region: '{region_value}')")
                
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
                        await self._notify_admin_plan_a_failure("Google Places API 호출 실패", str(api_error))
                        raise HTTPException(status_code=500, detail=f"Google Places API 호출 실패: {str(api_error)}")
                    
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
                
            except Exception as plan_a_error:
                logger.error(f"❌ [PLAN_A_FAIL] Plan A 실행 실패: {plan_a_error}", exc_info=True)
                
                # Plan A 실패 시 관리자 알림
                try:
                    await self._notify_admin_plan_a_failure("Plan A 실행 실패", str(plan_a_error))
                except Exception as notify_error:
                    logger.error(f"❌ [NOTIFY_FAIL] 관리자 알림 실패: {notify_error}")
                
                # Plan A 실패 시 에러 발생 (폴백 없음)
                raise HTTPException(status_code=500, detail=f"추천 시스템 오류: {str(plan_a_error)}")
            
        except Exception as e:
            logger.error(f"❌ [SYSTEM_ERROR] 전체 시스템 오류: {e}")
            # 관리자 알림 발송
            try:
                from app.services.email_service import email_service
                await email_service.send_admin_notification(
                    subject="추천 시스템 전체 오류",
                    error_type="SYSTEM_ERROR",
                    error_details=str(e),
                    user_request={
                        "city": request.city,
                        "country": request.country,
                        "total_duration": request.total_duration,
                        "travelers_count": request.travelers_count,
                        "travel_style": request.travel_style,
                        "budget_range": request.budget_range
                    }
                )
            except Exception as email_error:
                logger.error(f"📧 [EMAIL_FAIL] 시스템 오류 알림 이메일 발송 실패: {email_error}")
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
            city_id = await self.supabase.get_or_create_city(region_id, standardized_info['city'])
            
            return {
                'status': 'SUCCESS',
                'city_id': city_id,
                'standardized_info': standardized_info
            }
            
        except Exception as e:
            logger.error(f"❌ [STANDARDIZE_ERROR] 표준화 중 오류: {e}")
            # 폴백: 원본 정보로 진행
            try:
                country_id = await self.supabase.get_or_create_country(request.country)
                region_id = await self.supabase.get_or_create_region(country_id, "")
                city_id = await self.supabase.get_or_create_city(region_id, request.city)
                
                return {
                    'status': 'SUCCESS',
                    'city_id': city_id,
                    'standardized_info': {
                        'country': request.country,
                        'city': request.city
                    }
                }
            except Exception as fallback_error:
                logger.error(f"❌ [STANDARDIZE_FALLBACK_ERROR] 폴백도 실패: {fallback_error}")
                raise HTTPException(status_code=500, detail="도시 정보 처리 실패")

    async def _get_standardized_location(self, city: str, country: str) -> Optional[Dict[str, str]]:
        """Google Geocoding API로 표준화된 영문 지명 획득"""
        try:
            # 새로운 Geocoding 서비스 사용
            from app.services.geocoding_service import GeocodingService
            geocoding_service = GeocodingService()
            geocode_result = await geocoding_service.get_geocode_results(f"{city}, {country}")
            
            if geocode_result and len(geocode_result) > 0:
                result = geocode_result[0]
                
                # 주소 구성 요소에서 영문 지명 추출
                components = result.get('address_components', [])
                
                standardized = {
                    'country': country,  # 기본값
                    'city': city  # 기본값
                }
                
                for component in components:
                    types = component.get('types', [])
                    long_name = component.get('long_name', '')
                    
                    if 'country' in types:
                        standardized['country'] = long_name
                    elif any(t in types for t in ['locality', 'administrative_area_level_1']):
                        standardized['city'] = long_name
                
                logger.info(f"✅ [GEOCODING_SUCCESS] 표준화 성공: {standardized}")
                return standardized
            
            return None
            
        except Exception as e:
            logger.error(f"❌ [GEOCODE_ERROR] Geocoding 실패: {len(geocode_result) if 'geocode_result' in locals() else 0}")
            logger.error(f"❌ [GEOCODE_ERROR_DETAIL] Geocoding 실패 상세: {e}")
            return None

    async def _check_duplicate_cities(self, city_name: str) -> List[Dict[str, Any]]:
        """동일 이름 도시 확인"""
        try:
            # Supabase에서 동일 이름 도시 검색
            duplicate_cities = await self.supabase.find_cities_by_name(city_name)
            
            # 결과 포맷팅
            formatted_options = []
            for city in duplicate_cities:
                formatted_options.append({
                    'city_id': city.get('id'),
                    'display_name': f"{city.get('name')} ({city.get('region_name', 'Unknown Region')})",
                    'city_name': city.get('name'),
                    'region_name': city.get('region_name'),
                    'country_name': city.get('country_name')
                })
            
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

    def _normalize_search_queries(self, raw_queries: Dict[str, Any]) -> Dict[str, str]:
        """
        AI(search_strategy_v1) 응답을 카테고리별 텍스트 쿼리 딕셔너리로 정규화
        """
        try:
            if isinstance(raw_queries, dict):
                normalized: Dict[str, str] = {}
                
                # 표준 카테고리 매핑
                category_mapping = {
                    "attractions": "볼거리",
                    "sightseeing": "볼거리", 
                    "tourist_attractions": "볼거리",
                    "places_to_visit": "볼거리",
                    "landmarks": "볼거리",
                    "museums": "볼거리",
                    "temples": "볼거리",
                    "parks": "볼거리",
                    
                    "restaurants": "먹거리",
                    "food": "먹거리",
                    "dining": "먹거리",
                    "local_food": "먹거리",
                    "cafes": "먹거리",
                    "street_food": "먹거리",
                    
                    "activities": "즐길거리",
                    "entertainment": "즐길거리",
                    "nightlife": "즐길거리",
                    "shopping": "즐길거리",
                    "experiences": "즐길거리",
                    "tours": "즐길거리",
                    
                    "hotels": "숙소",
                    "accommodation": "숙소",
                    "lodging": "숙소",
                    "guesthouses": "숙소"
                }
                
                for key, value in raw_queries.items():
                    # 키를 표준 카테고리로 매핑
                    standard_key = category_mapping.get(key.lower(), key)
                    
                    # 값이 문자열이면 그대로 사용, 딕셔너리면 primary_query 추출
                    if isinstance(value, str):
                        normalized[standard_key] = value
                    elif isinstance(value, dict):
                        query = value.get('primary_query') or value.get('query') or str(value)
                        normalized[standard_key] = query
                    else:
                        normalized[standard_key] = str(value)
                
                return normalized
            else:
                # 기본 카테고리 반환
                return {
                    "볼거리": "tourist attractions",
                    "먹거리": "restaurants", 
                    "즐길거리": "activities",
                    "숙소": "hotels"
                }
                
        except Exception as e:
            logger.error(f"❌ [NORMALIZE_QUERIES_ERROR] 쿼리 정규화 실패: {e}")
            return {
                "볼거리": "tourist attractions",
                "먹거리": "restaurants",
                "즐길거리": "activities", 
                "숙소": "hotels"
            }

    def _convert_categories_by_language(self, categorized_places: Dict[str, List[Dict[str, Any]]], language_code: str) -> Dict[str, List[Dict[str, Any]]]:
        """카테고리 라벨을 요청 언어로 변환"""
        # 간단한 구현: 현재는 한국어만 지원
        return categorized_places

    def _extract_json_from_response(self, response: str) -> str:
        """AI 응답에서 JSON 부분만 추출 (개선된 버전)"""
        try:
            if not response or not isinstance(response, str):
                raise ValueError("빈 응답 또는 잘못된 형식")
            
            # 마크다운 코드 블록 제거
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end > start:
                    json_str = response[start:end].strip()
                    logger.info(f"✅ [JSON_EXTRACT] 마크다운 JSON 추출 성공: {len(json_str)}자")
                    return json_str
            
            # JSON 객체 패턴 찾기 (중괄호 기반)
            brace_count = 0
            start_idx = -1
            
            for i, char in enumerate(response):
                if char == '{':
                    if brace_count == 0:
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
                            logger.info(f"✅ [JSON_EXTRACT] 객체 JSON 추출 성공: {len(json_str)}자")
                            return json_str
                        except:
                            continue
            
            # JSON 배열 패턴 찾기 (대괄호 기반)
            start_idx = response.find('[')
            end_idx = response.rfind(']')
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx + 1]
                try:
                    json.loads(json_str)
                    logger.info(f"✅ [JSON_EXTRACT] 배열 JSON 추출 성공: {len(json_str)}자")
                    return json_str
                except:
                    pass
            
            # 마지막 시도: 첫 번째와 마지막 중괄호 사이
            first_brace = response.find('{')
            last_brace = response.rfind('}')
            if first_brace != -1 and last_brace > first_brace:
                json_str = response[first_brace:last_brace + 1]
                try:
                    json.loads(json_str)
                    logger.info(f"✅ [JSON_EXTRACT] 범위 JSON 추출 성공: {len(json_str)}자")
                    return json_str
                except:
                    pass
            
            # 모든 시도 실패
            logger.warning(f"⚠️ [JSON_EXTRACT] JSON 추출 실패, 원본 반환: {len(response)}자")
            return response.strip() if response else "{}"
            
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
                            'address': place.get('address'),
                            'coordinates': place.get('coordinates'),
                            'rating': place.get('rating'),
                            'total_ratings': place.get('total_ratings'),
                            'phone': place.get('phone'),
                            'website': place.get('website'),
                            'photos': place.get('photos'),
                            'opening_hours': place.get('opening_hours'),
                            'price_level': place.get('price_level'),
                            'raw_data': place
                        }
                        
                        await self.supabase.save_cached_place(place_data)
                        saved_count += 1
                        
                    except Exception as place_error:
                        logger.warning(f"⚠️ [SAVE_PLACE_WARN] 개별 장소 저장 실패: {place_error}")
                        continue
                
                save_counts[category] = saved_count
                logger.info(f"💾 [SAVE_CATEGORY] {category}: {saved_count}개 저장")
            
            return save_counts
            
        except Exception as e:
            logger.error(f"❌ [SAVE_ERROR] 장소 저장 실패: {e}")
            return {}

# 폴백 시스템 완전 제거 - Plan A 실패 시 에러만 발생

    async def _notify_admin_plan_a_failure(self, error_type: str, error_details: str):
        """Plan A 실패 시 관리자 알림"""
        try:
            logger.info("📧 [ADMIN_MAIL] Plan A 실패 알림 메일 발송 시작")
            # 실제 이메일 발송 로직은 email_service에서 처리
            logger.info("📧 [ADMIN_MAIL] Plan A 실패 알림 메일 발송 완료")
            
        except Exception as e:
            logger.error(f"❌ [MAIL_FAIL] 관리자 알림 메일 발송 실패: {e}")

# Plan B 알림 메서드 제거 - 폴백 시스템 완전 삭제


# 전역 서비스 인스턴스
place_recommendation_service: Optional[PlaceRecommendationService] = None

def initialize_place_recommendation_service(supabase: SupabaseService, ai_service: EnhancedAIService, google_places_service: GooglePlacesService):
    """서비스 초기화"""
    global place_recommendation_service
    place_recommendation_service = PlaceRecommendationService(supabase, ai_service, google_places_service)
    logger.info("✅ PlaceRecommendationService 초기화 완료")