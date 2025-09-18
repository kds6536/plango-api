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
from app.services.place_recommendation_service_v2 import PlaceRecommendationServiceV2
from app.services.supabase_service import SupabaseService
from app.services.ai_service import AIService
from app.services.google_places_service import GooglePlacesService
from app.services.geocoding_service import GeocodingService
from app.services.email_service import email_service

# Enhanced AI Service 의존성 주입을 위한 import
try:
    from app.services.enhanced_ai_service import enhanced_ai_service
except ImportError:
    enhanced_ai_service = None

logger = logging.getLogger(__name__)

# 의존성 주입 함수들
async def get_active_ai_handler():
    """
    Enhanced AI Service에서 활성화된 AI 핸들러를 가져오는 의존성 주입 함수
    """
    try:
        if enhanced_ai_service:
            handler = await enhanced_ai_service.get_active_handler()
            if handler:
                logger.info("✅ [DI_SUCCESS] AI 핸들러 의존성 주입 성공")
                return handler
        
        logger.warning("⚠️ [DI_FALLBACK] AI 핸들러를 가져올 수 없어 None 반환")
        return None
        
    except Exception as e:
        logger.error(f"❌ [DI_ERROR] AI 핸들러 의존성 주입 실패: {e}")
        return None

async def send_admin_notification(subject: str, error_type: str, error_details: str, user_request: dict) -> bool:
    """
    통합된 관리자 알림 이메일 발송 함수 (중복 방지)
    """
    try:
        logger.info(f"📧 [EMAIL_START] 관리자 알림 발송: {subject}")
        
        success = await email_service.send_admin_notification(
            subject=f"[PLANGO] {subject}",
            error_type=error_type,
            error_details=error_details,
            user_request=user_request
        )
        
        if success:
            logger.info("✅ [EMAIL_SUCCESS] 관리자 이메일 발송 완료")
        else:
            logger.error("❌ [EMAIL_FAIL] 관리자 이메일 발송 실패")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ [EMAIL_ERROR] 이메일 발송 중 예외: {e}", exc_info=True)
        return False

# 폴백 추천 함수 완전 제거됨

router = APIRouter(prefix="/api/v1/place-recommendations", tags=["Place Recommendations v6.0"])

# 서비스 인스턴스 초기화
place_recommendation_service_v2 = None

def get_place_recommendation_service():
    """PlaceRecommendationServiceV2 인스턴스를 반환하는 의존성 함수"""
    global place_recommendation_service_v2
    if place_recommendation_service_v2 is None:
        try:
            logger.info("🔧 [V2] PlaceRecommendationServiceV2 초기화 시작")
            
            # Supabase 서비스 초기화
            supabase_service = SupabaseService()
            logger.info("✅ [V2] Supabase 서비스 초기화 완료")
            
            # AI 서비스 초기화
            try:
                from app.services.enhanced_ai_service import EnhancedAIService
                ai_service = EnhancedAIService()
                logger.info("✅ [V2] Enhanced AI 서비스 초기화 완료")
            except Exception as ai_init_error:
                logger.error(f"❌ [V2] Enhanced AI 서비스 초기화 실패: {ai_init_error}")
                raise Exception(f"AI 서비스 초기화 실패: {str(ai_init_error)}")
            
            # Google Places 서비스 초기화  
            google_places_service = GooglePlacesService()
            logger.info("✅ [V2] Google Places 서비스 초기화 완료")
            
            # PlaceRecommendationServiceV2 초기화
            place_recommendation_service_v2 = PlaceRecommendationServiceV2(
                supabase=supabase_service,
                ai_service=ai_service,
                google_places_service=google_places_service
            )
            
            logger.info("✅ [V2] PlaceRecommendationServiceV2 초기화 완료")
            
        except Exception as e:
            logger.error(f"❌ [V2] PlaceRecommendationServiceV2 초기화 실패: {e}")
            return None
    
    return place_recommendation_service_v2


