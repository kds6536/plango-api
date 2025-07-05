"""여행 일정 생성 라우터 - AdvancedItineraryService 사용"""

import os
import json
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List
from datetime import datetime
import uuid
import traceback

from app.schemas.itinerary import (
    ItineraryRequest,
    ItineraryResponse,
    GenerateRequest,
    GenerateResponse
)

# AdvancedItineraryService import
from app.services.advanced_itinerary_service import AdvancedItineraryService

router = APIRouter(prefix="/api/v1/itinerary", tags=["여행 일정 API"])

# AdvancedItineraryService 인스턴스 생성
itinerary_service = AdvancedItineraryService()


@router.post("/generate", response_model=ItineraryResponse) 
async def generate_itinerary(
    request: ItineraryRequest,
    provider: str = Query(
        "gemini", 
        enum=["openai", "gemini"], 
        description="사용할 AI 공급자를 선택하세요 (openai 또는 gemini)"
    )
):
    """
    여행 일정을 생성합니다.
    AdvancedItineraryService를 사용하여 4단계 프로세스로 생성:
    1. AI 브레인스토밍 - 장소 추천
    2. Google Places API - 정보 강화
    3. AI 큐레이션 - 최적 일정 구성
    4. 최종 JSON 조립
    """
    print(f"🎯 GEMINI를 사용하여 여행 일정 생성 시작!")
    print(f"📍 목적지: {request.get_destination()}")
    print(f"⏰ 기간: {request.duration}일")
    print(f"🎨 스타일: {request.travel_style}")
    print(f"💰 예산: {request.budget_range}")
    
    try:
        # ItineraryRequest를 GenerateRequest로 변환
        generate_request = GenerateRequest(
            city=request.get_destination(),
            duration=request.duration,
            budget_range=request.budget_range,
            travelers_count=request.travelers_count,
            accommodation_preference=request.accommodation_preference,
            travel_style=request.travel_style,
            special_requests=", ".join(request.special_interests) if request.special_interests else None
        )
        
        print(f"🔄 AdvancedItineraryService로 여행 일정 생성 중...")
        
        # AdvancedItineraryService 사용
        generate_response = await itinerary_service.generate_itinerary(generate_request)
        
        print(f"✅ 여행 일정 생성 완료!")
        
        # GenerateResponse를 ItineraryResponse로 변환
        itinerary_response = ItineraryResponse(
            id=generate_response.id,
            destination=request.get_destination(),
            duration=request.duration,
            created_at=generate_response.created_at,
            plan_a=generate_response.plan_a,
            plan_b=generate_response.plan_b,
            provider="gemini",  # provider 정보 추가
            success=True,
            message="여행 일정이 성공적으로 생성되었습니다."
        )
        
        return itinerary_response
        
    except Exception as e:
        print(f"❌ 여행 일정 생성 실패: {str(e)}")
        print("Traceback:")
        traceback.print_exc()
        
        # 실패 시 기본 응답 반환
        return create_fallback_response(request, provider)


def create_fallback_response(request: ItineraryRequest, provider: str):
    """에러 발생 시 기본 응답을 생성합니다."""
    return ItineraryResponse(
        id=str(uuid.uuid4()),
        destination=request.get_destination(),
        duration=request.duration,
        created_at=datetime.now().isoformat(),
        plan_a={
            "plan_type": "classic",
            "title": f"{request.get_destination()} 클래식 여행",
            "concept": "전통적이고 안정적인 여행 코스",
            "daily_plans": [
                {
                    "day": i+1,
                    "theme": f"{i+1}일차 여행",
                    "activities": [
                        {
                            "time": "09:00",
                            "activity": f"{request.get_destination()} 대표 관광지 방문",
                            "location": f"{request.get_destination()} 중심가",
                            "description": "대표적인 관광지를 둘러보며 현지 문화를 체험합니다.",
                            "duration": "3시간",
                            "cost": "10,000원",
                            "tips": "미리 입장권을 예약하시면 좋습니다."
                        }
                    ],
                    "meals": {
                        "breakfast": f"{request.get_destination()} 현지 조식",
                        "lunch": f"{request.get_destination()} 전통 음식",
                        "dinner": f"{request.get_destination()} 맛집"
                    },
                    "transportation": ["지하철", "도보"],
                    "estimated_cost": "50,000원"
                } for i in range(request.duration)
            ],
            "total_estimated_cost": f"{50000 * request.duration:,}원",
            "highlights": [f"{request.get_destination()} 대표 관광지", "현지 맛집", "문화 체험"],
            "recommendations": {
                "best_time": ["봄", "가을"],
                "what_to_pack": ["편안한 신발", "카메라", "선크림"],
                "local_tips": ["현지 교통카드 구매", "미리 맛집 예약", "날씨 확인"]
            }
        },
        plan_b={
            "plan_type": "adventure",
            "title": f"{request.get_destination()} 액티비티 여행",
            "concept": "활동적이고 모험적인 여행 코스",
            "daily_plans": [
                {
                    "day": i+1,
                    "theme": f"{i+1}일차 액티비티",
                    "activities": [
                        {
                            "time": "09:00",
                            "activity": f"{request.get_destination()} 액티비티",
                            "location": f"{request.get_destination()} 체험존",
                            "description": "특별한 액티비티를 통해 잊지 못할 추억을 만듭니다.",
                            "duration": "3시간",
                            "cost": "15,000원",
                            "tips": "편안한 복장을 준비하세요."
                        }
                    ],
                    "meals": {
                        "breakfast": f"{request.get_destination()} 카페",
                        "lunch": f"{request.get_destination()} 퓨전 레스토랑",
                        "dinner": f"{request.get_destination()} 트렌디한 맛집"
                    },
                    "transportation": ["택시", "렌터카"],
                    "estimated_cost": "70,000원"
                } for i in range(request.duration)
            ],
            "total_estimated_cost": f"{70000 * request.duration:,}원",
            "highlights": [f"{request.get_destination()} 특별 체험", "트렌디한 장소", "인스타 핫플"],
            "recommendations": {
                "best_time": ["여름", "겨울"],
                "what_to_pack": ["액션카메라", "편안한 옷", "보조배터리"],
                "local_tips": ["사전 예약 필수", "안전장비 확인", "날씨 상황 점검"]
            }
        },
        provider=provider,
        success=False,
        message="일시적인 오류가 발생했습니다. 기본 일정을 제공합니다."
    )


@router.get("/itinerary/{itinerary_id}", response_model=ItineraryResponse)
async def get_itinerary(itinerary_id: str):
    """특정 여행 일정을 조회합니다."""
    try:
        # TODO: 실제 데이터베이스에서 조회
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")


@router.get("/itinerary/{itinerary_id}/preview")
async def get_itinerary_preview(itinerary_id: str):
    """여행 일정 미리보기를 제공합니다."""
    try:
        # TODO: 실제 데이터베이스에서 조회
        return {"preview": "일정 미리보기"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")


@router.post("/itinerary/{itinerary_id}/feedback")
async def submit_feedback(
    itinerary_id: str,
    feedback: Dict[str, Any]
):
    """여행 일정에 대한 피드백을 제출합니다."""
    try:
        # TODO: 피드백 저장 로직
        return {"message": "피드백이 저장되었습니다.", "feedback_id": str(uuid.uuid4())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}") 