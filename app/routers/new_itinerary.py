"""
새로운 여행 일정 라우터
사용자가 요청한 /generate와 /optimize 엔드포인트 구현
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
import logging
import time
import json

from app.schemas.itinerary import (
    GenerateRequest, GenerateResponse, 
    OptimizeRequest, OptimizeResponse
)
from app.services.advanced_itinerary_service import AdvancedItineraryService
from app.utils.logger import get_logger

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/itinerary", tags=["새로운 여행 일정"])


# 서비스 인스턴스 생성
ai_service = None
google_places_service = None
itinerary_service = None
advanced_itinerary_service = None

try:
    import app.main
    app = app.main.app
    from app.services.ai_service import AIService
    from app.services.google_places_service import GooglePlacesService
    from app.services.itinerary_service import ItineraryService
    from app.config import settings

    ai_service = AIService(api_key=settings.OPENAI_API_KEY)
    google_places_service = GooglePlacesService(api_key=settings.MAPS_PLATFORM_API_KEY)
    itinerary_service = ItineraryService(
        ai_service=ai_service,
        google_places_service=google_places_service
    )
    advanced_itinerary_service = AdvancedItineraryService(
        ai_service=ai_service,
        google_places_service=google_places_service
    )
except Exception:
    pass


# 서비스 의존성
def get_itinerary_service() -> AdvancedItineraryService:
    return advanced_itinerary_service


@router.post("/generate", response_model=GenerateResponse)
async def generate_itinerary(
    request: GenerateRequest,
    service: AdvancedItineraryService = Depends(get_itinerary_service)
):
    """
    4단계 프로세스로 여행 일정을 생성합니다:
    1. AI 브레인스토밍 - 장소 이름 후보군 생성
    2. 구글 플레이스 API 정보 강화 - 실제 데이터 부여  
    3. AI 큐레이션 - 1안/2안 분할 및 상세 일정 구성
    4. 최종 JSON 조립 및 반환
    """
    start_time = time.time()
    
    try:
        # === Railway 로그: 라우터 요청 시작 ===
        logger.info("=" * 100)
        logger.info(f"🌐 [ROUTER_START] 여행 일정 생성 API 요청 접수")
        logger.info(f"🏙️ [REQUEST_CITY] {request.city}")
        logger.info(f"📅 [REQUEST_DURATION] {request.duration}일")
        logger.info(f"💰 [REQUEST_BUDGET] {request.budget_range}")
        logger.info(f"👥 [REQUEST_TRAVELERS] {request.travelers_count}명")
        logger.info(f"🎨 [REQUEST_STYLE] {request.travel_style}")
        logger.info(f"📝 [REQUEST_SPECIAL] {request.special_requests}")
        logger.info("=" * 100)
        
        # 입력 검증
        logger.info(f"🔍 [VALIDATION_START] 입력 데이터 검증 시작")
        if not request.city or not request.city.strip():
            logger.error(f"❌ [VALIDATION_ERROR] 도시명이 누락됨")
            raise HTTPException(status_code=400, detail="도시명이 필요합니다")
        
        if request.duration < 1 or request.duration > 30:
            logger.error(f"❌ [VALIDATION_ERROR] 여행 기간 범위 초과: {request.duration}일")
            raise HTTPException(status_code=400, detail="여행 기간은 1-30일 사이여야 합니다")
        
        logger.info(f"✅ [VALIDATION_SUCCESS] 입력 데이터 검증 완료")
        
        # 4단계 프로세스 실행
        logger.info(f"🚀 [SERVICE_START] AdvancedItineraryService 4단계 프로세스 시작")
        response = await service.generate_itinerary(request)
        
        generation_time = time.time() - start_time
        logger.info("=" * 100)
        logger.info(f"🎉 [ROUTER_SUCCESS] 여행 일정 생성 API 완료: {generation_time:.2f}초")
        logger.info(f"📋 [RESPONSE_PLAN_A] {response.plan_a.title}")
        logger.info(f"📋 [RESPONSE_PLAN_B] {response.plan_b.title}")
        logger.info(f"🆔 [RESPONSE_ID] {response.request_id}")
        logger.info("=" * 100)
        
        return response
        
    except HTTPException as he:
        # === Railway 로그: HTTP 예외 ===
        logger.error("=" * 100)
        logger.error(f"⚠️ [HTTP_EXCEPTION] HTTP 예외 발생")
        logger.error(f"🔢 [STATUS_CODE] {he.status_code}")
        logger.error(f"📝 [DETAIL] {he.detail}")
        logger.error("=" * 100)
        raise
    except Exception as e:
        # === Railway 로그: 서버 에러 ===
        generation_time = time.time() - start_time
        logger.error("=" * 100)
        logger.error(f"💥 [SERVER_ERROR] 여행 일정 생성 서버 오류 발생")
        logger.error(f"⏱️ [ERROR_TIME] {generation_time:.2f}초 경과 후 실패")
        logger.error(f"🚨 [ERROR_TYPE] {type(e).__name__}")
        logger.error(f"📝 [ERROR_MESSAGE] {str(e)}")
        import traceback
        logger.error(f"🔍 [ERROR_TRACEBACK] {traceback.format_exc()}")
        logger.error("=" * 100)
        raise HTTPException(
            status_code=500, 
            detail=f"여행 일정 생성 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_itinerary(
    request: OptimizeRequest,
    service: AdvancedItineraryService = Depends(get_itinerary_service)
):
    """
    선택된 장소들을 구글 다이렉션 API로 최적화합니다:
    1. 구글 다이렉션 API 동선 최적화
    2. 최종 일정 재구성
    """
    start_time = time.time()
    
    try:
        logger.info(f"🎯 경로 최적화 요청: {len(request.selected_places)}개 장소")
        
        # 입력 검증
        if not request.selected_places:
            raise HTTPException(status_code=400, detail="선택된 장소가 없습니다")
        
        if len(request.selected_places) < 2:
            raise HTTPException(status_code=400, detail="최소 2개 이상의 장소가 필요합니다")
        
        if request.duration < 1 or request.duration > 30:
            raise HTTPException(status_code=400, detail="여행 기간은 1-30일 사이여야 합니다")
        
        # 경로 최적화 실행
        response = await service.optimize_itinerary(request)
        
        optimization_time = time.time() - start_time
        logger.info(f"✅ 경로 최적화 완료: {optimization_time:.2f}초")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 경로 최적화 실패: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"경로 최적화 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """API 상태 확인"""
    return {
        "status": "healthy",
        "service": "Plango New Itinerary API",
        "endpoints": [
            "/api/v1/itinerary/generate",
            "/api/v1/itinerary/optimize"
        ],
        "description": "4단계 프로세스 여행 일정 생성 API"
    }


@router.get("/info")
async def get_api_info():
    """API 정보 및 사용법"""
    return {
        "api_name": "Plango Advanced Itinerary API",
        "version": "1.0.0",
        "description": "사용자가 요청한 4단계 프로세스를 구현한 여행 일정 생성 API",
        "endpoints": {
            "/generate": {
                "method": "POST",
                "description": "4단계 프로세스로 1안/2안 여행 일정 생성",
                "process": [
                    "1단계: AI 브레인스토밍 - 장소 이름 후보군 생성",
                    "2단계: 구글 플레이스 API 정보 강화 - 실제 데이터 부여",
                    "3단계: AI 큐레이션 - 1안/2안 분할 및 상세 일정 구성",
                    "4단계: 최종 JSON 조립 및 반환"
                ],
                "input": {
                    "city": "여행 도시 (필수)",
                    "duration": "여행 기간 1-30일 (필수)",
                    "special_requests": "특별 요청사항 (선택)",
                    "travel_style": "여행 스타일 목록 (선택)",
                    "budget_range": "예산 범위 (선택)",
                    "travelers_count": "여행자 수 (선택)"
                }
            },
            "/optimize": {
                "method": "POST", 
                "description": "선택된 장소들을 구글 다이렉션 API로 최적화",
                "process": [
                    "1단계: 구글 다이렉션 API 동선 최적화",
                    "2단계: 최종 일정 재구성"
                ],
                "input": {
                    "selected_places": "선택된 장소 목록 (필수)",
                    "duration": "여행 기간 1-30일 (필수)",
                    "start_location": "시작 지점 (선택)"
                }
            }
        },
        "features": [
            "AI 기반 브레인스토밍으로 다양한 장소 후보 생성",
            "구글 플레이스 API로 실제 장소 데이터 강화",
            "AI 큐레이션으로 개성 있는 1안/2안 생성",
            "구글 다이렉션 API로 동선 최적화",
            "완전한 JSON 응답으로 프론트엔드 연동 용이"
        ]
    } 