"""여행 일정 생성 라우터 - OpenAI & Gemini AI 스위치 지원"""

import os
import json
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List
from datetime import datetime
import uuid

# === 두 AI 라이브러리를 모두 import ===
from openai import OpenAI
import google.generativeai as genai

# Supabase 클라이언트 import (기존 유지)
from supabase import create_client, Client

from app.schemas.itinerary import (
    ItineraryRequest,
    ItineraryResponse,
    ItineraryPlan,
    DayPlan,
    ActivityItem
)

router = APIRouter(prefix="/api/v1/itinerary", tags=["여행 일정 API"])

# === API 클라이언트 초기화 (지연 초기화) ===
# OpenAI와 Gemini 클라이언트는 함수 호출 시점에 초기화됩니다.

# Supabase 클라이언트도 지연 초기화로 변경
# supabase 클라이언트는 함수 호출 시점에 초기화됩니다.


async def get_destination_spots(destination: str) -> List[Dict]:
    """Supabase에서 해당 목적지의 여행지 목록을 가져옵니다."""
    try:
        print(f"🔍 Supabase에서 '{destination}' 여행지 정보 검색 중...")
        
        # Supabase 클라이언트 초기화
        supabase: Client = create_client(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_API_KEY", "")
        )
        
        # Supabase에서 destinations 테이블 조회 (목적지 이름으로 검색)
        response = supabase.table('itineraries').select('*').ilike('city', f'%{destination}%').execute()
        
        if response.data:
            print(f"✅ {len(response.data)}개의 여행지 정보를 찾았습니다!")
            return response.data
        else:
            print(f"⚠️ '{destination}'에 대한 여행지 정보를 찾을 수 없습니다")
            return []
            
    except Exception as e:
        print(f"❌ Supabase 조회 실패: {str(e)}")
        print(f"🔄 기본 데이터로 진행합니다")
        return []


def create_openai_prompt(request: ItineraryRequest, available_spots: List[Dict] = None) -> str:
    """OpenAI용 한국어 프롬프트를 생성합니다."""
    
    travel_styles_text = ", ".join(request.travel_style) if request.travel_style else "문화 탐방, 맛집 투어"
    
    # Supabase에서 가져온 여행지 정보 추가
    spots_info = ""
    if available_spots:
        spots_info = f"""

## 추천 여행지 목록 (반드시 이 목록에서 선택하세요):
{json.dumps(available_spots, ensure_ascii=False, indent=2)}

위 목록에서 선택하여 일정을 구성해주세요. 각 여행지의 name, description, category, rating 정보를 활용하세요.
"""
    else:
        spots_info = f"""

## 여행지 정보:
데이터베이스에서 '{request.get_destination()}' 관련 정보를 찾을 수 없어서, 당신의 전문 지식을 바탕으로 {request.get_destination()}의 대표적인 관광지들을 추천해주세요.
"""
    
    prompt = f"""
당신은 세계적으로 유명한 여행 전문가 'Plango AI'입니다. 
사용자의 요청에 따라 두 가지 다른 스타일의 완벽한 여행 일정을 생성해주세요.

## 사용자 요청 정보:
- 목적지: {request.get_destination()}
- 여행 기간: {request.duration}일
- 여행 스타일: {travel_styles_text}
- 예산 범위: {request.budget_range}
- 인원수: {request.travelers_count}명
- 숙박 선호도: {request.accommodation_preference}
- 특별 관심사: {", ".join(request.special_interests) if request.special_interests else "없음"}

{spots_info}

## 응답 요구사항:
반드시 아래 JSON 형식으로만 응답해주세요. 다른 텍스트는 포함하지 마세요.

{{
  "plan_a": {{
    "plan_type": "classic",
    "title": "매력적인 제목 (예: 도쿄 클래식 문화 여행)",
    "concept": "이 여행의 핵심 컨셉 설명 (1-2문장)",
    "daily_plans": [
      {{
        "day": 1,
        "theme": "첫째 날 테마",
        "activities": [
          {{
            "time": "09:00",
            "activity": "활동명",
            "location": "구체적인 장소명",
            "description": "활동에 대한 자세한 설명",
            "duration": "2시간",
            "cost": "예상 비용",
            "tips": "유용한 팁"
          }}
        ],
        "meals": {{
          "breakfast": "아침 식사 추천",
          "lunch": "점심 식사 추천", 
          "dinner": "저녁 식사 추천"
        }},
        "transportation": ["지하철", "도보"],
        "estimated_cost": "일일 예상 비용"
      }}
    ],
    "total_estimated_cost": "총 예상 비용",
    "highlights": ["하이라이트1", "하이라이트2", "하이라이트3"],
    "recommendations": {{
      "best_time": ["봄(4월-5월)", "가을(9월-10월)"],
      "what_to_pack": ["편안한 신발", "모자", "선크림", "카메라"],
      "local_tips": ["팁 1", "팁 2", "팁 3"]
    }}
  }},
  "plan_b": {{
    "plan_type": "adventure",
    "title": "모험적인 제목 (예: 도쿄 모던 액티비티 여행)",
    "concept": "Plan A와 다른 스타일의 컨셉",
    "daily_plans": [
      {{
        "day": 1,
        "theme": "첫째 날 테마 (Plan A와 다른 스타일)",
        "activities": [
          {{
            "time": "09:00",
            "activity": "활동명",
            "location": "구체적인 장소명", 
            "description": "활동에 대한 자세한 설명",
            "duration": "2시간",
            "cost": "예상 비용",
            "tips": "유용한 팁"
          }}
        ],
        "meals": {{
          "breakfast": "아침 식사 추천",
          "lunch": "점심 식사 추천",
          "dinner": "저녁 식사 추천"
        }},
        "transportation": ["지하철", "도보"],
        "estimated_cost": "일일 예상 비용"
      }}
    ],
    "total_estimated_cost": "총 예상 비용", 
    "highlights": ["하이라이트1", "하이라이트2", "하이라이트3"],
    "recommendations": {{
      "best_time": "최적 방문 시기",
      "what_to_pack": "준비물 추천", 
      "local_tips": "현지 팁"
    }}
  }}
}}

**엄격한 출력 규칙:**
- recommendations.best_time, recommendations.what_to_pack, recommendations.local_tips는 반드시 쉼표로 구분된 문자열이 아니라, 각 항목이 따로따로 들어간 JSON 배열(예: ["봄(4월-5월)", "가을(9월-10월)"])로 출력해야 합니다.
- 예시처럼 반드시 배열로 만들어주세요. (단일 문자열 금지)
Plan A는 클래식하고 전통적인 스타일로, Plan B는 모던하고 액티비티 중심으로 구성해주세요.
각 플랜마다 {request.duration}일치 일정을 모두 채워주세요.
"""
    return prompt