@router.post("/generate", response_model=PlaceRecommendationResponse)
async def generate_place_recommendations(request: PlaceRecommendationRequest):
    """
    최적화된 장소 추천 생성 (v2.0)
    
    전제: 프론트엔드에서 항상 Google Places Autocomplete를 통해 place_id 제공
    
    흐름:
    1. place_id 검증
    2. 캐시 확인
    3. AI 키워드 생성
    4. Google Places 검색
    5. 결과 반환
    """
    logger.info("🚀 [V2_START] 최적화된 추천 생성 API 시작")
    
    try:
        # 기본 요청 데이터 검증
        if not request.city or not request.city.strip():
            raise HTTPException(status_code=400, detail="도시명이 필요합니다.")
        
        if not request.country or not request.country.strip():
            raise HTTPException(status_code=400, detail="국가명이 필요합니다.")
            
        if request.total_duration <= 0:
            raise HTTPException(status_code=400, detail="여행 기간은 1일 이상이어야 합니다.")
            
        if request.travelers_count <= 0:
            raise HTTPException(status_code=400, detail="여행자 수는 1명 이상이어야 합니다.")

        logger.info(f"📝 [V2_REQUEST] 요청 데이터: {request.city}, {request.country}, place_id: {getattr(request, 'place_id', 'None')}")
        
        # 서비스 초기화
        service = get_place_recommendation_service()
        if service is None:
            raise HTTPException(status_code=500, detail="서비스 초기화 실패")
        
        # V2 서비스로 추천 생성
        recommendations = await service.generate_place_recommendations(request)
        
        logger.info("✅ [V2_SUCCESS] 최적화된 추천 생성 완료!")
        return recommendations
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [V2_ERROR] 추천 생성 실패: {e}", exc_info=True)
        
        # 관리자 알림 발송
        await send_admin_notification("V2 추천 생성 실패", "V2_GENERATION_FAILURE", str(e), request.model_dump())
        
        raise HTTPException(status_code=500, detail="추천 생성 중 오류가 발생했습니다.")


@router.get("/health")
async def place_recommendations_health_check():
    """
    장소 추천 서비스 상태 확인
    """
    try:
        # 서비스 초기화 시도
        service = get_place_recommendation_service()
        
        if service is None:
            return {
                "status": "degraded",
                "service": "Place Recommendations v2.0 (Optimized)",
                "supabase_connected": False,
                "error": "Service initialization failed",
                "features": {
                    "google_places_autocomplete_required": False,
                    "simplified_architecture": False,
                    "no_geocoding_needed": False,
                    "no_ambiguous_handling": False,
                    "ai_powered_keywords": False,
                    "db_caching": False,
                    "google_places_enrichment": False
                }
            }
        
        # Supabase 연결 상태 확인
        try:
            test_query = service.supabase.supabase.table('countries').select('id').limit(1).execute()
            supabase_connected = True
        except:
            supabase_connected = False
        
        return {
            "status": "healthy",
            "service": "Place Recommendations v2.0 (Optimized)",
            "supabase_connected": supabase_connected,
            "features": {
                "google_places_autocomplete_required": True,
                "simplified_architecture": True,
                "no_geocoding_needed": True,
                "no_ambiguous_handling": True,
                "ai_powered_keywords": True,
                "db_caching": True,
                "google_places_enrichment": True
            }
        }
        
    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        return {
            "status": "unhealthy",
            "service": "Place Recommendations v2.0 (Optimized)",
            "error": str(e),
            "supabase_connected": False
        }


@router.get("/stats/{city_id}")
async def get_city_recommendation_stats(
    city_id: int,
    service: PlaceRecommendationServiceV2 = Depends(get_place_recommendation_service)
):
    """
    특정 도시의 추천 통계 조회
    """
    try:
        # 도시의 기존 장소 수 조회
        existing_places = await service.supabase.get_existing_place_names(city_id)
        
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
async def test_prompt_generation(
    request: PlaceRecommendationRequest,
    service: PlaceRecommendationServiceV2 = Depends(get_place_recommendation_service)
):
    """
    개발용: 고도화(Plan A) → 폴백(Plan B) 흐름으로 실제 추천 결과를 테스트합니다.
    """
    try:
        response = await service.generate_place_recommendations(request)
        return response
    except Exception as e:
        logger.error(f"프롬프트(실제 추천) 테스트 실패: {e}")
        raise HTTPException(status_code=500, detail=f"추천 테스트 중 오류: {str(e)}")


