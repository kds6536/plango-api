"""
고급 여행 일정 생성 서비스
사용자가 요청한 4단계 프로세스를 구현합니다:
1. AI 브레인스토밍 - 장소 이름 후보군 생성
2. 구글 플레이스 API 정보 강화 - 실제 데이터 부여
3. AI 큐레이션 - 1안/2안 분할 및 상세 일정 구성
4. 최종 JSON 조립 및 반환
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

# AI 라이브러리
from openai import AsyncOpenAI
import google.generativeai as genai

from app.schemas.itinerary import (
    GenerateRequest, GenerateResponse, OptimizeRequest, OptimizeResponse,
    TravelPlan, DayPlan, ActivityDetail, PlaceData
)
from app.services.google_places_service import GooglePlacesService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AdvancedItineraryService:
    """고급 여행 일정 생성 서비스"""
    
    def __init__(self):
        # AI 클라이언트 초기화
        self.openai_client = None
        self.gemini_model = None
        self.google_places = GooglePlacesService()
        
        # OpenAI 초기화
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            self.openai_client = AsyncOpenAI(api_key=openai_key)
            logger.info("OpenAI 클라이언트 초기화 완료")
        
        # Gemini 초기화
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
            self.gemini_model = genai.GenerativeModel('gemini-pro')
            logger.info("Gemini 모델 초기화 완료")

    async def generate_itinerary(self, request: GenerateRequest) -> GenerateResponse:
        """
        4단계 프로세스로 여행 일정을 생성합니다
        """
        request_id = str(uuid.uuid4())
        logger.info(f"여행 일정 생성 시작 [{request_id}]: {request.city}, {request.duration}일")
        
        try:
            # 1단계: AI 브레인스토밍 - 장소 이름 후보군 생성
            place_candidates = await self._step1_ai_brainstorming(request)
            logger.info(f"1단계 완료: {len(place_candidates)}개 카테고리의 장소 후보 생성")
            
            # 2단계: 구글 플레이스 API 정보 강화
            place_pool = await self._step2_google_places_enrichment(place_candidates, request.city)
            logger.info(f"2단계 완료: {len(place_pool)}개 장소 데이터 풀 생성")
            
            # 3단계: AI 큐레이션 - 1안/2안 분할 및 상세 일정 구성
            ai_plans = await self._step3_ai_curation(request, place_pool)
            logger.info(f"3단계 완료: 1안/2안 큐레이션 완료")
            
            # 4단계: 최종 JSON 조립
            final_response = self._step4_json_assembly(ai_plans, place_pool, request_id)
            logger.info(f"4단계 완료: 최종 응답 생성 [{request_id}]")
            
            return final_response
            
        except Exception as e:
            logger.error(f"여행 일정 생성 실패 [{request_id}]: {str(e)}")
            # 실패 시 기본 응답 반환
            return self._create_fallback_response(request, request_id)

    async def _step1_ai_brainstorming(self, request: GenerateRequest) -> Dict[str, List[str]]:
        """
        1단계: AI 브레인스토밍 - 장소 이름 후보군 생성
        """
        prompt1 = f"""당신은 창의적인 여행 아이디어 브레인스토밍 어시스턴트, "플랜고 아이디어봇"입니다.
사용자의 여행 요청을 기반으로, 다양한 카테고리의 추천 장소 '이름' 목록을 JSON 형식으로 생성하는 것이 당신의 임무입니다.

**사용자 요청:**
- 도시: {request.city}
- 기간: {request.duration}일
- 취향 및 요청사항: {request.special_requests or '일반적인 여행'}

