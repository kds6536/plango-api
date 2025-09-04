"""
새로운 여행 일정 라우터
사용자가 요청한 /generate와 /optimize 엔드포인트 구현
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Optional, List, Dict, Any
from supabase import Client
import logging

from app.schemas.itinerary import (
    ItineraryRequest,
    RecommendationResponse,
    PlaceData,
    OptimizeResponse
)
from app.services.advanced_itinerary_service import AdvancedItineraryService
from app.services.google_places_service import GooglePlacesService
from app.services.dynamic_ai_service import DynamicAIService
from app.config import settings

router = APIRouter(
    prefix="/api/v1/itinerary",
    tags=["New Itinerary"],
)

# Supabase 클라이언트를 main.py에서 주입받을 변수
supabase: Optional[Client] = None

# 서비스 인스턴스를 전역으로 관리하여 재사용
# AdvancedItineraryService는 여러 서비스에 의존하므로 요청마다 생성하는 것은 비효율적
_itinerary_service_instance = None

def get_itinerary_service():
    """
    AdvancedItineraryService의 싱글톤 인스턴스를 반환하는 의존성 함수.
    필요한 모든 하위 서비스(AI, Google)를 초기화하여 주입합니다.
    """
    global _itinerary_service_instance
    if _itinerary_service_instance is None:
        logging.info("AdvancedItineraryService 인스턴스를 생성합니다.")
        # DynamicAIService는 내부적으로 API 키를 관리하므로 인자가 필요 없습니다.
        ai_service = DynamicAIService()
        # GooglePlacesService는 config에서 API 키를 읽어옵니다.
        google_service = GooglePlacesService()
        _itinerary_service_instance = AdvancedItineraryService(ai_service, google_service)
    return _itinerary_service_instance


@router.post("/generate-recommendations", response_model=RecommendationResponse)
async def generate_recommendations(
    request: ItineraryRequest,
    service: AdvancedItineraryService = Depends(get_itinerary_service)
):
    """
    1단계: 사용자 입력을 기반으로 AI가 여행지 키워드를 추천하고, 
           Google Places API를 통해 검증된 장소 목록을 반환합니다.
    """
    try:
        logging.info(f"추천 생성 요청: {request.model_dump_json(indent=2)}")
        places_data = await service.generate_recommendations_with_details(request)
        
        if not places_data:
            raise HTTPException(status_code=404, detail="추천 장소를 생성하지 못했습니다.")
            
        return RecommendationResponse(places=places_data)

    except Exception as e:
        logging.error(f"추천 생성 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_itinerary_v2(  # 함수명 변경으로 캐시 무효화
    payload: Dict[str, Any] = Body(...),
    service: AdvancedItineraryService = Depends(get_itinerary_service)
):
    """
    2단계: 사용자가 선택한 장소 목록을 받아 AI가 최적의 경로와 일정을 생성하고,
           Google Directions API를 통해 이동 시간을 계산하여 최종 일정을 반환합니다.
    """
    try:
        # ===== 🚨 [실제 실행 경로 확인] - print로 강제 출력 =====
        print("=" * 100)
        print("🔥🔥🔥 NEW VERSION DEPLOYED! optimize_itinerary_v2 function CALLED! 🔥🔥🔥")
        print("✅✅✅ ACTUAL EXECUTION PATH: /routers/new_itinerary.py -> optimize_itinerary_v2 function CALLED! ✅✅✅")
        print("🚀 [OPTIMIZE_START] 일정 최적화 API 호출 시작")
        print(f"📋 [OPTIMIZE_PAYLOAD] 요청 페이로드: {payload}")
        print("=" * 100)
        
        logging.info("=" * 100)
        logging.info("✅✅✅ ACTUAL EXECUTION PATH: /routers/new_itinerary.py -> optimize_itinerary function CALLED! ✅✅✅")
        logging.info("🚀 [OPTIMIZE_START] 일정 최적화 API 호출 시작")
        logging.info(f"📋 [OPTIMIZE_PAYLOAD] 요청 페이로드: {payload}")
        logging.info("=" * 100)
        
        # 호환성 처리: {places:[...]} 또는 {selected_places:[...]} 모두 허용
        raw_places = payload.get("places") or payload.get("selected_places") or []
        if not isinstance(raw_places, list):
            logging.error("❌ [OPTIMIZE_ERROR] places 배열이 없거나 잘못된 형식입니다.")
            raise HTTPException(status_code=422, detail="요청 본문에 places 배열이 필요합니다.")

        logging.info(f"📍 [OPTIMIZE_PLACES] 받은 장소 개수: {len(raw_places)}")
        
        places: List[PlaceData] = [PlaceData(**p) if isinstance(p, dict) else p for p in raw_places]
        
        # 장소 이름들 로깅
        place_names = [place.name for place in places]
        logging.info(f"🏛️ [OPTIMIZE_PLACE_NAMES] 장소 목록: {place_names}")

        # 시간 제약 및 기간 기본값
        constraints = {
            "daily_start_time": payload.get("daily_start_time") or "09:00",
            "daily_end_time": payload.get("daily_end_time") or "22:00",
            "duration": int(payload.get("duration") or max(1, len(places) // 3)),
            # 날짜별 시간 제약 조건 추가
            "time_constraints": payload.get("timeConstraints") or payload.get("time_constraints") or []
        }

        logging.info(
            f"⏰ [OPTIMIZE_CONSTRAINTS] 경로 최적화 요청: 장소 {len(places)}개, 기간 {constraints['duration']}일, "
            f"시간 {constraints['daily_start_time']}~{constraints['daily_end_time']}"
        )

        if len(places) < 2:
            logging.error(f"❌ [OPTIMIZE_ERROR] 장소 개수 부족: {len(places)}개 (최소 2개 필요)")
            raise HTTPException(status_code=400, detail="최적화를 위해 최소 2곳 이상의 장소가 필요합니다.")
        
        logging.info("🔄 [OPTIMIZE_PROCESSING] create_final_itinerary 호출 시작")
        logging.info(f"🔍 [SERVICE_TYPE] 사용 중인 서비스 타입: {type(service).__name__}")
        logging.info(f"🔍 [SERVICE_MODULE] 서비스 모듈: {type(service).__module__}")
        
        # create_final_itinerary는 비동기 함수
        final_itinerary = await service.create_final_itinerary(places, constraints=constraints)
        logging.info(f"🔍 [FINAL_ITINERARY_TYPE] 반환된 final_itinerary 타입: {type(final_itinerary).__name__}")

        if not final_itinerary:
            logging.error("❌ [OPTIMIZE_FAIL] final_itinerary가 None입니다.")
            raise HTTPException(status_code=404, detail="최종 일정을 생성하지 못했습니다.")
        
        # ===== 🚨 [핵심 수정] AI 실패 감지 로직 추가 =====
        travel_plan = final_itinerary.travel_plan if hasattr(final_itinerary, 'travel_plan') else None
        if travel_plan and hasattr(travel_plan, 'days'):
            day_plans = travel_plan.days
            logging.info(f"🔍 [VALIDATION] travel_plan.days 길이: {len(day_plans)}")
            
            # 모든 날짜의 활동이 비어있는지 확인
            all_days_empty = True
            total_activities = 0
            
            for day_plan in day_plans:
                activities = getattr(day_plan, 'activities', [])
                activity_count = len(activities) if activities else 0
                total_activities += activity_count
                logging.info(f"  - {day_plan.day}일차: {activity_count}개 활동")
                
                if activity_count > 0:
                    all_days_empty = False
            
            logging.info(f"🔍 [VALIDATION] 총 활동 수: {total_activities}, 모든 날짜 비어있음: {all_days_empty}")
            
            # 🚨 [핵심] AI가 빈 일정을 반환한 경우 에러 발생
            if all_days_empty or total_activities == 0:
                logging.error("❌ [AI_EMPTY_RESULT] AI가 유효한 일정을 생성하지 못했습니다 (모든 날짜의 활동이 비어있음)")
                raise HTTPException(
                    status_code=500, 
                    detail="AI가 일정을 생성하지 못했습니다. 장소 수를 줄이거나 다시 시도해주세요."
                )
            
            logging.info(f"✅ [OPTIMIZE_SUCCESS] 최종 일정 생성 완료: {len(day_plans)}일 일정, 총 {total_activities}개 활동")
        else:
            logging.warning("⚠️ [OPTIMIZE_WARNING] final_itinerary는 있지만 travel_plan 구조가 예상과 다릅니다.")
            logging.info(f"🔍 [OPTIMIZE_DEBUG] final_itinerary 타입: {type(final_itinerary)}")
            logging.info(f"🔍 [OPTIMIZE_DEBUG] final_itinerary 속성: {dir(final_itinerary)}")
            
            # travel_plan이 없거나 구조가 다른 경우도 에러로 처리
            raise HTTPException(
                status_code=500, 
                detail="일정 데이터 구조에 문제가 있습니다. 다시 시도해주세요."
            )

        return final_itinerary

    except Exception as e:
        logging.error(f"경로 최적화 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 