def create_gemini_prompt(request: ItineraryRequest, available_spots: List[Dict] = None) -> str:
    """Gemini용 한국어 프롬프트를 생성합니다."""
    
    travel_styles_text = ", ".join(request.travel_style) if request.travel_style else "문화 탐방, 맛집 투어"
    
    # Supabase에서 가져온 여행지 정보 추가
    spots_info = ""
    if available_spots:
        spots_info = f"""

## 추천 여행지 목록 (반드시 이 목록에서 선택하세요):
{json.dumps(available_spots, ensure_ascii=False, indent=2)}

위 목록에서 선택하여 일정을 구성해주세요. 각 여행지의 name, description, category, rating 정보를 활용하세요.
"""
    else:
        spots_info = f"""

## 여행지 정보:
데이터베이스에서 '{request.get_destination()}' 관련 정보를 찾을 수 없어서, 당신의 전문 지식을 바탕으로 {request.get_destination()}의 대표적인 관광지들을 추천해주세요.
"""
    
    prompt = f"""
당신은 세계적으로 유명한 여행 전문가 'Plango AI'입니다. 
사용자의 요청에 따라 두 가지 다른 스타일의 완벽한 여행 일정을 생성해주세요.

## 사용자 요청 정보:
- 목적지: {request.get_destination()}
- 여행 기간: {request.duration}일
- 여행 스타일: {travel_styles_text}
- 예산 범위: {request.budget_range}
- 인원수: {request.travelers_count}명
- 숙박 선호도: {request.accommodation_preference}
- 특별 관심사: {", ".join(request.special_interests) if request.special_interests else "없음"}

{spots_info}

## 응답 요구사항:
반드시 아래 JSON 형식으로만 응답해주세요. 다른 텍스트는 포함하지 마세요.

{{
  "plan_a": {{
    "plan_type": "classic",
    "title": "매력적인 제목 (예: 도쿄 클래식 문화 여행)",
    "concept": "이 여행의 핵심 컨셉 설명 (1-2문장)",
    "daily_plans": [
      {{
        "day": 1,
        "theme": "첫째 날 테마",
        "activities": [
          {{
            "time": "09:00",
            "activity": "활동명",
            "location": "구체적인 장소명",
            "description": "활동에 대한 자세한 설명",
            "duration": "2시간",
            "cost": "예상 비용",
            "tips": "유용한 팁"
          }}
        ],
        "meals": {{
          "breakfast": "아침 식사 추천",
          "lunch": "점심 식사 추천", 
          "dinner": "저녁 식사 추천"
        }},
        "transportation": ["지하철", "도보"],
        "estimated_cost": "일일 예상 비용"
      }}
    ],
    "total_estimated_cost": "총 예상 비용",
    "highlights": ["하이라이트1", "하이라이트2", "하이라이트3"],
    "recommendations": {{
      "best_time": "최적 방문 시기",
      "what_to_pack": "준비물 추천",
      "local_tips": "현지 팁"
    }}
  }},
  "plan_b": {{
    "plan_type": "adventure",
    "title": "모험적인 제목 (예: 도쿄 모던 액티비티 여행)",
    "concept": "Plan A와 다른 스타일의 컨셉",
    "daily_plans": [
      {{
        "day": 1,
        "theme": "첫째 날 테마 (Plan A와 다른 스타일)",
        "activities": [
          {{
            "time": "09:00",
            "activity": "활동명",
            "location": "구체적인 장소명", 
            "description": "활동에 대한 자세한 설명",
            "duration": "2시간",
            "cost": "예상 비용",
            "tips": "유용한 팁"
          }}
        ],
        "meals": {{
          "breakfast": "아침 식사 추천",
          "lunch": "점심 식사 추천",
          "dinner": "저녁 식사 추천"
        }},
        "transportation": ["지하철", "도보"],
        "estimated_cost": "일일 예상 비용"
      }}
    ],
    "total_estimated_cost": "총 예상 비용", 
    "highlights": ["하이라이트1", "하이라이트2", "하이라이트3"],
    "recommendations": {{
      "best_time": "최적 방문 시기",
      "what_to_pack": "준비물 추천", 
      "local_tips": "현지 팁"
    }}
  }}
}}

Plan A는 클래식하고 전통적인 스타일로, Plan B는 모던하고 액티비티 중심으로 구성해주세요.
각 플랜마다 {request.duration}일치 일정을 모두 채워주세요.
"""
    return prompt


