"""여행지 스키마"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class Destination(BaseModel):
    """여행지 정보"""
    id: str = Field(..., description="여행지 ID")
    name: str = Field(..., description="여행지 이름")
    country: str = Field(..., description="국가")
    description: str = Field(..., description="설명")
    category: str = Field(..., description="카테고리")
    popular_attractions: List[str] = Field(..., description="인기 명소")
    best_season: List[str] = Field(..., description="최적 시즌")
    average_temperature: Dict[str, str] = Field(..., description="평균 기온")
    recommended_duration: str = Field(..., description="권장 여행 기간")
    timezone: Optional[str] = Field(None, description="시간대")
    currency: Optional[str] = Field(None, description="통화")
    language: Optional[List[str]] = Field(None, description="사용 언어")
    visa_required: Optional[bool] = Field(None, description="비자 필요 여부")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "tokyo",
                "name": "도쿄",
                "country": "일본",
                "description": "일본의 현대적인 수도",
                "category": "도시",
                "popular_attractions": ["아사쿠사", "시부야", "신주쿠"],
                "best_season": ["봄", "가을"],
                "average_temperature": {"spring": "15-20°C", "summer": "25-30°C"},
                "recommended_duration": "3-5일",
                "timezone": "JST (UTC+9)",
                "currency": "JPY",
                "language": ["일본어"],
                "visa_required": False
            }
        }


class DestinationList(BaseModel):
    """여행지 목록"""
    destinations: List[Destination] = Field(..., description="여행지 목록")
    total: int = Field(..., description="전체 개수")
    page: int = Field(..., description="현재 페이지")
    size: int = Field(..., description="페이지 크기")
    total_pages: int = Field(..., description="전체 페이지 수")


class DestinationCreate(BaseModel):
    """여행지 생성 요청"""
    name: str = Field(..., description="여행지 이름")
    country: str = Field(..., description="국가")
    description: str = Field(..., description="설명")
    category: str = Field(..., description="카테고리")
    popular_attractions: List[str] = Field(..., description="인기 명소")
    best_season: List[str] = Field(..., description="최적 시즌")
    average_temperature: Dict[str, str] = Field(..., description="평균 기온")
    recommended_duration: str = Field(..., description="권장 여행 기간")


class DestinationUpdate(BaseModel):
    """여행지 업데이트 요청"""
    name: Optional[str] = Field(None, description="여행지 이름")
    description: Optional[str] = Field(None, description="설명")
    category: Optional[str] = Field(None, description="카테고리")
    popular_attractions: Optional[List[str]] = Field(None, description="인기 명소")
    best_season: Optional[List[str]] = Field(None, description="최적 시즌")
    average_temperature: Optional[Dict[str, str]] = Field(None, description="평균 기온")
    recommended_duration: Optional[str] = Field(None, description="권장 여행 기간") 