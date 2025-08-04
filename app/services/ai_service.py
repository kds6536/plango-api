"""AI 서비스"""

import openai
from typing import Dict, Any, List
import json
import asyncio
from app.config import settings
from app.schemas.itinerary import ItineraryRequest, ItineraryPlan, DayPlan, ActivityItem
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AIService:
    """AI 기반 여행 일정 생성 서비스"""
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def generate_travel_plans(self, request: ItineraryRequest) -> Dict[str, ItineraryPlan]:
        """여행 계획 A와 B를 생성합니다"""
        try:
            logger.info(f"AI 여행 일정 생성 시작: {request.destination}")
            
            # Plan A와 Plan B를 병렬로 생성
            plan_a_task = self._generate_single_plan(request, "A", "문화와 미식 중심")
            plan_b_task = self._generate_single_plan(request, "B", "체험과 모험 중심")
            
            plan_a, plan_b = await asyncio.gather(plan_a_task, plan_b_task)
            
            logger.info(f"AI 여행 일정 생성 완료: {request.destination}")
            return {"plan_a": plan_a, "plan_b": plan_b}
            
        except Exception as e:
            logger.error(f"AI 여행 일정 생성 실패: {str(e)}")
            # 실패 시 기본 계획 반환
            return await self._generate_fallback_plans(request)
    
    async def _generate_single_plan(
        self, 
        request: ItineraryRequest, 
        plan_type: str, 
        concept: str
    ) -> ItineraryPlan:
        """단일 여행 계획을 생성합니다"""
        
        prompt = self._build_prompt(request, plan_type, concept)
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": "당신은 전문 여행 플래너입니다. 사용자의 요청에 따라 상세하고 실용적인 여행 일정을 JSON 형태로 제공해주세요."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            return self._parse_ai_response(content, plan_type, concept)
            
        except Exception as e:
            logger.error(f"OpenAI API 호출 실패: {str(e)}")
            return await self._generate_fallback_single_plan(request, plan_type, concept)
    
    def _build_prompt(self, request: ItineraryRequest, plan_type: str, concept: str) -> str:
        """AI 프롬프트를 구성합니다"""
        
        travel_styles = ", ".join(request.travel_style)
        special_interests = ", ".join(request.special_interests or [])
        dietary_restrictions = ", ".join(request.dietary_restrictions or [])
        
        prompt = f"""
{request.destination}로 {request.duration}일 여행 일정을 짜주세요.

**여행 정보:**
- 목적지: {request.destination}
- 기간: {request.duration}일
- 여행자 수: {request.travelers_count}명
- 여행 스타일: {travel_styles}
- 예산 범위: {request.budget_range.value}
- 계획 컨셉: {concept}

**추가 요구사항:**
- 숙박 선호: {request.accommodation_preference or '없음'}
- 식단 제한: {dietary_restrictions or '없음'}
- 특별 관심사: {special_interests or '없음'}
- 이동성 고려: {request.mobility_considerations or '없음'}

**요청사항:**
1. 각 날짜별로 상세한 일정을 작성해주세요
2. 시간대별 활동, 장소, 설명을 포함해주세요
3. 식사 추천과 교통수단을 명시해주세요
4. 예상 비용을 포함해주세요
5. 실용적이고 실현 가능한 일정으로 구성해주세요

다음 JSON 형식으로 응답해주세요:
{{
    "title": "계획 제목",
    "daily_plans": [
        {{
            "day": 1,
            "theme": "첫날 테마",
            "activities": [
                {{
                    "time": "09:00",
                    "activity": "활동명",
                    "location": "장소",
                    "description": "상세 설명",
                    "duration": "2시간",
                    "cost": "15,000원",
                    "tips": "유용한 팁"
                }}
            ],
            "meals": {{
                "breakfast": "아침 식사 추천",
                "lunch": "점심 식사 추천", 
                "dinner": "저녁 식사 추천"
            }},
            "transportation": ["지하철", "도보"],
            "estimated_cost": "80,000원"
        }}
    ],
    "total_estimated_cost": "240,000원",
    "highlights": ["주요 하이라이트1", "주요 하이라이트2"],
    "recommendations": {{
        "shopping": ["쇼핑 추천1", "쇼핑 추천2"],
        "local_tips": ["현지 팁1", "현지 팁2"]
    }}
}}
        """
        
        return prompt
    
    def _parse_ai_response(self, content: str, plan_type: str, concept: str) -> ItineraryPlan:
        """AI 응답을 파싱합니다"""
        try:
            # JSON 응답 파싱
            data = json.loads(content)
            
            # DayPlan 객체 생성
            daily_plans = []
            for day_data in data.get("daily_plans", []):
                activities = [
                    ActivityItem(**activity) 
                    for activity in day_data.get("activities", [])
                ]
                
                day_plan = DayPlan(
                    day=day_data.get("day"),
                    theme=day_data.get("theme"),
                    activities=activities,
                    meals=day_data.get("meals", {}),
                    transportation=day_data.get("transportation", []),
                    estimated_cost=day_data.get("estimated_cost", "0원")
                )
                daily_plans.append(day_plan)
            
            return ItineraryPlan(
                plan_type=plan_type,
                title=data.get("title", f"Plan {plan_type}"),
                concept=concept,
                daily_plans=daily_plans,
                total_estimated_cost=data.get("total_estimated_cost", "0원"),
                highlights=data.get("highlights", []),
                recommendations=data.get("recommendations", {})
            )
            
        except Exception as e:
            logger.error(f"AI 응답 파싱 실패: {str(e)}")
            return self._create_fallback_plan(plan_type, concept)
    
    async def _generate_fallback_plans(self, request: ItineraryRequest) -> Dict[str, ItineraryPlan]:
        """기본 계획을 생성합니다 (AI 실패 시)"""
        plan_a = await self._generate_fallback_single_plan(request, "A", "문화와 미식 중심")
        plan_b = await self._generate_fallback_single_plan(request, "B", "체험과 모험 중심")
        return {"plan_a": plan_a, "plan_b": plan_b}
    
    async def _generate_fallback_single_plan(
        self, 
        request: ItineraryRequest, 
        plan_type: str, 
        concept: str
    ) -> ItineraryPlan:
        """기본 단일 계획을 생성합니다"""
        return self._create_fallback_plan(plan_type, concept)
    
    def _create_fallback_plan(self, plan_type: str, concept: str) -> ItineraryPlan:
        """기본 계획을 생성합니다"""
        activity = ActivityItem(
            time="09:00",
            activity="관광지 방문",
            location="주요 명소",
            description="현지 주요 명소를 방문합니다",
            duration="2-3시간",
            cost="20,000원",
            tips="사전 예약을 추천합니다"
        )
        
        day_plan = DayPlan(
            day=1,
            theme="기본 관광",
            activities=[activity],
            meals={
                "breakfast": "호텔 조식",
                "lunch": "현지 맛집",
                "dinner": "전통 요리"
            },
            transportation=["대중교통"],
            estimated_cost="80,000원"
        )
        
        return ItineraryPlan(
            plan_type=plan_type,
            title=f"기본 여행 계획 {plan_type}",
            concept=concept,
            daily_plans=[day_plan],
            total_estimated_cost="80,000원",
            highlights=["주요 명소 방문", "현지 문화 체험"],
            recommendations={
                "shopping": ["현지 기념품"],
                "local_tips": ["현지 교통카드 구매"]
            }
        ) 