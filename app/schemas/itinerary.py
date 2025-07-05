"""여행 일정 스키마"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class TravelStyle(str, Enum):
    """여행 스타일"""
    ADVENTURE = "adventure"  # 모험형
    RELAXATION = "relaxation"  # 휴양형
    CULTURAL = "cultural"  # 문화형
    GOURMET = "gourmet"  # 미식형
    SHOPPING = "shopping"  # 쇼핑형
    NATURE = "nature"  # 자연형


class BudgetRange(str, Enum):
    """예산 범위"""
    LOW = "low"  # 저예산 (1-5만원/일)
    MEDIUM = "medium"  # 중예산 (5-15만원/일)
    HIGH = "high"  # 고예산 (15만원+/일)
    LUXURY = "luxury"


class ActivityItem(BaseModel):
    """활동 아이템"""
    time: str = Field(..., description="시간")
    activity: str = Field(..., description="활동명")
    location: str = Field(..., description="장소")
    description: str = Field(..., description="상세 설명")
    duration: str = Field(..., description="소요 시간")
    cost: Optional[str] = Field(None, description="예상 비용")
    tips: Optional[str] = Field(None, description="팁")


class DayPlan(BaseModel):
    """일별 계획"""
    day: int = Field(..., description="날짜")
    theme: str = Field(..., description="하루 테마")
    activities: List[ActivityItem] = Field(..., description="활동 목록")
    meals: Dict[str, str] = Field(..., description="식사 정보")
    transportation: List[str] = Field(..., description="교통수단")
    estimated_cost: str = Field(..., description="예상 비용")


class ItineraryPlan(BaseModel):
    """여행 계획"""
    plan_type: str = Field(..., description="계획 타입 (A 또는 B)")
    title: str = Field(..., description="계획 제목")
    concept: str = Field(..., description="계획 컨셉")
    daily_plans: List[DayPlan] = Field(..., description="일별 계획")
    total_estimated_cost: str = Field(..., description="총 예상 비용")
    highlights: List[str] = Field(..., description="하이라이트")
    recommendations: Dict[str, List[str]] = Field(..., description="추천 정보")


class ItineraryRequest(BaseModel):
    """여행 일정 생성 요청"""
    destination: Optional[str] = Field(None, description="목적지", example="도쿄")
    city: Optional[str] = Field(None, description="여행 도시 (destination과 동일)", example="도쿄")
    duration: int = Field(..., ge=1, le=30, description="여행 기간 (일)", example=3)
    travel_style: Optional[List[TravelStyle]] = Field(default=[], description="여행 스타일")
    budget_range: Optional[BudgetRange] = Field(default=BudgetRange.MEDIUM, description="예산 범위")
    travelers_count: int = Field(default=2, ge=1, le=20, description="여행자 수", example=2)
    accommodation_preference: Optional[str] = Field(None, description="숙박 선호도")
    dietary_restrictions: Optional[List[str]] = Field(None, description="식단 제한사항")
    special_interests: Optional[List[str]] = Field(None, description="특별 관심사")
    special_requests: Optional[str] = Field(None, description="특별 요청사항")
    mobility_considerations: Optional[str] = Field(None, description="이동성 고려사항")
    
    def get_destination(self) -> str:
        """destination 또는 city 중 하나를 반환"""
        return self.destination or self.city or "Unknown"
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate_destination_or_city
    
    @classmethod
    def validate_destination_or_city(cls, v):
        if isinstance(v, dict):
            destination = v.get('destination')
            city = v.get('city')
            if not destination and not city:
                raise ValueError('destination 또는 city 중 하나는 반드시 제공되어야 합니다')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "destination": "도쿄",
                "duration": 3,
                "travel_style": ["cultural", "gourmet"],
                "budget_range": "medium",
                "travelers_count": 2,
                "accommodation_preference": "호텔",
                "dietary_restrictions": ["vegetarian"],
                "special_interests": ["사진촬영", "전통문화"],
                "mobility_considerations": "대중교통 선호"
            }
        }


class ItineraryResponse(BaseModel):
    """여행 일정 생성 응답"""
    id: str = Field(..., description="일정 ID")
    request_info: ItineraryRequest = Field(..., description="요청 정보")
    plan_a: ItineraryPlan = Field(..., description="여행 계획 A")
    plan_b: ItineraryPlan = Field(..., description="여행 계획 B")
    created_at: str = Field(..., description="생성 시간 (ISO8601 문자열)")
    status: str = Field(..., description="상태")
    ai_confidence: Optional[float] = Field(None, description="AI 신뢰도 점수")
    generation_time: Optional[float] = Field(None, description="생성 소요 시간 (초)")


class GenerateRequest(BaseModel):
    """일정 생성 요청 스키마 (/generate용)"""
    city: str = Field(..., description="여행 도시")
    duration: int = Field(..., ge=1, le=30, description="여행 기간 (일)")
    special_requests: Optional[str] = Field(None, description="특별 요청사항")
    travel_style: Optional[List[str]] = Field(default=[], description="여행 스타일")
    budget_range: Optional[BudgetRange] = Field(default=BudgetRange.MEDIUM, description="예산 범위")
    travelers_count: Optional[int] = Field(default=2, description="여행자 수")


class PlaceData(BaseModel):
    """장소 데이터 스키마"""
    place_id: str = Field(..., description="구글 플레이스 ID")
    name: str = Field(..., description="장소명")
    category: str = Field(..., description="카테고리")
    lat: float = Field(..., description="위도")
    lng: float = Field(..., description="경도")
    rating: Optional[float] = Field(None, description="평점")
    address: Optional[str] = Field(None, description="주소")
    description: Optional[str] = Field(None, description="설명")


class ActivityDetail(BaseModel):
    """활동 상세 정보"""
    time: str = Field(..., description="시간")
    place_name: str = Field(..., description="장소명")
    activity_description: str = Field(..., description="활동 설명")
    transportation_details: str = Field(..., description="교통 정보")
    place_id: Optional[str] = Field(None, description="구글 플레이스 ID")
    lat: Optional[float] = Field(None, description="위도")
    lng: Optional[float] = Field(None, description="경도")


class TravelPlan(BaseModel):
    """여행 계획"""
    title: str = Field(..., description="계획 제목")
    concept: str = Field(..., description="컨셉")
    daily_plans: List[DayPlan] = Field(..., description="일일 계획 목록")
    places: List[PlaceData] = Field(..., description="포함된 장소 목록")


class GenerateResponse(BaseModel):
    """일정 생성 응답 스키마"""
    plan_a: TravelPlan = Field(..., description="1안")
    plan_b: TravelPlan = Field(..., description="2안")
    request_id: str = Field(..., description="요청 ID")
    generated_at: str = Field(..., description="생성 시간 (ISO8601 문자열)")


class OptimizeRequest(BaseModel):
    """일정 최적화 요청 스키마 (/optimize용)"""
    selected_places: List[PlaceData] = Field(..., description="선택된 장소들")
    duration: int = Field(..., ge=1, le=30, description="여행 기간")
    start_location: Optional[str] = Field(None, description="시작 지점")


class OptimizeResponse(BaseModel):
    """일정 최적화 응답 스키마"""
    optimized_plan: TravelPlan = Field(..., description="최적화된 계획")
    total_distance: Optional[str] = Field(None, description="총 이동 거리")
    total_duration: Optional[str] = Field(None, description="총 이동 시간")
    optimization_details: Optional[Dict[str, Any]] = Field(None, description="최적화 상세 정보") 