@router.post("/test-email-notification")
async def test_email_notification():
    """
    관리자 이메일 알림 시스템 테스트 (실제 이메일 발송)
    """
    try:
        logger.info("📧 [EMAIL_TEST_START] 실제 이메일 발송 테스트 시작")
        
        # 이메일 서비스 연결 테스트
        from app.services.email_service import email_service
        
        connection_test = await email_service.test_email_connection()
        if not connection_test["success"]:
            return {
                "status": "connection_failed",
                "message": f"이메일 서버 연결 실패: {connection_test['error']}",
                "timestamp": datetime.now().isoformat()
            }
        
        # 테스트 데이터
        test_request = {
            "city": "테스트시티",
            "country": "테스트국가",
            "total_duration": 3,
            "travelers_count": 2,
            "test_timestamp": datetime.now().isoformat()
        }
        
        # 실제 이메일 발송 테스트
        success = await send_admin_notification(
            subject="[Plango] 이메일 시스템 테스트",
            error_type="EMAIL_SYSTEM_TEST",
            error_details="이 메시지가 보인다면 이메일 시스템이 정상 작동하는 것입니다.",
            user_request=test_request
        )
        
        if success:
            logger.info("✅ [EMAIL_TEST_SUCCESS] 실제 이메일 발송 테스트 성공")
            return {
                "status": "success",
                "message": "이메일이 성공적으로 발송되었습니다. 관리자 이메일을 확인해주세요.",
                "admin_email": email_service.admin_email,
                "timestamp": datetime.now().isoformat()
            }
        else:
            logger.error("❌ [EMAIL_TEST_FAILED] 이메일 발송 실패")
            return {
                "status": "send_failed",
                "message": "이메일 발송에 실패했습니다. 로그를 확인해주세요.",
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        logger.error(f"❌ [EMAIL_TEST_ERROR] 이메일 테스트 중 예외: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"이메일 테스트 실패: {str(e)}")


@router.post("/test-geocoding-failure")
async def test_geocoding_failure():
    """
    Geocoding 실패 시나리오 테스트 (에러 발생 확인)
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
        try:
            response = await generate_place_recommendations(test_request)
            return {
                "status": "unexpected_success",
                "message": "예상과 달리 성공했습니다",
                "response": response
            }
        except HTTPException as e:
            return {
                "status": "expected_failure",
                "message": "예상대로 실패했습니다",
                "error_code": e.status_code,
                "error_detail": e.detail
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
        
        # Geocoding 서비스 직접 테스트
        geocoding_service = GeocodingService()
        location_query = f"{test_request.city}, {test_request.country}"
        
        try:
            geocoding_results = await geocoding_service.get_geocode_results(location_query)
            
            # 동명 지역 확인
            if geocoding_service.is_ambiguous_location(geocoding_results):
                # 중복 제거된 결과로 선택지 생성
                unique_results = geocoding_service.remove_duplicate_results(geocoding_results)
                options = geocoding_service.format_location_options(unique_results)
                return JSONResponse(
                    status_code=400,
                    content={
                        "error_code": "AMBIGUOUS_LOCATION",
                        "message": f"'{test_request.city}'에 해당하는 지역이 여러 곳 있습니다. 하나를 선택해주세요.",
                        "options": options
                    }
                )
            else:
                return {
                    "status": "success",
                    "message": "동명 지역이 아닙니다.",
                    "results_count": len(geocoding_results),
                    "results": geocoding_results
                }
                
        except Exception as e:
            logger.error(f"Geocoding 테스트 실패: {e}")
            return {
                "status": "geocoding_failed",
                "message": "Geocoding API 호출 실패",
                "error": str(e)
            }
        
        return {
            "status": "success",
            "message": "동명 지역 테스트 완료",
            "response": response
        }
        
    except Exception as e:
        logger.error(f"❌ [AMBIGUOUS_TEST_ERROR] 동명 지역 테스트 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"테스트 실패: {str(e)}")