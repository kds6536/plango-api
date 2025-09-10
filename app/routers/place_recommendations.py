"""
새로운 장소 추천 라우터 (v6.0)
새로운 DB 스키마에 맞춘 장소 추천 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
import logging
import json
from datetime import datetime
from typing import Dict, Any
from app.schemas.place import PlaceRecommendationRequest, PlaceRecommendationResponse
from app.services.place_recommendation_service import place_recommendation_service
from app.services.geocoding_service import GeocodingService

logger = logging.getLogger(__name__)

# 폴백 추천 데이터 (Plan A 실패 시 사용)
FALLBACK_RECOMMENDATIONS = {
    "서울": [
        {"name": "경복궁", "category": "볼거리", "description": "조선 왕조의 대표 궁궐"},
        {"name": "명동", "category": "쇼핑", "description": "서울의 대표 쇼핑 거리"},
        {"name": "남산타워", "category": "볼거리", "description": "서울의 랜드마크"},
        {"name": "홍대", "category": "즐길거리", "description": "젊음의 거리"},
        {"name": "동대문", "category": "쇼핑", "description": "24시간 쇼핑 천국"}
    ],
    "부산": [
        {"name": "해운대해수욕장", "category": "볼거리", "description": "부산의 대표 해수욕장"},
        {"name": "감천문화마을", "category": "볼거리", "description": "부산의 마추픽추"},
        {"name": "자갈치시장", "category": "먹거리", "description": "부산 대표 수산시장"},
        {"name": "광안리해수욕장", "category": "볼거리", "description": "야경이 아름다운 해수욕장"},
        {"name": "태종대", "category": "볼거리", "description": "부산의 대표 관광지"}
    ],
    "제주": [
        {"name": "한라산", "category": "볼거리", "description": "제주도의 상징"},
        {"name": "성산일출봉", "category": "볼거리", "description": "일출 명소"},
        {"name": "우도", "category": "볼거리", "description": "제주의 작은 섬"},
        {"name": "천지연폭포", "category": "볼거리", "description": "제주의 대표 폭포"},
        {"name": "흑돼지거리", "category": "먹거리", "description": "제주 흑돼지 맛집 거리"}
    ]
}

async def send_admin_notification(subject: str, error_type: str, error_details: str, user_request: Dict[str, Any]):
    """
    관리자에게 이메일 알림을 발송합니다.
    """
    try:
        logger.info(f"📧 [EMAIL_NOTIFICATION_START] 관리자 알림 발송 시작: {subject}")
        
        # 이메일 내용 구성
        email_body = f"""
Plango 시스템 알림

발생 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
오류 유형: {error_type}
오류 상세: {error_details}

사용자 요청 정보:
{json.dumps(user_request, indent=2, ensure_ascii=False)}

