"""
Google Places API 라우터
실제 장소 정보를 검색하고 조회하는 API 엔드포인트들
"""

from fastapi import APIRouter, Query, HTTPException, Path
from typing import List, Optional
import logging

from app.services.google_places_service import google_places_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/places", tags=["Places"])

@router.get("/search")
async def search_places(
    query: str = Query(..., description="검색할 장소명"),
    location: Optional[str] = Query(None, description="검색 중심 위치 (도시명 또는 주소)"),
    radius: int = Query(5000, description="검색 반경 (미터)", ge=100, le=50000),
    place_type: Optional[str] = Query(None, description="장소 타입 (restaurant, tourist_attraction 등)")
):
    """
    장소 검색 API
    
    - **query**: 검색할 장소명 (필수)
    - **location**: 검색 중심 위치 (선택)
    - **radius**: 검색 반경 (기본: 5000미터)
    - **place_type**: 장소 타입 필터 (선택)
    """
    try:
        logger.info(f"장소 검색 요청: {query}, 위치: {location}, 반경: {radius}m")
        
        places = await google_places_service.search_places(
            query=query,
            location=location,
            radius=radius,
            place_type=place_type
        )
        
        return {
            "success": True,
            "query": query,
            "location": location,
            "total_results": len(places),
            "places": places
        }
        
    except Exception as e:
        logger.error(f"장소 검색 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"장소 검색 실패: {str(e)}")

@router.get("/details/{place_id}")
async def get_place_details(
    place_id: str = Path(..., description="Google Places API 장소 ID")
):
    """
    장소 상세 정보 조회 API
    
    - **place_id**: Google Places API에서 제공하는 고유 장소 ID
    """
    try:
        logger.info(f"장소 상세 정보 요청: {place_id}")
        
        place_details = await google_places_service.get_place_details(place_id)
        
        if not place_details:
            raise HTTPException(status_code=404, detail="장소 정보를 찾을 수 없습니다.")
        
        return {
            "success": True,
            "place_id": place_id,
            "details": place_details
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"장소 상세 정보 조회 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"장소 상세 정보 조회 실패: {str(e)}")

@router.get("/attractions")
async def get_nearby_attractions(
    location: str = Query(..., description="중심 위치 (도시명 또는 주소)"),
    radius: int = Query(10000, description="검색 반경 (미터)", ge=100, le=50000)
):
    """
    주변 관광명소 검색 API
    
    - **location**: 중심 위치 (필수)
    - **radius**: 검색 반경 (기본: 10000미터)
    """
    try:
        logger.info(f"주변 관광명소 검색 요청: {location}, 반경: {radius}m")
        
        attractions = await google_places_service.get_nearby_attractions(
            location=location,
            radius=radius
        )
        
        return {
            "success": True,
            "location": location,
            "radius": radius,
            "total_results": len(attractions),
            "attractions": attractions
        }
        
    except Exception as e:
        logger.error(f"주변 관광명소 검색 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"주변 관광명소 검색 실패: {str(e)}")

@router.get("/restaurants")
async def get_nearby_restaurants(
    location: str = Query(..., description="중심 위치 (도시명 또는 주소)"),
    radius: int = Query(5000, description="검색 반경 (미터)", ge=100, le=50000)
):
    """
    주변 음식점 검색 API
    
    - **location**: 중심 위치 (필수)
    - **radius**: 검색 반경 (기본: 5000미터)
    """
    try:
        logger.info(f"주변 음식점 검색 요청: {location}, 반경: {radius}m")
        
        restaurants = await google_places_service.get_nearby_restaurants(
            location=location,
            radius=radius
        )
        
        return {
            "success": True,
            "location": location,
            "radius": radius,
            "total_results": len(restaurants),
            "restaurants": restaurants
        }
        
    except Exception as e:
        logger.error(f"주변 음식점 검색 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"주변 음식점 검색 실패: {str(e)}")

@router.get("/popular/{city}")
async def get_popular_places(
    city: str = Path(..., description="도시명"),
    category: str = Query("tourist_attraction", description="카테고리 (tourist_attraction, restaurant, shopping_mall 등)")
):
    """
    도시별 인기 장소 검색 API
    
    - **city**: 도시명 (필수)
    - **category**: 장소 카테고리 (기본: tourist_attraction)
    """
    try:
        logger.info(f"인기 장소 검색 요청: {city}, 카테고리: {category}")
        
        # 인기 장소 검색을 위한 쿼리 구성
        if category == "tourist_attraction":
            query = f"{city} 관광명소 인기"
        elif category == "restaurant":
            query = f"{city} 맛집 유명"
        elif category == "shopping_mall":
            query = f"{city} 쇼핑몰"
        else:
            query = f"{city} {category}"
        
        places = await google_places_service.search_places(
            query=query,
            location=city,
            place_type=category if category != "shopping_mall" else "shopping_mall"
        )
        
        # 평점 순으로 정렬
        sorted_places = sorted(places, key=lambda x: x.get('rating', 0), reverse=True)
        
        return {
            "success": True,
            "city": city,
            "category": category,
            "total_results": len(sorted_places),
            "popular_places": sorted_places[:10]  # 상위 10개만 반환
        }
        
    except Exception as e:
        logger.error(f"인기 장소 검색 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"인기 장소 검색 실패: {str(e)}")

@router.get("/health")
async def places_health_check():
    """
    Google Places API 서비스 상태 확인
    """
    try:
        # API 키 존재 여부 확인
        api_available = google_places_service.gmaps is not None
        
        return {
            "status": "healthy" if api_available else "degraded",
            "google_places_api": "available" if api_available else "unavailable",
            "message": "Google Places API 서비스가 정상 작동 중입니다." if api_available else "Google Places API 키가 설정되지 않았습니다."
        }
        
    except Exception as e:
        logger.error(f"Places 서비스 상태 확인 중 오류 발생: {e}")
        return {
            "status": "unhealthy",
            "google_places_api": "error",
            "message": f"서비스 오류: {str(e)}"
        } 