"""새로운 장소 관련 스키마"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union
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
    # DB에는 latitude/longitude로 저장하지만, 하위 호환을 위해 입력으로 coordinates를 허용할 수 있음
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
    region: Optional[str] = Field(None, description="지역/주/도/광역시 (선택)")
    total_duration: int = Field(..., description="총 여행 기간 (일)")
    travelers_count: int = Field(..., description="여행자 수")
    budget_range: Optional[str] = Field(None, description="예산 범위")
    budget_level: Optional[str] = Field("중간", description="예산 수준 (낮음/중간/높음)")
    travel_style: Union[List[str], str] = Field(default="관광", description="여행 스타일")
    special_requests: Optional[str] = Field(None, description="특별 요청사항")
    language_code: Optional[str] = Field("ko", description="검색/결과 언어 코드 (예: ko, ja, en, zh-CN, id, vi)")
    
    # 동명 지역 구분을 위한 필드
    place_id: Optional[str] = Field(None, description="Google Places API place_id (동명 지역 구분용)")
    
    # 일일 활동 시간 설정
    daily_start_time: Optional[str] = Field(default="09:00", description="일일 활동 시작 시간 (HH:MM)")
    daily_end_time: Optional[str] = Field(default="21:00", description="일일 활동 종료 시간 (HH:MM)")


class PlaceRecommendationResponse(BaseModel):
    """장소 추천 응답"""
    success: bool = Field(default=True, description="성공 여부")
    city_id: int = Field(..., description="도시 ID")
    city_name: Optional[str] = Field(None, description="도시명")
    country_name: Optional[str] = Field(None, description="국가명")
    main_theme: Optional[str] = Field(None, description="추천 테마")
    recommendations: Optional[Dict[str, List[Dict[str, Any]]]] = Field(None, description="카테고리별 추천 장소")
    places: Optional[List[Dict[str, Any]]] = Field(None, description="추천 장소 목록 (폴백용)")
    previously_recommended_count: int = Field(default=0, description="기존 추천 장소 수")
    newly_recommended_count: int = Field(..., description="새로 추천된 장소 수")
    
    # AMBIGUOUS(동음이의) 응답 처리를 위한 필드들 (프론트 모달 표시용)
    status: Optional[str] = Field(default=None, description="응답 상태 (예: AMBIGUOUS, SUCCESS, NOT_FOUND)")
    options: Optional[List[Union[str, Dict[str, Any]]]] = Field(
        default=None,
        description="모호한 경우 사용자가 선택할 수 있는 후보 목록 (문자열 또는 상세 객체)"
    )
    message: Optional[str] = Field(default=None, description="상태에 대한 사용자 지향 메시지")
    
    # 폴백 시스템 관련 필드
    is_fallback: Optional[bool] = Field(default=False, description="폴백 응답 여부")
    fallback_reason: Optional[str] = Field(None, description="폴백 사용 이유")
    error_details: Optional[str] = Field(None, description="오류 상세 정보 (디버깅용)")