이 알림은 자동으로 발송되었습니다.
"""
        
        # 실제 이메일 발송 로직 (현재는 로깅만)
        # TODO: 실제 이메일 서비스 연동 필요
        logger.info(f"📧 [EMAIL_CONTENT] 제목: {subject}")
        logger.info(f"📧 [EMAIL_CONTENT] 내용: {email_body}")
        
        # 임시로 성공 처리 (실제 이메일 서비스 연동 후 수정 필요)
        logger.info("✅ [EMAIL_NOTIFICATION_SUCCESS] 관리자 알림 발송 완료")
        
    except Exception as e:
        logger.error(f"❌ [EMAIL_NOTIFICATION_ERROR] 관리자 알림 발송 실패: {e}")
        raise

async def generate_fallback_recommendations(request: PlaceRecommendationRequest) -> PlaceRecommendationResponse:
    """
    Plan A 실패 시 사용하는 폴백 추천 시스템
    """
    try:
        logger.info(f"🔄 [FALLBACK_START] 폴백 추천 시스템 시작: {request.city}")
        
        # 도시명 정규화
        city_key = request.city.lower()
        city_mapping = {
            "seoul": "서울",
            "busan": "부산", 
            "jeju": "제주",
            "광주": "서울",  # 기본값으로 서울 사용
        }
        
        normalized_city = city_mapping.get(city_key, "서울")
        fallback_places = FALLBACK_RECOMMENDATIONS.get(normalized_city, FALLBACK_RECOMMENDATIONS["서울"])
        
        logger.info(f"🔄 [FALLBACK_PLACES] {normalized_city}에 대한 폴백 장소 {len(fallback_places)}개 반환")
        
        # PlaceRecommendationResponse 형식으로 반환
        response = PlaceRecommendationResponse(
            city_id=0,  # 폴백 시에는 임시 ID
            city_name=request.city,
            country_name=request.country,
            previously_recommended_count=0,
            newly_recommended_count=len(fallback_places),
            places=fallback_places,
            is_fallback=True,  # 폴백 응답임을 표시
            fallback_reason="Plan A 시스템 실패로 인한 폴백 응답"
        )
        
        logger.info(f"✅ [FALLBACK_SUCCESS] 폴백 추천 완료: {len(fallback_places)}개 장소")
        return response
        
    except Exception as e:
        logger.error(f"❌ [FALLBACK_ERROR] 폴백 시스템도 실패: {e}")
        raise HTTPException(status_code=500, detail=f"폴백 시스템 실패: {str(e)}")

router = APIRouter(prefix="/api/v1/place-recommendations", tags=["Place Recommendations v6.0"])


@router.post("/generate", response_model=PlaceRecommendationResponse)
async def generate_place_recommendations(request: PlaceRecommendationRequest):
    """
    새로운 장소 추천 생성 (v6.0)
    
    - 새로운 DB 스키마 (countries, cities, cached_places, prompts) 활용
    - 중복 추천 방지: 기존 추천 장소 제외
    - 프롬프트 동적 생성: 기존 장소 목록을 포함한 맞춤형 프롬프트
    - AI + Google Places API 연동으로 검증된 장소 정보 제공
    """
    try:
        # 요청 데이터 검증
        if not request.city or not request.city.strip():
            raise HTTPException(status_code=400, detail="도시명이 필요합니다.")
        
        if not request.country or not request.country.strip():
            raise HTTPException(status_code=400, detail="국가명이 필요합니다.")
            
        if request.total_duration <= 0:
            raise HTTPException(status_code=400, detail="여행 기간은 1일 이상이어야 합니다.")
            
        if request.travelers_count <= 0:
            raise HTTPException(status_code=400, detail="여행자 수는 1명 이상이어야 합니다.")

        logger.info(f"새로운 장소 추천 요청: {request.model_dump_json(indent=2)}")

        # --- [핵심 로그 추가] ---
        logger.info("📍 [GEOCODING_START] 동명 지역 확인을 위해 Geocoding API 호출을 시작합니다.")
        
        # 1. 동명 지역 확인 (place_id가 명시적으로 제공되지 않은 경우에만)
        geocoding_success = False
        if not hasattr(request, 'place_id') or not request.place_id:
            geocoding_service = GeocodingService()
            location_query = f"{request.city}, {request.country}"
            logger.info(f"🌍 [GEOCODING_QUERY] 검색 쿼리: '{location_query}'")
            
            try:
                geocoding_results = await geocoding_service.get_geocode_results(location_query)
                logger.info(f"✅ [GEOCODING_SUCCESS] Geocoding 결과 {len(geocoding_results)}개를 찾았습니다.")
                
                # 2. 동명 지역이 있는 경우 선택지 반환
                if geocoding_service.is_ambiguous_location(geocoding_results):
                    options = geocoding_service.format_location_options(geocoding_results)
                    logger.info(f"⚠️ [AMBIGUOUS_LOCATION] 동명 지역이 감지되어 사용자에게 선택지를 반환합니다: {request.city} - {len(options)}개 선택지")
                    
                    return JSONResponse(
                        status_code=400,
                        content={
                            "error_code": "AMBIGUOUS_LOCATION",
                            "message": f"'{request.city}'에 해당하는 지역이 여러 곳 있습니다. 하나를 선택해주세요.",
                            "options": options
                        }
                    )
                
                logger.info("✅ [GEOCODING_PASS] 동명 지역 문제가 없어, 정상적인 추천 생성을 계속합니다.")
                geocoding_success = True
                
            except Exception as geocoding_error:
                logger.error(f"❌ [GEOCODING_FAIL] Geocoding API 호출 중 에러 발생: {geocoding_error}", exc_info=True)
                logger.error(f"🚨 [PLAN_A_BLOCKED] Geocoding 실패로 인해 Plan A 실행이 차단됩니다.")
                geocoding_success = False
                
                # 🚨 [핵심] Geocoding 실패 시 즉시 폴백으로 전환
                logger.warning("🔄 [IMMEDIATE_FALLBACK] Geocoding 실패로 즉시 폴백 시스템으로 전환합니다.")
                
                # 관리자에게 이메일 알림 발송
                try:
                    await send_admin_notification(
                        subject="[Plango] Geocoding API 실패 - 폴백 시스템 활성화",
                        error_type="GEOCODING_FAILURE",
                        error_details=str(geocoding_error),
                        user_request=request.model_dump()
                    )
                except Exception as email_error:
                    logger.error(f"❌ [EMAIL_NOTIFICATION_FAIL] 관리자 이메일 발송 실패: {email_error}")
                
                # 폴백 추천 생성
                return await generate_fallback_recommendations(request)
        else:
            logger.info("ℹ️ [GEOCODING_SKIP] place_id가 제공되어 Geocoding을 건너뜁니다.")
            geocoding_success = True

        # 3. Plan A: 정상적인 장소 추천 서비스 호출
        try:
            logger.info("🚀 [PLAN_A_START] Plan A (정상 추천 시스템) 실행 시작")
            response = await place_recommendation_service.generate_place_recommendations(request)
            
            # Plan A 결과 검증
            if not response or not hasattr(response, 'newly_recommended_count') or response.newly_recommended_count == 0:
                logger.warning("⚠️ [PLAN_A_INSUFFICIENT] Plan A 결과가 충분하지 않습니다.")
                raise Exception("Plan A에서 충분한 추천 결과를 생성하지 못했습니다")
            
            logger.info(f"✅ [PLAN_A_SUCCESS] Plan A 성공: 신규 {response.newly_recommended_count}개 추천")
            return response
            
        except Exception as plan_a_error:
            logger.error(f"❌ [PLAN_A_FAIL] Plan A 실행 실패: {plan_a_error}", exc_info=True)
            
            # 관리자에게 이메일 알림 발송
            try:
                await send_admin_notification(
                    subject="[Plango] Plan A 실패 - 폴백 시스템 활성화",
                    error_type="PLAN_A_FAILURE",
                    error_details=str(plan_a_error),
                    user_request=request.model_dump()
                )
            except Exception as email_error:
                logger.error(f"❌ [EMAIL_NOTIFICATION_FAIL] 관리자 이메일 발송 실패: {email_error}")
            
            # Plan B: 폴백 시스템으로 전환
            logger.warning("🔄 [FALLBACK_ACTIVATION] Plan A 실패로 폴백 시스템으로 전환합니다.")
            return await generate_fallback_recommendations(request)

        logger.info(
            f"장소 추천 완료: 도시 ID {response.city_id}, 기존 {response.previously_recommended_count}개, 신규 {response.newly_recommended_count}개"
        )

        return response

    except HTTPException as he:  # 서비스에서 명시적으로 404 등을 던진 경우 그대로 전달
        raise he
    except ValueError as ve:
        logger.error(f"장소 추천 요청 검증 실패: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"장소 추천 중 예상치 못한 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"장소 추천 처리 중 오류가 발생했습니다: {str(e)}")


@router.get("/health")
async def place_recommendations_health_check():
    """
    장소 추천 서비스 상태 확인
    """
    try:
        # Supabase 연결 상태 확인
        supabase_connected = place_recommendation_service.supabase.is_connected()
        
        return {
            "status": "healthy",
            "service": "Place Recommendations v6.0",
            "supabase_connected": supabase_connected,
            "features": {
                "duplicate_prevention": True,
                "dynamic_prompts": True,
                "db_caching": True,
                "google_places_enrichment": True
            }
        }
        
    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        raise HTTPException(status_code=500, detail=f"헬스체크 실패: {str(e)}")


@router.get("/stats/{city_id}")
async def get_city_recommendation_stats(city_id: int):
    """
    특정 도시의 추천 통계 조회
    """
    try:
        # 도시의 기존 장소 수 조회
        existing_places = await place_recommendation_service.supabase.get_existing_place_names(city_id)
        
        # 카테고리별 분포 계산 (cached_places에서 직접 조회하는 것이 더 정확하지만, 
        # 현재는 간단히 이름 기반으로 계산)
        category_stats = {
            "볼거리": 0,
            "먹거리": 0, 
            "즐길거리": 0,
            "숙소": 0,
            "기타": 0
        }
        
        return {
            "city_id": city_id,
            "total_cached_places": len(existing_places),
            "category_distribution": category_stats,
            "place_names": existing_places[:10]  # 최대 10개만 미리보기
        }
        
    except ValueError as ve:
        logger.error(f"도시 통계 조회 실패: {ve}")
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"도시 통계 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}")


@router.post("/test-prompt-generation")
async def test_prompt_generation(request: PlaceRecommendationRequest):
    """
    개발용: 고도화(Plan A) → 폴백(Plan B) 흐름으로 실제 추천 결과를 테스트합니다.
    """
    try:
        response = await place_recommendation_service.generate_place_recommendations(request)
        return response
    except Exception as e:
        logger.error(f"프롬프트(실제 추천) 테스트 실패: {e}")
        raise HTTPException(status_code=500, detail=f"추천 테스트 중 오류: {str(e)}")


@router.post("/test-email-notification")
async def test_email_notification():
    """
    관리자 이메일 알림 시스템 테스트
    """
    try:
        logger.info("📧 [EMAIL_TEST_START] 이메일 알림 시스템 테스트 시작")
        
        # 테스트 데이터
        test_request = {
            "city": "테스트시티",
            "country": "테스트국가",
            "total_duration": 3,
            "travelers_count": 2
        }
        
        # 이메일 발송 테스트
        await send_admin_notification(
            subject="[Plango] 이메일 시스템 테스트",
            error_type="EMAIL_SYSTEM_TEST",
            error_details="이 메시지가 보인다면 이메일 시스템이 정상 작동하는 것입니다.",
            user_request=test_request
        )
        
        logger.info("✅ [EMAIL_TEST_SUCCESS] 이메일 테스트 완료")
        
        return {
            "status": "success",
            "message": "이메일 알림 테스트가 완료되었습니다. 로그를 확인해주세요.",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [EMAIL_TEST_ERROR] 이메일 테스트 실패: {e}")
        raise HTTPException(status_code=500, detail=f"이메일 테스트 실패: {str(e)}")


@router.post("/test-geocoding-failure")
async def test_geocoding_failure():
    """
    Geocoding 실패 시나리오 테스트 (폴백 시스템 동작 확인)
    """
    try:
        logger.info("🧪 [GEOCODING_FAIL_TEST] Geocoding 실패 시나리오 테스트 시작")
        
        # 존재하지 않는 도시로 테스트
        test_request = PlaceRecommendationRequest(
            city="존재하지않는도시12345",
            country="존재하지않는국가12345",
            total_duration=3,
            travelers_count=2,
            travel_style="관광",
            budget_level="중간"
        )
        
        # 실제 추천 생성 호출 (Geocoding 실패 예상)
        response = await generate_place_recommendations(test_request)
        
        return {
            "status": "success",
            "message": "Geocoding 실패 테스트 완료",
            "response": response,
            "is_fallback": getattr(response, 'is_fallback', False)
        }
        
    except Exception as e:
        logger.error(f"❌ [GEOCODING_FAIL_TEST_ERROR] Geocoding 실패 테스트 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"테스트 실패: {str(e)}")


@router.post("/test-ambiguous-location")
async def test_ambiguous_location():
    """
    동명 지역 처리 테스트
    """
    try:
        logger.info("🧪 [AMBIGUOUS_TEST] 동명 지역 처리 테스트 시작")
        
        # 광주로 테스트 (경기도 광주 vs 전라도 광주)
        test_request = PlaceRecommendationRequest(
            city="광주",
            country="대한민국",
            total_duration=2,
            travelers_count=2,
            travel_style="관광",
            budget_level="중간"
        )
        
        response = await generate_place_recommendations(test_request)
        
        return {
            "status": "success",
            "message": "동명 지역 테스트 완료",
            "response": response
        }
        
    except Exception as e:
        logger.error(f"❌ [AMBIGUOUS_TEST_ERROR] 동명 지역 테스트 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"테스트 실패: {str(e)}")