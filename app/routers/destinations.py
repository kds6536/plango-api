"""여행지 관리 라우터"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.schemas.destination import Destination, DestinationList
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/v1/destinations", tags=["Destinations"])
logger = get_logger(__name__)


@router.get("/destinations", response_model=DestinationList)
async def get_destinations(
    country: Optional[str] = Query(None, description="국가 필터"),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(20, ge=1, le=100, description="페이지 크기")
):
    """여행지 목록 조회"""
    try:
        # 임시 데이터 (실제로는 데이터베이스에서 조회)
        destinations = [
            Destination(
                id="tokyo",
                name="도쿄",
                country="일본",
                description="일본의 현대적인 수도",
                category="도시",
                popular_attractions=["아사쿠사", "시부야", "신주쿠"],
                best_season=["봄", "가을"],
                average_temperature={"spring": "15-20°C", "summer": "25-30°C"},
                recommended_duration="3-5일"
            ),
            Destination(
                id="seoul",
                name="서울",
                country="한국",
                description="한국의 활기찬 수도",
                category="도시",
                popular_attractions=["명동", "강남", "홍대"],
                best_season=["봄", "가을"],
                average_temperature={"spring": "10-18°C", "summer": "23-28°C"},
                recommended_duration="2-4일"
            )
        ]
        
        # 필터링 적용
        if country:
            destinations = [d for d in destinations if d.country.lower() == country.lower()]
        if category:
            destinations = [d for d in destinations if d.category.lower() == category.lower()]
        
        # 페이지네이션
        start = (page - 1) * size
        end = start + size
        paginated_destinations = destinations[start:end]
        
        return DestinationList(
            destinations=paginated_destinations,
            total=len(destinations),
            page=page,
            size=size,
            total_pages=(len(destinations) + size - 1) // size
        )
        
    except Exception as e:
        logger.error(f"여행지 목록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="여행지 목록 조회 중 오류가 발생했습니다")


@router.get("/destinations/{destination_id}", response_model=Destination)
async def get_destination(destination_id: str):
    """특정 여행지 상세 정보 조회"""
    try:
        # 임시 데이터 (실제로는 데이터베이스에서 조회)
        if destination_id == "tokyo":
            destination = Destination(
                id="tokyo",
                name="도쿄",
                country="일본",
                description="일본의 현대적인 수도로, 전통과 현대가 공존하는 매력적인 도시입니다.",
                category="도시",
                popular_attractions=[
                    "아사쿠사 센소지 절",
                    "시부야 스크램블 교차로",
                    "신주쿠 고엔",
                    "츠키지 시장",
                    "도쿄 타워"
                ],
                best_season=["봄(3-5월)", "가을(9-11월)"],
                average_temperature={
                    "spring": "15-20°C",
                    "summer": "25-30°C",
                    "autumn": "18-23°C",
                    "winter": "5-12°C"
                },
                recommended_duration="3-5일"
            )
            return destination
        else:
            raise HTTPException(status_code=404, detail="여행지를 찾을 수 없습니다")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"여행지 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="여행지 조회 중 오류가 발생했습니다")


@router.get("/destinations/{destination_id}/recommendations")
async def get_destination_recommendations(destination_id: str):
    """여행지 추천 정보"""
    return {
        "destination_id": destination_id,
        "recommendations": {
            "restaurants": ["스시 다이", "이치란 라멘", "규카츠 마이센"],
            "activities": ["전통 다도 체험", "스카이트리 전망대", "하라주쿠 쇼핑"],
            "accommodations": ["도쿄역 주변 호텔", "시부야 비즈니스 호텔"],
            "transportation": ["JR 패스", "도쿄 메트로 1일권"]
        }
    } 