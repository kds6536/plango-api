"""간단한 여행 일정 생성 API (더미 데이터 버전)"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

app = FastAPI(title="Plango API - 간단 버전", version="1.0.0-simple")

# 간단한 요청 스키마
class SimpleItineraryRequest(BaseModel):
    destination: str
    duration: int  # 일수
    budget: str = "medium"  # low, medium, high
    travelers: int = 2

# 간단한 응답 스키마  
class SimpleItineraryResponse(BaseModel):
    id: str
    destination: str
    duration: int
    plan_a: dict
    plan_b: dict
    created_at: str

@app.get("/")
def root():
    return {"message": "Plango API 간단 버전이 작동중입니다! ✈️", "version": "1.0.0-simple"}

@app.get("/health")
def health():
    return {"status": "ok", "message": "서버 정상 작동중"}

@app.post("/api/v1/itinerary/generate", response_model=SimpleItineraryResponse)
def generate_itinerary(request: SimpleItineraryRequest):
    """간단한 여행 일정 생성 (더미 데이터)"""
    
    # 더미 데이터 생성
    plan_a = {
        "title": f"{request.destination} 문화 탐방 {request.duration}일",
        "concept": "전통 문화와 현지 음식을 중심으로 한 여행",
        "daily_plans": [
            {
                "day": i+1,
                "theme": f"{i+1}일차 - 주요 명소 탐방",
                "activities": [
                    f"09:00 - {request.destination} 대표 명소 방문",
                    f"12:00 - 현지 전통 음식 체험",
                    f"15:00 - 문화 체험 프로그램 참여",
                    f"18:00 - 현지 맛집에서 저녁 식사"
                ],
                "estimated_cost": f"{50000 * (1 if request.budget == 'low' else 2 if request.budget == 'medium' else 3):,}원"
            }
            for i in range(request.duration)
        ],
        "highlights": [f"{request.destination} 대표 명소", "현지 음식", "문화 체험"]
    }
    
    plan_b = {
        "title": f"{request.destination} 모험 여행 {request.duration}일", 
        "concept": "액티비티와 체험을 중심으로 한 여행",
        "daily_plans": [
            {
                "day": i+1,
                "theme": f"{i+1}일차 - 액티비티 체험",
                "activities": [
                    f"09:00 - {request.destination} 어드벤처 액티비티",
                    f"12:00 - 현지 길거리 음식 탐방",
                    f"15:00 - 자연 명소 트레킹",
                    f"18:00 - 현지인 추천 숨은 맛집"
                ],
                "estimated_cost": f"{60000 * (1 if request.budget == 'low' else 2 if request.budget == 'medium' else 3):,}원"
            }
            for i in range(request.duration)
        ],
        "highlights": [f"{request.destination} 자연 명소", "어드벤처", "현지 체험"]
    }
    
    response = SimpleItineraryResponse(
        id=str(uuid.uuid4()),
        destination=request.destination,
        duration=request.duration,
        plan_a=plan_a,
        plan_b=plan_b,
        created_at=datetime.now().isoformat()
    )
    
    return response

# 테스트용 더미 데이터
@app.get("/api/v1/itinerary/example")
def get_example():
    """테스트용 예시 응답"""
    return {
        "destination": "도쿄",
        "plan_a": {
            "title": "도쿄 문화 탐방 3일",
            "day1": "아사쿠사 센소지 절 → 츠키지 시장",
            "day2": "시부야 → 하라주쿠 → 메이지 신궁",
            "day3": "우에노 공원 → 도쿄 국립박물관"
        },
        "plan_b": {
            "title": "도쿄 모던 체험 3일", 
            "day1": "도쿄 스카이트리 → 긴자 쇼핑",
            "day2": "원피스 타워 → 롯폰기 힐스",
            "day3": "오다이바 → 팀랩 보더리스"
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 간단한 Plango API 서버를 시작합니다...")
    print("📍 주소: http://localhost:8001")
    print("📋 테스트 엔드포인트:")
    print("   GET  /")
    print("   GET  /health") 
    print("   POST /api/v1/itinerary/generate")
    print("   GET  /api/v1/itinerary/example")
    uvicorn.run(app, host="0.0.0.0", port=8001) 