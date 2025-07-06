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
    """에러 발생 시 ItineraryResponse 스키마에 맞는 기본 응답을 생성합니다."""
    # 요청 정보 객체 생성 (최소 필수값만 채움)
    request_info = ItineraryRequest(
        destination=request.get_destination(),
        duration=request.duration,
        travel_style=request.travel_style,
        budget_range=request.budget_range,
        travelers_count=request.travelers_count,
        accommodation_preference=request.accommodation_preference,
        dietary_restrictions=None,
        special_interests=request.special_interests,
        special_requests=request.special_requests,
        mobility_considerations=None
    )
    
    # 최소한의 DayPlan/ActivityItem 생성
    def make_day_plan(day, theme, activity, location, description):
        return {
            "day": day,
            "theme": theme,
            "activities": [
                {
                    "time": "09:00",
                    "activity": activity,
                    "location": location,
                    "description": description,
                    "duration": "3시간",
                    "cost": "10,000원",
                    "tips": "미리 입장권을 예약하세요."
                }
            ],
            "meals": {
                "breakfast": f"{request.get_destination()} 현지 조식",
                "lunch": f"{request.get_destination()} 전통 음식",
                "dinner": f"{request.get_destination()} 맛집"
            },
            "transportation": ["지하철", "도보"],
            "estimated_cost": "50,000원"
        }
    
    plan_a = {
        "plan_type": "classic",
        "title": f"{request.get_destination()} 클래식 여행",
        "concept": "전통적이고 안정적인 여행 코스",
        "daily_plans": [
            make_day_plan(i+1, f"{i+1}일차 여행", f"{request.get_destination()} 대표 관광지 방문", f"{request.get_destination()} 중심가", "대표 관광지를 둘러보며 현지 문화를 체험합니다.")
            for i in range(request.duration)
        ],
        "total_estimated_cost": f"{50000 * request.duration:,}원",
        "highlights": [f"{request.get_destination()} 대표 관광지", "현지 맛집", "문화 체험"],
        "recommendations": {
            "best_time": ["봄", "가을"],
            "what_to_pack": ["편안한 신발", "카메라", "선크림"],
            "local_tips": ["현지 교통카드 구매", "미리 맛집 예약", "날씨 확인"]
        }
    }
    plan_b = {
        "plan_type": "adventure",
        "title": f"{request.get_destination()} 액티비티 여행",
        "concept": "활동적이고 모험적인 여행 코스",
        "daily_plans": [
            make_day_plan(i+1, f"{i+1}일차 액티비티", f"{request.get_destination()} 액티비티", f"{request.get_destination()} 체험존", "특별한 액티비티를 통해 잊지 못할 추억을 만듭니다.")
            for i in range(request.duration)
        ],
        "total_estimated_cost": f"{70000 * request.duration:,}원",
        "highlights": [f"{request.get_destination()} 특별 체험", "트렌디한 장소", "인스타 핫플"],
        "recommendations": {
            "best_time": ["여름", "겨울"],
            "what_to_pack": ["액션카메라", "편안한 옷", "보조배터리"],
            "local_tips": ["사전 예약 필수", "안전장비 확인", "날씨 상황 점검"]
        }
    }
    
    return ItineraryResponse(
        id=str(uuid.uuid4()),
        request_info=request_info,
        plan_a=plan_a,
        plan_b=plan_b,
        created_at=datetime.now().isoformat(),
        status="fallback",
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


@router.post("/customize", response_model=ItineraryResponse)
async def customize_itinerary(
    customization_request: Dict[str, Any]
):
    """
    고객 커스터마이징 요청에 따라 일정을 재생성합니다.
    4단계에서 적용되는 커스텀 재생성 기능
    """
    print(f"🎨 커스터마이징 요청 받음: {customization_request}")
    
    try:
        # 커스터마이징 요청 파라미터 추출
        original_destination = customization_request.get("destination")
        original_duration = customization_request.get("duration")
        custom_preferences = customization_request.get("customization", {})
        
        # 커스터마이징 옵션 분석
        custom_style = custom_preferences.get("style", "standard")
        custom_budget = custom_preferences.get("budget", "medium")
        custom_interests = custom_preferences.get("interests", [])
        custom_pace = custom_preferences.get("pace", "normal")  # relaxed, normal, packed
        
        print(f"🔄 커스터마이징 옵션: 스타일={custom_style}, 예산={custom_budget}, 페이스={custom_pace}")
        
        # 커스터마이징된 요청 생성
        customized_request = GenerateRequest(
            city=original_destination,
            duration=original_duration,
            budget_range=custom_budget,
            travelers_count=customization_request.get("travelers_count", 2),
            travel_style=[custom_style] if custom_style else ["cultural"],
            special_requests=f"커스터마이징 요청: {custom_pace} 페이스, 관심사: {', '.join(custom_interests)}"
        )
        
        # AdvancedItineraryService로 재생성
        generate_response = await itinerary_service.generate_itinerary(customized_request)
        
        print(f"✅ 커스터마이징된 일정 생성 완료!")
        
        # 커스터마이징된 응답 반환
        return ItineraryResponse(
            id=generate_response.id,
            destination=original_destination,
            duration=original_duration,
            created_at=generate_response.created_at,
            plan_a=generate_response.plan_a,
            plan_b=generate_response.plan_b,
            provider="gemini",
            success=True,
            message=f"커스터마이징된 일정이 성공적으로 생성되었습니다. (스타일: {custom_style}, 페이스: {custom_pace})"
        )
        
    except Exception as e:
        print(f"❌ 커스터마이징 실패: {str(e)}")
        traceback.print_exc()
        
        # 기본 응답 반환
        fallback_request = ItineraryRequest(
            destination=original_destination,
            duration=original_duration,
            travel_style=["cultural"],
            budget_range="medium",
            travelers_count=2,
            accommodation_preference="mid_range",
            special_interests=custom_interests
        )
        
        return create_fallback_response(fallback_request, "gemini")


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