#!/usr/bin/env python3
"""
서비스 영향도 테스트 스크립트
"""

import asyncio
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.geocoding_service import GeocodingService
from app.services.google_places_service import GooglePlacesService
from app.services.google_directions_service import GoogleDirectionsService
from app.schemas.place import PlaceRecommendationRequest

async def test_geocoding_service():
    """Geocoding 서비스 테스트"""
    print("🌍 [GEOCODING SERVICE] 테스트 시작")
    
    try:
        service = GeocodingService()
        
        # 광주 테스트
        results = await service.get_geocode_results("광주, 대한민국")
        print(f"✅ Geocoding 서비스 성공: {len(results)}개 결과")
        
        # 동명 지역 확인
        is_ambiguous = service.is_ambiguous_location(results)
        print(f"동명 지역 여부: {is_ambiguous}")
        
        return True
        
    except Exception as e:
        print(f"❌ Geocoding 서비스 실패: {e}")
        return False

async def test_places_service():
    """Places 서비스 테스트"""
    print("\n🏢 [PLACES SERVICE] 테스트 시작")
    
    try:
        service = GooglePlacesService()
        
        # 텍스트 검색 테스트
        results = await service.search_places_by_text("서울 맛집", language="ko")
        print(f"✅ Places 서비스 성공: {len(results)}개 결과")
        
        return True
        
    except Exception as e:
        print(f"❌ Places 서비스 실패: {e}")
        return False

async def test_directions_service():
    """Directions 서비스 테스트"""
    print("\n🚗 [DIRECTIONS SERVICE] 테스트 시작")
    
    try:
        service = GoogleDirectionsService()
        
        # 경로 검색 테스트
        result = await service.get_directions(
            origin="서울역",
            destination="강남역",
            mode="transit"
        )
        
        if result:
            print(f"✅ Directions 서비스 성공")
            print(f"소요시간: {result.get('duration', 'N/A')}")
            print(f"거리: {result.get('distance', 'N/A')}")
        else:
            print("❌ Directions 서비스 실패: 결과 없음")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Directions 서비스 실패: {e}")
        return False

async def test_place_recommendations():
    """장소 추천 서비스 테스트"""
    print("\n🎯 [PLACE RECOMMENDATIONS] 테스트 시작")
    
    try:
        from app.routers.place_recommendations import generate_place_recommendations
        
        request = PlaceRecommendationRequest(
            city="서울",
            country="대한민국",
            total_duration=3,
            travelers_count=2,
            travel_style="관광",
            budget_level="중간"
        )
        
        response = await generate_place_recommendations(request)
        print(f"✅ 장소 추천 서비스 성공")
        print(f"신규 추천: {response.newly_recommended_count}개")
        print(f"폴백 여부: {getattr(response, 'is_fallback', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 장소 추천 서비스 실패: {e}")
        return False

async def test_itinerary_creation():
    """일정 생성 서비스 테스트"""
    print("\n📅 [ITINERARY CREATION] 테스트 시작")
    
    try:
        from app.services.advanced_itinerary_service import AdvancedItineraryService
        from app.services.enhanced_ai_service import EnhancedAIService
        from app.schemas.itinerary import PlaceData
        
        # 테스트용 장소 데이터
        places = [
            PlaceData(
                place_id="test1",
                name="경복궁",
                category="관광",
                lat=37.5788,
                lng=126.9770,
                address="서울 종로구"
            ),
            PlaceData(
                place_id="test2", 
                name="명동",
                category="쇼핑",
                lat=37.5636,
                lng=126.9834,
                address="서울 중구"
            )
        ]
        
        ai_service = EnhancedAIService()
        places_service = GooglePlacesService()
        itinerary_service = AdvancedItineraryService(ai_service, places_service)
        
        constraints = {
            "duration": 2,
            "daily_start_time": "09:00",
            "daily_end_time": "21:00"
        }
        
        result = await itinerary_service.create_final_itinerary(places, constraints)
        
        if result and result.travel_plan:
            print(f"✅ 일정 생성 서비스 성공")
            print(f"일정 기간: {result.travel_plan.total_days}일")
            print(f"일별 계획: {len(result.travel_plan.days)}개")
        else:
            print("❌ 일정 생성 서비스 실패: 결과 없음")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 일정 생성 서비스 실패: {e}")
        return False

async def main():
    """메인 테스트 함수"""
    print("🚀 서비스 영향도 테스트 시작")
    print("=" * 60)
    
    tests = [
        ("Geocoding Service", test_geocoding_service),
        ("Places Service", test_places_service),
        ("Directions Service", test_directions_service),
        ("Place Recommendations", test_place_recommendations),
        ("Itinerary Creation", test_itinerary_creation),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            success = await test_func()
            results[test_name] = success
        except Exception as e:
            print(f"💥 {test_name} 테스트 중 예외 발생: {e}")
            results[test_name] = False
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 서비스 영향도 분석")
    print("=" * 60)
    
    working_services = []
    broken_services = []
    
    for service_name, success in results.items():
        if success:
            working_services.append(service_name)
            print(f"✅ {service_name}: 정상 작동")
        else:
            broken_services.append(service_name)
            print(f"❌ {service_name}: 작동 불가")
    
    print(f"\n📈 정상 작동: {len(working_services)}개")
    print(f"📉 작동 불가: {len(broken_services)}개")
    
    if len(working_services) > 0:
        print(f"\n🎯 폴백 시스템이 작동하여 일부 서비스는 계속 이용 가능합니다.")
    
    if len(broken_services) == len(tests):
        print(f"\n🚨 모든 서비스가 영향을 받았습니다. 즉시 API 키 문제를 해결해야 합니다.")

if __name__ == "__main__":
    asyncio.run(main())