**당신의 임무 및 규칙:**
1. 다양한 카테고리에 걸쳐 장소 이름 목록을 생성하세요.
2. 다음 각 카테고리에 대해 최소 5개의 추천 장소를 제공해야 합니다: '관광', '맛집', '카페', '유적지', '문화', '놀거리', '쇼핑'.
3. 추천 장소는 사용자의 취향 및 요청사항과 강력하게 일치해야 합니다.
4. 당신은 반드시 하나의 JSON 객체만으로 응답해야 합니다. JSON 외부에는 어떠한 설명도 추가하지 마세요. JSON 구조는 다음과 같아야 합니다:
   {{"관광": ["이름1", "이름2", ...], "맛집": ["이름3", "이름4", ...], ...}}"""

        try:
            if self.gemini_model:
                response = await self.gemini_model.generate_content_async(prompt1)
                content = response.text
            elif self.openai_client:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt1}],
                    temperature=0.7
                )
                content = response.choices[0].message.content
            else:
                raise Exception("AI 클라이언트가 초기화되지 않았습니다")
            
            # JSON 파싱
            place_candidates = json.loads(content)
            return place_candidates
            
        except Exception as e:
            logger.error(f"1단계 AI 브레인스토밍 실패: {str(e)}")
            # 기본 후보 반환
            return {
                "관광": [f"{request.city} 대표 관광지", f"{request.city} 명소"],
                "맛집": [f"{request.city} 맛집", f"{request.city} 현지 음식"],
                "카페": [f"{request.city} 카페", f"{request.city} 디저트"],
                "유적지": [f"{request.city} 박물관", f"{request.city} 역사"],
                "문화": [f"{request.city} 문화센터", f"{request.city} 갤러리"],
                "놀거리": [f"{request.city} 놀이시설", f"{request.city} 액티비티"],
                "쇼핑": [f"{request.city} 쇼핑몰", f"{request.city} 시장"]
            }

    async def _step2_google_places_enrichment(
        self, 
        place_candidates: Dict[str, List[str]], 
        city: str
    ) -> List[Dict[str, Any]]:
        """
        2단계: 구글 플레이스 API 정보 강화
        """
        place_pool = []
        
        for category, place_names in place_candidates.items():
            # 카테고리별로 장소 데이터 강화
            enriched_places = await self.google_places.enrich_places_data(place_names, city)
            
            # 카테고리 정보 추가
            for place in enriched_places:
                place['category'] = category
                place_pool.append(place)
        
        # 중복 제거 (place_id 기준)
        seen_ids = set()
        unique_places = []
        for place in place_pool:
            if place.get('place_id') not in seen_ids:
                seen_ids.add(place.get('place_id'))
                unique_places.append(place)
        
        return unique_places

    async def _step3_ai_curation(
        self, 
        request: GenerateRequest, 
        place_pool: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        3단계: AI 큐레이션 - 1안/2안 분할 및 상세 일정 구성
        """
        travel_dates = f"Day 1 to Day {request.duration}"
        
        prompt2 = f"""당신은 세계 최고 수준의 꼼꼼한 여행 플래너, "플랜고-GPT"입니다.
제공된 '선택 가능한 장소 목록'을 사용하여, 서로 다른 테마를 가진 완벽하게 최적화되고 매우 상세한 두 가지 여행 일정(1안, 2안)을 만드는 것이 당신의 임무입니다.

**1. 사용자의 최초 요청:**
- 도시: {request.city}
- 여행 날짜: {travel_dates} (총 {request.duration}일)
- 취향 및 요청사항: {request.special_requests or '일반적인 여행'}

**2. 선택 가능한 장소 목록 (사전 분석 단계에서 제공됨):**
여기에 상세 정보가 포함된 장소 목록이 JSON 형식으로 제공됩니다. 당신은 반드시 이 목록 안에서만 장소를 선택해야 합니다.
```json
{json.dumps(place_pool, ensure_ascii=False, indent=2)}
```

**3. 당신의 임무 및 엄격한 규칙:**
가. 두 가지 테마의 계획 수립:
사용자의 취향을 반영하는 매력적이고 뚜렷하게 다른 테마를 가진 "1안"과 "2안"을 만드세요. (예: "1안: 예술과 역사를 거니는 힐링 코스", "2안: 트렌디한 핫플레이스 탐험").
제공된 목록에서 각 계획에 어울리는 균형 잡힌 장소들을 선택하세요. 모든 장소를 사용할 필요는 없습니다.

나. 극도로 상세한 일일 스케줄:
각 날짜별로 오전, 오후, 저녁 스케줄을 구성하세요.
각 활동에 대해 다음 정보를 제공해야 합니다:
- time: 추천 시간대 (예: "10:00 - 12:00").
- place_name: 장소의 이름.
- activity_description: 그곳에서 무엇을 할지에 대한 매력적인 한두 문장의 설명.
- transportation_details: 다음 장소로 이동하기 위한 상세하고 실용적인 대중교통 안내를 제공하세요.

다. 동선 최적화:
일일 스케줄은 이동 시간을 최소화하고 왔던 길을 되돌아가지 않도록 지리적으로 최적화되어야 합니다.

라. 최종 출력 형식:
당신은 반드시 하나의 깔끔한 JSON 객체로만 응답해야 합니다. JSON 외부에는 어떠한 설명도 추가하지 마세요. 구조는 다음과 같아야 합니다:

{{
  "plan_a": {{
    "title": "1안 제목",
    "concept": "1안 컨셉 설명",
    "daily_plans": [
      {{
        "day": 1,
        "theme": "첫째 날 테마",
        "activities": [
          {{
            "time": "09:00 - 11:00",
            "place_name": "장소명",
            "activity_description": "활동 설명",
            "transportation_details": "교통 정보",
            "place_id": "선택한 장소의 place_id",
            "lat": 위도,
            "lng": 경도
          }}
        ]
      }}
    ]
  }},
  "plan_b": {{
    "title": "2안 제목",
    "concept": "2안 컨셉 설명",
    "daily_plans": [
      {{
        "day": 1,
        "theme": "첫째 날 테마 (1안과 다른 스타일)",
        "activities": [
          {{
            "time": "09:00 - 11:00",
            "place_name": "장소명",
            "activity_description": "활동 설명",
            "transportation_details": "교통 정보",
            "place_id": "선택한 장소의 place_id",
            "lat": 위도,
            "lng": 경도
          }}
        ]
      }}
    ]
  }}
}}"""

        try:
            if self.gemini_model:
                response = await self.gemini_model.generate_content_async(prompt2)
                content = response.text
            elif self.openai_client:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4",  # 더 정확한 결과를 위해 GPT-4 사용
                    messages=[{"role": "user", "content": prompt2}],
                    temperature=0.7,
                    max_tokens=4000
                )
                content = response.choices[0].message.content
            else:
                raise Exception("AI 클라이언트가 초기화되지 않았습니다")
            
            # JSON 파싱
            ai_plans = json.loads(content)
            return ai_plans
            
        except Exception as e:
            logger.error(f"3단계 AI 큐레이션 실패: {str(e)}")
            # 기본 계획 반환
            return self._create_basic_plans(request, place_pool)

    def _step4_json_assembly(
        self, 
        ai_plans: Dict[str, Any], 
        place_pool: List[Dict[str, Any]], 
        request_id: str
    ) -> GenerateResponse:
        """
        4단계: 최종 JSON 조립 및 반환
        """
        def create_travel_plan(plan_data: Dict[str, Any]) -> TravelPlan:
            daily_plans = []
            used_places = []
            
            for day_data in plan_data.get("daily_plans", []):
                activities = []
                for activity_data in day_data.get("activities", []):
                    activity = ActivityDetail(
                        time=activity_data.get("time", "09:00"),
                        place_name=activity_data.get("place_name", ""),
                        activity_description=activity_data.get("activity_description", ""),
                        transportation_details=activity_data.get("transportation_details", ""),
                        place_id=activity_data.get("place_id"),
                        lat=activity_data.get("lat"),
                        lng=activity_data.get("lng")
                    )
                    activities.append(activity)
                    
                    # 사용된 장소 추가
                    if activity_data.get("place_id"):
                        for place in place_pool:
                            if place.get("place_id") == activity_data.get("place_id"):
                                place_data = PlaceData(
                                    place_id=place.get("place_id", ""),
                                    name=place.get("name", ""),
                                    category=place.get("category", ""),
                                    lat=place.get("lat", 0.0),
                                    lng=place.get("lng", 0.0),
                                    rating=place.get("rating"),
                                    address=place.get("address"),
                                    description=place.get("description")
                                )
                                used_places.append(place_data)
                                break
                
                day_plan = DayPlan(
                    day=day_data.get("day", 1),
                    theme=day_data.get("theme", ""),
                    activities=activities
                )
                daily_plans.append(day_plan)
            
            return TravelPlan(
                title=plan_data.get("title", ""),
                concept=plan_data.get("concept", ""),
                daily_plans=daily_plans,
                places=used_places
            )
        
        plan_a = create_travel_plan(ai_plans.get("plan_a", {}))
        plan_b = create_travel_plan(ai_plans.get("plan_b", {}))
        
        return GenerateResponse(
            plan_a=plan_a,
            plan_b=plan_b,
            request_id=request_id,
            generated_at=datetime.now()
        )

    async def optimize_itinerary(self, request: OptimizeRequest) -> OptimizeResponse:
        """
        선택된 장소들을 구글 다이렉션 API로 최적화합니다
        """
        logger.info(f"경로 최적화 시작: {len(request.selected_places)}개 장소")
        
        try:
            # 장소 데이터를 구글 API 형식으로 변환
            places_for_optimization = []
            for place in request.selected_places:
                places_for_optimization.append({
                    "place_id": place.place_id,
                    "name": place.name,
                    "lat": place.lat,
                    "lng": place.lng,
                    "category": place.category
                })
            
            # 구글 다이렉션 API로 경로 최적화
            optimization_result = await self.google_places.optimize_route(
                places_for_optimization, 
                request.start_location
            )
            
            if not optimization_result:
                raise Exception("경로 최적화 실패")
            
            # 최적화된 순서로 일정 재구성
            optimized_places = optimization_result.get("optimized_places", [])
            optimized_plan = self._create_optimized_plan(optimized_places, request.duration)
            
            return OptimizeResponse(
                optimized_plan=optimized_plan,
                total_distance=optimization_result.get("total_distance"),
                total_duration=optimization_result.get("total_duration"),
                optimization_details=optimization_result
            )
            
        except Exception as e:
            logger.error(f"경로 최적화 실패: {str(e)}")
            # 실패 시 원래 순서 유지
            fallback_plan = self._create_optimized_plan(
                [place.dict() for place in request.selected_places], 
                request.duration
            )
            return OptimizeResponse(
                optimized_plan=fallback_plan,
                total_distance="계산 불가",
                total_duration="계산 불가",
                optimization_details={}
            )

    def _create_optimized_plan(self, places: List[Dict[str, Any]], duration: int) -> TravelPlan:
        """최적화된 장소들로 일정을 재구성합니다"""
        daily_plans = []
        places_per_day = max(1, len(places) // duration)
        
        for day in range(1, duration + 1):
            start_idx = (day - 1) * places_per_day
            end_idx = start_idx + places_per_day
            if day == duration:  # 마지막 날은 남은 모든 장소
                end_idx = len(places)
            
            day_places = places[start_idx:end_idx]
            activities = []
            
            for i, place in enumerate(day_places):
                time_slot = f"{9 + i * 2:02d}:00 - {11 + i * 2:02d}:00"
                activity = ActivityDetail(
                    time=time_slot,
                    place_name=place.get("name", ""),
                    activity_description=f"{place.get('name')}에서 여행을 즐겨보세요",
                    transportation_details="최적화된 경로로 이동",
                    place_id=place.get("place_id"),
                    lat=place.get("lat"),
                    lng=place.get("lng")
                )
                activities.append(activity)
            
            day_plan = DayPlan(
                day=day,
                theme=f"{day}일차 최적화된 일정",
                activities=activities
            )
            daily_plans.append(day_plan)
        
        # PlaceData 객체 생성
        place_data_list = []
        for place in places:
            place_data = PlaceData(
                place_id=place.get("place_id", ""),
                name=place.get("name", ""),
                category=place.get("category", ""),
                lat=place.get("lat", 0.0),
                lng=place.get("lng", 0.0),
                rating=place.get("rating"),
                address=place.get("address"),
                description=place.get("description")
            )
            place_data_list.append(place_data)
        
        return TravelPlan(
            title="나만의 맞춤 일정",
            concept="선택하신 장소들을 최적의 동선으로 재조합한 맞춤형 여행 계획",
            daily_plans=daily_plans,
            places=place_data_list
        )

    def _create_fallback_response(self, request: GenerateRequest, request_id: str) -> GenerateResponse:
        """AI 실패 시 기본 응답을 생성합니다"""
        basic_activity = ActivityDetail(
            time="09:00 - 12:00",
            place_name=f"{request.city} 대표 관광지",
            activity_description="현지 주요 명소를 방문합니다",
            transportation_details="대중교통 이용"
        )
        
        basic_day = DayPlan(
            day=1,
            theme="기본 여행 일정",
            activities=[basic_activity]
        )
        
        basic_plan = TravelPlan(
            title=f"{request.city} 기본 여행",
            concept="기본적인 여행 계획",
            daily_plans=[basic_day],
            places=[]
        )
        
        return GenerateResponse(
            plan_a=basic_plan,
            plan_b=basic_plan,
            request_id=request_id,
            generated_at=datetime.now()
        )

    def _create_basic_plans(self, request: GenerateRequest, place_pool: List[Dict[str, Any]]) -> Dict[str, Any]:
        """기본 계획을 생성합니다"""
        return {
            "plan_a": {
                "title": f"{request.city} 클래식 여행",
                "concept": "전통적인 관광 중심의 여행",
                "daily_plans": [
                    {
                        "day": 1,
                        "theme": "주요 관광지 탐방",
                        "activities": [
                            {
                                "time": "09:00 - 12:00",
                                "place_name": "관광지",
                                "activity_description": "주요 관광지 방문",
                                "transportation_details": "대중교통 이용"
                            }
                        ]
                    }
                ]
            },
            "plan_b": {
                "title": f"{request.city} 모던 여행",
                "concept": "현대적인 액티비티 중심의 여행",
                "daily_plans": [
                    {
                        "day": 1,
                        "theme": "트렌디한 장소 탐방",
                        "activities": [
                            {
                                "time": "09:00 - 12:00",
                                "place_name": "카페/맛집",
                                "activity_description": "현지 트렌드 체험",
                                "transportation_details": "대중교통 이용"
                            }
                        ]
                    }
                ]
            }
        } 