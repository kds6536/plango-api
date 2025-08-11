"""
새로운 여행 일정 라우터
사용자가 요청한 /generate와 /optimize 엔드포인트 구현
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Optional, List
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
async def optimize_itinerary(
    places: List[PlaceData] = Body(..., embed=True),
    service: AdvancedItineraryService = Depends(get_itinerary_service)
):
    """
    2단계: 사용자가 선택한 장소 목록을 받아 AI가 최적의 경로와 일정을 생성하고,
           Google Directions API를 통해 이동 시간을 계산하여 최종 일정을 반환합니다.
    """
    try:
        logging.info(f"경로 최적화 요청: {len(places)}개의 장소")
        
        if len(places) < 2:
            raise HTTPException(status_code=400, detail="최적화를 위해 최소 2곳 이상의 장소가 필요합니다.")
        
        # create_final_itinerary는 비동기 함수이므로 await가 필요합니다.
        final_itinerary = await service.create_final_itinerary(places)

        if not final_itinerary:
            raise HTTPException(status_code=404, detail="최종 일정을 생성하지 못했습니다.")

        return final_itinerary

    except Exception as e:
        logging.error(f"경로 최적화 중 오류 발생: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 