async def call_openai_api(prompt: str) -> Dict[str, Any]:
    """OpenAI API를 호출합니다."""
    try:
        print(f"🚀 OpenAI API 호출 시작...")
        
        # OpenAI 클라이언트 초기화
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo-1106",  # JSON 모드를 지원하는 모델
            messages=[
                {
                    "role": "system", 
                    "content": "You are a professional travel planner. Always respond in accurate JSON format only."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},  # JSON 응답 강제
            temperature=0.8,  # 창의적인 응답을 위해 적당한 온도 설정
            max_tokens=4000   # 충분한 토큰 제한
        )
        
        ai_response_content = response.choices[0].message.content
        print(f"✅ OpenAI API 응답 받음 (길이: {len(ai_response_content)} 문자)")
        
        try:
            return json.loads(ai_response_content)
        except json.JSONDecodeError as e:
            print(f"❌ OpenAI JSON 파싱 실패: {e}")
            print(f"AI 응답 내용: {ai_response_content[:500]}...")
            raise HTTPException(status_code=500, detail="OpenAI 응답을 파싱할 수 없습니다")
            
    except Exception as e:
        print(f"❌ OpenAI API 호출 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OpenAI API 호출 중 오류가 발생했습니다: {str(e)}")


async def call_gemini_api(prompt: str) -> Dict[str, Any]:
    """Google Gemini API를 호출합니다."""
    try:
        print(f"🚀 Gemini API 호출 시작...")
        
        # Gemini 클라이언트 초기화
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        # Gemini 응답에서 불필요한 마크다운 제거
        cleaned_response_text = response.text.strip()
        if "```json" in cleaned_response_text:
            cleaned_response_text = cleaned_response_text.replace("```json", "").replace("```", "").strip()
        
        print(f"✅ Gemini API 응답 받음 (길이: {len(cleaned_response_text)} 문자)")
        
        try:
            return json.loads(cleaned_response_text)
        except json.JSONDecodeError as e:
            print(f"❌ Gemini JSON 파싱 실패: {e}")
            print(f"AI 응답 내용: {cleaned_response_text[:500]}...")
            raise HTTPException(status_code=500, detail="Gemini 응답을 파싱할 수 없습니다")
            
    except Exception as e:
        print(f"❌ Gemini API 호출 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Gemini API 호출 중 오류가 발생했습니다: {str(e)}")


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
    🎯 AI 스위치 여행 일정 생성기
    
    사용자 요청과 선택한 AI 공급자(provider)에 따라 여행 일정을 생성합니다.
    - provider=openai : OpenAI GPT 모델 사용 (영어 프롬프트)
    - provider=gemini : Google Gemini 모델 사용 (한국어 프롬프트)
    """
    try:
        print(f"🎯 {provider.upper()}를 사용하여 여행 일정 생성을 시작합니다!")
        print(f"📍 목적지: {request.get_destination()}")
        print(f"📅 기간: {request.duration}일")
        print(f"🎨 스타일: {request.travel_style}")
        print(f"💰 예산: {request.budget_range}")
        print(f"🤖 AI 공급자: {provider.upper()}")
        
        # 1. Supabase에서 여행지 정보 가져오기
        available_spots = await get_destination_spots(request.get_destination())
        
        # 2. AI 공급자에 따라 다른 프롬프트 생성 및 API 호출
        if provider == "openai":
            # OpenAI 사용
            prompt = create_openai_prompt(request, available_spots)
            ai_data = await call_openai_api(prompt)
            
        elif provider == "gemini":
            # Gemini 사용
            prompt = create_gemini_prompt(request, available_spots)
            ai_data = await call_gemini_api(prompt)
            
        else:
            raise HTTPException(status_code=400, detail="지원하지 않는 AI 공급자입니다. openai 또는 gemini를 선택하세요.")
        
        # 3. 응답 데이터 구성
        itinerary_id = str(uuid.uuid4())
        
        response_data = {
            "id": itinerary_id,
            "request_info": {
                "destination": request.get_destination(),
                "duration": request.duration,
                "travel_style": request.travel_style,
                "budget_range": request.budget_range,
                "travelers_count": request.travelers_count,
                "ai_provider": provider.upper()  # 어떤 AI를 사용했는지 기록
            },
            "plan_a": ai_data.get("plan_a", {}),
            "plan_b": ai_data.get("plan_b", {}),
            "created_at": datetime.now().isoformat(),
            "status": "completed",
            "ai_provider": provider.upper()
        }
        
        print(f"🎉 {provider.upper()}로 여행 일정 생성 완료! ID: {itinerary_id}")
        return response_data
        
    except HTTPException:
        # 이미 처리된 HTTP 예외는 그대로 전달
        raise
        
    except Exception as e:
        import traceback
        print("!!!!!!!!!!!!! 에러 발생 !!!!!!!!!!!!!")
        print(f"에러 타입: {type(e).__name__}")
        print(f"에러 메시지: {e}")
        print("상세 Traceback:")
        traceback.print_exc()
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        # API 키 오류인 경우 폴백
        if "api_key" in str(e).lower() or "401" in str(e):
            print(f"🔑 {provider.upper()} API 키가 설정되지 않았거나 잘못되었습니다")
            return create_fallback_response(request, provider)
        raise HTTPException(status_code=500, detail=f"서버 내부 오류 발생: {str(e)}")


def create_fallback_response(request: ItineraryRequest, provider: str):
    """API 호출 실패 시 사용할 폴백 응답 (개발용)"""
    print(f"🔄 {provider.upper()} 폴백 응답 생성 중...")
    
    itinerary_id = str(uuid.uuid4())
    
    fallback_data = {
        "id": itinerary_id,
        "request_info": {
            "destination": request.get_destination(),
            "duration": request.duration,
            "travel_style": request.travel_style,
            "budget_range": request.budget_range,
            "travelers_count": request.travelers_count,
            "ai_provider": f"{provider.upper()} (FALLBACK)"
        },
        "plan_a": {
            "plan_type": "classic",
            "title": f"{request.get_destination()} 클래식 여행 ({provider.upper()} 폴백 데이터)",
            "concept": f"실제 {provider.upper()} API 연결 후 더욱 맞춤형 일정을 제공받으실 수 있습니다",
            "daily_plans": [
                {
                    "day": 1,
                    "theme": "도시 탐험",
                    "activities": [
                        {
                            "time": "09:00",
                            "activity": "주요 관광지 방문",
                            "location": f"{request.get_destination()} 중심가",
                            "description": "현지의 대표적인 관광지를 둘러보며 여행을 시작합니다",
                            "duration": "3시간",
                            "cost": "15,000원",
                            "tips": f"실제 {provider.upper()} API 연결 시 더 구체적인 정보를 제공합니다"
                        }
                    ],
                    "meals": {
                        "breakfast": "호텔 조식",
                        "lunch": "현지 맛집",
                        "dinner": "전통 요리"
                    },
                    "transportation": ["지하철", "도보"],
                    "estimated_cost": "50,000원"
                }
            ],
            "total_estimated_cost": f"{request.duration * 50000:,}원",
            "highlights": ["주요 관광지", "현지 문화 체험", "맛집 투어"],
            "recommendations": {
                "best_time": "연중무휴",
                "what_to_pack": "편한 신발, 카메라",
                "local_tips": f"{provider.upper()} API 연결 후 더 자세한 팁을 제공합니다"
            }
        },
        "plan_b": {
            "plan_type": "adventure",
            "title": f"{request.get_destination()} 액티비티 여행 ({provider.upper()} 폴백 데이터)",
            "concept": f"실제 {provider.upper()} API 연결 후 더욱 다양한 액티비티를 추천받으실 수 있습니다",
            "daily_plans": [
                {
                    "day": 1,
                    "theme": "액티비티 체험",
                    "activities": [
                        {
                            "time": "10:00",
                            "activity": "액티비티 체험",
                            "location": f"{request.get_destination()} 액티비티 센터",
                            "description": "현지에서 즐길 수 있는 특별한 액티비티를 체험합니다",
                            "duration": "4시간",
                            "cost": "25,000원",
                            "tips": f"실제 {provider.upper()} API 연결 시 더 구체적인 액티비티를 추천합니다"
                        }
                    ],
                    "meals": {
                        "breakfast": "카페 브런치",
                        "lunch": "액티비티 근처 식당",
                        "dinner": "야경 맛집"
                    },
                    "transportation": ["택시", "대중교통"],
                    "estimated_cost": "70,000원"
                }
            ],
            "total_estimated_cost": f"{request.duration * 70000:,}원",
            "highlights": ["특별 액티비티", "현지 체험", "야경 투어"],
            "recommendations": {
                "best_time": "계절별 상이",
                "what_to_pack": "액티비티용 복장",
                "local_tips": f"{provider.upper()} API 연결 후 더 자세한 정보를 제공합니다"
            }
        },
        "created_at": datetime.now().isoformat(),
        "status": "fallback",
        "ai_provider": f"{provider.upper()} (FALLBACK)"
    }
    
    print(f"⚠️ {provider.upper()} 폴백 응답 생성 완료 (API 키를 설정하면 실제 AI 응답을 받을 수 있습니다)")
    return fallback_data


@router.get("/itinerary/{itinerary_id}", response_model=ItineraryResponse)
async def get_itinerary(itinerary_id: str):
    """여행 일정 조회"""
    try:
        # 실제로는 DB에서 조회하지만, 현재는 가짜 데이터를 반환
        raise HTTPException(status_code=404, detail="해당 일정을 찾을 수 없습니다. 새로운 일정을 생성해주세요.")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 여행 일정 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="여행 일정 조회 중 오류가 발생했습니다")


@router.get("/itinerary/{itinerary_id}/preview")
async def get_itinerary_preview(itinerary_id: str):
    """여행 일정 미리보기"""
    return {
        "id": itinerary_id,
        "preview": {
            "destination": "도쿄",
            "duration": "3일 2박",
            "highlights": ["아사쿠사 관광", "시부야 쇼핑", "츠키지 시장"]
        }
    }


@router.post("/itinerary/{itinerary_id}/feedback")
async def submit_feedback(
    itinerary_id: str,
    feedback: Dict[str, Any]
):
    """여행 일정 피드백 제출"""
    print(f"여행 일정 피드백 수신: {itinerary_id}")
    
    return {
        "message": "피드백이 성공적으로 제출되었습니다",
        "itinerary_id": itinerary_id,
        "feedback_id": str(uuid.uuid4())
    } 