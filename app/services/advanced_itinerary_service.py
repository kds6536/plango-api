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

from app.schemas.itinerary import (
    GenerateRequest, GenerateResponse, OptimizeRequest, OptimizeResponse,
    TravelPlan, DayPlan, ActivityDetail, PlaceData
)
from app.services.google_places_service import GooglePlacesService
from app.services.dynamic_ai_service import dynamic_ai_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AdvancedItineraryService:
    """고급 여행 일정 생성 서비스"""
    
    def __init__(self):
        # 서비스 초기화
        self.ai_service = dynamic_ai_service
        self.google_places = GooglePlacesService()
        logger.info("AdvancedItineraryService 초기화 완료 - Dynamic AI Service 연결됨")

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
        prompt1 = f"""당신은 'Plango AI'라는 이름의 세계 최고의 여행 컨설턴트이자 키워드 추출 전문가입니다.
당신의 임무는 사용자의 여행 요청을 분석하여, 여행의 핵심 테마를 정의하고, 그 테마에 맞는 활동들을 검색 가능한 '키워드'로 구조화하는 것입니다.

**사용자 여행 정보:**
- 목적지: {request.city}
- 기간: {request.duration}일
- 예산: {getattr(request, 'budget_range', 'medium')}
- 여행 스타일: {getattr(request, 'travel_style', [])}
- 특별 요청사항: {request.special_requests or '일반적인 여행'}

**## 지시사항 ##**
1. **입력 분석:** 사용자가 제공한 여행 정보를 완벽하게 분석합니다.
2. **테마 설정:** 분석 내용을 바탕으로 여행의 전체적인 컨셉을 한 문장으로 정의합니다.
3. **키워드 추출:** 사용자의 요청을 충족시킬 수 있는 장소나 활동 유형을 '검색어' 형태로 생성합니다.
4. **응답 형식:** 당신의 답변은 **반드시** 아래에 명시된 구조의 **JSON 객체 하나**여야 합니다. 다른 설명은 절대 추가하지 마세요.

**## 핵심 규칙 (매우 중요) ##**
- **절대 특정 상호명이나 장소명을 제안하지 마세요.** (예: '이치란 라멘' (X) -> '{request.city} 현지인 추천 돈코츠 라멘 맛집' (O))
- 키워드는 사용자의 숨은 니즈를 반영해야 합니다.
- 카테고리는 'food', 'activity', 'healing', 'history', 'shopping', 'nature' 중에서 선택하세요.
- 우선순위는 사용자가 명시적으로 언급한 요청에 따라 'high', 'medium', 'low'로 설정하세요.

**응답 JSON 구조:**
{{
  "theme": "여행 테마 한 문장",
  "search_keywords": [
    {{
      "keyword": "검색 키워드",
      "category": "카테고리",
      "priority": "우선순위",
      "description": "키워드 설명"
    }}
  ]
}}"""

        try:
            # Dynamic AI Service 사용
            content = await self.ai_service.generate_text(prompt1, max_tokens=1500)
            
            # JSON 파싱
            ai_response = json.loads(content)
            
            # 새로운 응답 구조에서 카테고리별 키워드 추출
            place_candidates = {}
            if "search_keywords" in ai_response:
                for keyword_info in ai_response["search_keywords"]:
                    category = keyword_info.get("category", "activity")
                    keyword = keyword_info.get("keyword", "")
                    
                    if category not in place_candidates:
                        place_candidates[category] = []
                    place_candidates[category].append(keyword)
            
            # 테마 정보 저장 (나중에 사용)
            self.travel_theme = ai_response.get("theme", f"{request.city} 여행")
            
            return place_candidates
            
        except Exception as e:
            logger.error(f"1단계 AI 브레인스토밍 실패: {str(e)}")
            # 기본 후보 반환
            return {
                "food": [f"{request.city} 맛집", f"{request.city} 현지 음식"],
                "activity": [f"{request.city} 관광명소", f"{request.city} 액티비티"],
                "healing": [f"{request.city} 카페", f"{request.city} 힐링 스팟"],
                "history": [f"{request.city} 박물관", f"{request.city} 역사 유적지"],
                "shopping": [f"{request.city} 쇼핑몰", f"{request.city} 시장"],
                "nature": [f"{request.city} 공원", f"{request.city} 자연 명소"]
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
        
        prompt2 = f"""당신은 'Plango AI'라는 이름의 최고의 여행 일정 설계 전문가입니다.
당신의 임무는 사전 검증된 장소 목록과 사용자의 원래 요청사항을 바탕으로, 가장 효율적이고 매력적인 일일 여행 계획을 수립하는 것입니다.

**사용자의 원래 요청사항:**
- 목적지: {request.city}
- 여행 기간: {request.duration}일
- 예산: {getattr(request, 'budget_range', 'medium')}
- 여행 스타일: {getattr(request, 'travel_style', [])}
- 특별 요청사항: {request.special_requests or '일반적인 여행'}

**API로 검증된 장소 목록:**
```json
{json.dumps(place_pool, ensure_ascii=False, indent=2)}
```

**## 지시사항 ##**
1. **입력 분석:** 사용자의 원래 요청사항과 API로 검증된 장소 목록을 함께 분석합니다.
2. **동선 최적화:** 각 장소의 위도/경도 정보를 활용하여, 지리적으로 가까운 장소들을 같은 날 일정으로 묶어 이동 시간을 최소화합니다. 이것이 가장 중요한 임무입니다.
3. **논리적 시간 배분:** 활동들을 '오전', '점심', '오후', '저녁' 시간대에 맞게 논리적으로 배치합니다.
4. **사용자 맞춤:** 사용자의 원래 요청(여유롭게, 빡빡하게 등)을 참고하여 하루에 배치할 활동의 개수를 조절합니다.
5. **응답 형식:** 당신의 답변은 **반드시** 아래에 명시된 구조의 **JSON 객체 하나**여야 합니다. 다른 설명은 절대 추가하지 마세요.

**## 핵심 규칙 (매우 중요) ##**
- **데이터 무결성:** 장소 목록에 제공된 `place_id`와 `name`을 절대 변경하거나 누락하지 말고, 그대로 출력 JSON에 포함시켜야 합니다.
- **지리적 클러스터링:** 위도/경도 좌표를 기준으로 가장 가까운 장소들을 묶는 것을 최우선으로 고려하세요.
- **창의적 설명:** 각 날짜의 `theme`과 각 활동의 `activity_description`을 사용자가 기대할 만한 매력적인 문장으로 작성해주세요.

**출력 JSON 구조:**
{{
  "itinerary": {{
    "title": "여행 일정 제목",
    "concept": "여행 컨셉 설명",
    "daily_plans": [
      {{
        "day": 1,
        "theme": "첫째 날 테마",
        "activities": [
          {{
            "time": "09:00 - 11:00",
            "place_name": "장소명",
            "activity_description": "활동 설명",
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
            # Dynamic AI Service 사용
            content = await self.ai_service.generate_text(prompt2, max_tokens=4000)
            
            # JSON 파싱
            ai_response = json.loads(content)
            
            # 새로운 응답 구조 처리 (단일 itinerary)
            if "itinerary" in ai_response:
                return ai_response
            else:
                # 기본 계획 반환
                return self._create_basic_plans(request, place_pool)
            
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
        
        # 단일 itinerary 구조 처리
        itinerary_data = ai_plans.get("itinerary", {})
        main_plan = create_travel_plan(itinerary_data)
        
        return GenerateResponse(
            plan_a=main_plan,
            plan_b=main_plan,  # 호환성을 위해 동일한 계획 제공
            request_id=request_id,
            generated_at=datetime.now().isoformat()
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
            generated_at=datetime.now().isoformat()
        )

    def _create_basic_plans(self, request: GenerateRequest, place_pool: List[Dict[str, Any]]) -> Dict[str, Any]:
        """기본 계획을 생성합니다"""
        return {
            "itinerary": {
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