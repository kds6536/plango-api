"""여행 일정 스키마"""

from pydantic import BaseModel, Field, model_validator
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


class Destination(BaseModel):
    """목적지 정보"""
    country: str = Field(..., description="국가", example="japan")
    city: str = Field(..., description="도시", example="도쿄")
    start_date: str = Field(..., description="시작일 (YYYY-MM-DD)", example="2024-06-01")
    end_date: str = Field(..., description="종료일 (YYYY-MM-DD)", example="2024-06-05")


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
    """v6.0: 다중 목적지 지원 여행 일정 생성 요청"""
    destinations: List[Destination] = Field(..., description="목적지 목록", min_items=1)
    total_duration: int = Field(..., ge=1, le=90, description="총 여행 기간 (일)")
    travelers_count: int = Field(default=2, ge=1, le=20, description="여행자 수", example=2)
    budget_range: Optional[str] = Field(default="1000000 KRW", description="예산 범위")
    travel_style: Optional[List[str]] = Field(default=[], description="여행 스타일")
    special_requests: Optional[str] = Field(default="", description="특별 요청사항")
    language_code: Optional[str] = Field(default="ko", description="언어 코드")
    
    @model_validator(mode='before')
    @classmethod
    def validate_destinations(cls, data: Any) -> Any:
        if isinstance(data, dict):
            destinations = data.get('destinations', [])
            if not destinations:
                raise ValueError('최소 하나의 목적지가 필요합니다')
            
            # 각 목적지의 기간 계산
            total_days = 0
            for dest in destinations:
                if dest.get('start_date') and dest.get('end_date'):
                    start = datetime.strptime(dest['start_date'], '%Y-%m-%d')
                    end = datetime.strptime(dest['end_date'], '%Y-%m-%d')
                    days = (end - start).days + 1
                    total_days += days
            
            # total_duration이 계산된 값과 일치하는지 확인
            if 'total_duration' in data and data['total_duration'] != total_days:
                data['total_duration'] = total_days
                
        return data
    
    class Config:
        json_schema_extra = {
            "example": {
                "destinations": [
                    {
                        "country": "japan",
                        "city": "도쿄",
                        "start_date": "2024-06-01",
                        "end_date": "2024-06-05"
                    }
                ],
                "total_duration": 5,
                "travelers_count": 2,
                "budget_range": "1000000 KRW",
                "travel_style": ["cultural", "gourmet"],
                "special_requests": "전통문화 체험을 원합니다",
                "language_code": "ko"
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
    
    # 프론트로부터 숫자 혹은 Enum 문자열을 받을 수 있는 필드
    budget_range: Optional[Any] = Field(None, description="예산 범위 (숫자 또는 Enum)")
    
    # 내부 저장용 필드
    budget_amount: Optional[int] = Field(None, exclude=True)

    travelers_count: Optional[int] = Field(default=2, description="여행자 수")

    @model_validator(mode='before')
    @classmethod
    def convert_budget_to_range(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # 프론트에서 'budget_range' 키로 숫자 또는 문자열이 들어옴
            budget_value = data.get('budget_range')
            
            # 숫자 형태일 경우에만 변환 로직 실행
            if isinstance(budget_value, (int, str)) and str(budget_value).isdigit():
                budget_num = int(budget_value)
                
                # 원본 숫자 값을 budget_amount에 저장
                data['budget_amount'] = budget_num
                
                # budget_range 값을 Enum으로 변환하여 덮어쓰기
                if budget_num < 500000:
                    data['budget_range'] = BudgetRange.LOW
                elif budget_num < 1500000:
                    data['budget_range'] = BudgetRange.MEDIUM
                elif budget_num < 3000000:
                    data['budget_range'] = BudgetRange.HIGH
                else:
                    data['budget_range'] = BudgetRange.LUXURY
        return data


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


class RecommendationResponse(BaseModel):
    places: List[PlaceData] 