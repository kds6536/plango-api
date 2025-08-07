"""새로운 장소 관련 스키마"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


class Country(BaseModel):
    """국가 정보"""
    id: Optional[int] = Field(None, description="국가 ID")
    name: str = Field(..., description="국가명")
    created_at: Optional[datetime] = Field(None, description="생성일시")
    updated_at: Optional[datetime] = Field(None, description="수정일시")


class City(BaseModel):
    """도시 정보"""
    id: Optional[int] = Field(None, description="도시 ID")
    name: str = Field(..., description="도시명")
    country_id: int = Field(..., description="국가 ID (Foreign Key)")
    created_at: Optional[datetime] = Field(None, description="생성일시")
    updated_at: Optional[datetime] = Field(None, description="수정일시")


class CachedPlace(BaseModel):
    """캐시된 장소 정보"""
    id: Optional[int] = Field(None, description="장소 캐시 ID")
    city_id: int = Field(..., description="도시 ID (Foreign Key)")
    place_id: str = Field(..., description="Google Places API 장소 ID")
    name: str = Field(..., description="장소명")
    category: str = Field(..., description="카테고리 (볼거리, 먹거리, 즐길거리, 숙소)")
    address: Optional[str] = Field(None, description="주소")
    coordinates: Optional[Dict[str, float]] = Field(None, description="좌표 (lat, lng)")
    rating: Optional[float] = Field(None, description="평점")
    total_ratings: Optional[int] = Field(None, description="총 평가 수")
    phone: Optional[str] = Field(None, description="전화번호")
    website: Optional[str] = Field(None, description="웹사이트")
    photos: Optional[List[str]] = Field(None, description="사진 URL 목록")
    opening_hours: Optional[Dict[str, Any]] = Field(None, description="운영 시간")
    price_level: Optional[int] = Field(None, description="가격 수준 (0-4)")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Google API 원본 데이터")
    created_at: Optional[datetime] = Field(None, description="생성일시")
    updated_at: Optional[datetime] = Field(None, description="수정일시")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "city_id": 1,
                "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
                "name": "경복궁",
                "category": "볼거리",
                "address": "서울 종로구 사직로 161",
                "coordinates": {
                    "lat": 37.5788,
                    "lng": 126.9770
                },
                "rating": 4.5,
                "total_ratings": 25000,
                "phone": "+82-2-3700-3900",
                "website": "https://www.royalpalace.go.kr",
                "photos": ["https://example.com/photo1.jpg"],
                "opening_hours": {
                    "weekday_text": ["월: 09:00-18:00", "화: 09:00-18:00"]
                },
                "price_level": 2
            }
        }


class Prompt(BaseModel):
    """프롬프트 정보"""
    id: Optional[int] = Field(None, description="프롬프트 ID")
    name: str = Field(..., description="프롬프트 이름")
    value: str = Field(..., description="프롬프트 내용")
    description: Optional[str] = Field(None, description="프롬프트 설명")
    created_at: Optional[datetime] = Field(None, description="생성일시")
    updated_at: Optional[datetime] = Field(None, description="수정일시")


# 요청/응답 스키마
class PlaceRecommendationRequest(BaseModel):
    """장소 추천 요청"""
    country: str = Field(..., description="국가명")
    city: str = Field(..., description="도시명")
    total_duration: int = Field(..., description="총 여행 기간 (일)")
    travelers_count: int = Field(..., description="여행자 수")
    budget_range: str = Field(..., description="예산 범위")
    travel_style: List[str] = Field(default_factory=list, description="여행 스타일 목록")
    special_requests: Optional[str] = Field(None, description="특별 요청사항")


class PlaceRecommendationResponse(BaseModel):
    """장소 추천 응답"""
    success: bool = Field(..., description="성공 여부")
    city_id: int = Field(..., description="도시 ID")
    main_theme: Optional[str] = Field(None, description="추천 테마")
    recommendations: Dict[str, List[Dict[str, Any]]] = Field(..., description="카테고리별 추천 장소")
    previously_recommended_count: int = Field(..., description="기존 추천 장소 수")
    newly_recommended_count: int = Field(..., description="새로 추천된 장소 수")