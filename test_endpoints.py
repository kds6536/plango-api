#!/usr/bin/env python3
"""
간단한 테스트 스크립트
"""

import asyncio
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.geocoding_service import GeocodingService
from app.schemas.place import PlaceRecommendationRequest

async def test_geocoding():
    """Geocoding 서비스 테스트"""
    print("🧪 Geocoding 서비스 테스트 시작")
    
    try:
        geocoding_service = GeocodingService()
        
        # 광주 테스트 (동명 지역)
        print("\n1. 광주 테스트 (동명 지역 예상)")
        results = await geocoding_service.get_geocode_results("광주, 대한민국")
        print(f"결과 수: {len(results)}")
        
        is_ambiguous = geocoding_service.is_ambiguous_location(results)
        print(f"동명 지역 여부: {is_ambiguous}")
        
        if is_ambiguous:
            options = geocoding_service.format_location_options(results)
            print("선택지:")
            for i, option in enumerate(options):
                print(f"  {i+1}. {option['display_name']}")
        
        # 서울 테스트 (단일 지역)
        print("\n2. 서울 테스트 (단일 지역 예상)")
        results = await geocoding_service.get_geocode_results("서울, 대한민국")
        print(f"결과 수: {len(results)}")
        
        is_ambiguous = geocoding_service.is_ambiguous_location(results)
        print(f"동명 지역 여부: {is_ambiguous}")
        
        print("✅ Geocoding 테스트 완료")
        
    except Exception as e:
        print(f"❌ Geocoding 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

async def test_fallback():
    """폴백 시스템 테스트"""
    print("\n🧪 폴백 시스템 테스트 시작")
    
    try:
        from app.routers.place_recommendations import generate_fallback_recommendations
        
        test_request = PlaceRecommendationRequest(
            city="서울",
            country="대한민국",
            total_duration=3,
            travelers_count=2,
            travel_style="관광",
            budget_level="중간"
        )
        
        response = await generate_fallback_recommendations(test_request)
        print(f"폴백 응답: {response}")
        print("✅ 폴백 테스트 완료")
        
    except Exception as e:
        print(f"❌ 폴백 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

async def test_email_notification():
    """이메일 알림 시스템 테스트"""
    print("\n📧 이메일 알림 시스템 테스트 시작")
    
    try:
        from app.routers.place_recommendations import send_admin_notification
        
        # 테스트 데이터
        test_request_data = {
            "city": "테스트시티",
            "country": "테스트국가",
            "total_duration": 3,
            "travelers_count": 2,
            "travel_style": "관광",
            "budget_level": "중간"
        }
        
        # 이메일 발송 테스트
        await send_admin_notification(
            subject="[Plango] 테스트 - 이메일 시스템 동작 확인",
            error_type="EMAIL_SYSTEM_TEST",
            error_details="이 메시지가 로그에 보인다면 이메일 시스템이 정상 작동하는 것입니다.",
            user_request=test_request_data
        )
        
        print("✅ 이메일 알림 테스트 완료 - 로그를 확인하세요")
        
    except Exception as e:
        print(f"❌ 이메일 알림 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

async def test_geocoding_failure_with_email():
    """Geocoding 실패 시 이메일 알림 포함 테스트"""
    print("\n🚨 Geocoding 실패 + 이메일 알림 통합 테스트 시작")
    
    try:
        from app.routers.place_recommendations import send_admin_notification, generate_fallback_recommendations
        
        # 존재하지 않는 도시로 테스트
        test_request = PlaceRecommendationRequest(
            city="존재하지않는도시12345",
            country="존재하지않는국가12345",
            total_duration=3,
            travelers_count=2,
            travel_style="관광",
            budget_level="중간"
        )
        
        print("1. Geocoding 실패 시뮬레이션...")
        
        # Geocoding 실패 시나리오 시뮬레이션
        geocoding_error = "REQUEST_DENIED (API keys with referer restrictions cannot be used with this API.)"
        
        # 관리자 이메일 알림 발송
        print("2. 관리자 이메일 알림 발송...")
        await send_admin_notification(
            subject="[Plango] Geocoding API 실패 - 폴백 시스템 활성화",
            error_type="GEOCODING_FAILURE",
            error_details=geocoding_error,
            user_request=test_request.model_dump()
        )
        
        # 폴백 시스템 실행
        print("3. 폴백 시스템 실행...")
        fallback_response = await generate_fallback_recommendations(test_request)
        
        print(f"✅ 통합 테스트 완료")
        print(f"   - 이메일 알림: 발송됨 (로그 확인)")
        print(f"   - 폴백 응답: {fallback_response.newly_recommended_count}개 장소 반환")
        print(f"   - 폴백 여부: {fallback_response.is_fallback}")
        
    except Exception as e:
        print(f"❌ 통합 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

async def test_plan_a_failure_with_email():
    """Plan A 실패 시 이메일 알림 포함 테스트"""
    print("\n🚨 Plan A 실패 + 이메일 알림 통합 테스트 시작")
    
    try:
        from app.routers.place_recommendations import send_admin_notification, generate_fallback_recommendations
        
        test_request = PlaceRecommendationRequest(
            city="서울",
            country="대한민국",
            total_duration=3,
            travelers_count=2,
            travel_style="관광",
            budget_level="중간"
        )
        
        print("1. Plan A 실패 시뮬레이션...")
        
        # Plan A 실패 시나리오 시뮬레이션
        plan_a_error = "Plan A에서 충분한 추천 결과를 생성하지 못했습니다"
        
        # 관리자 이메일 알림 발송
        print("2. 관리자 이메일 알림 발송...")
        await send_admin_notification(
            subject="[Plango] Plan A 실패 - 폴백 시스템 활성화",
            error_type="PLAN_A_FAILURE",
            error_details=plan_a_error,
            user_request=test_request.model_dump()
        )
        
        # 폴백 시스템 실행
        print("3. 폴백 시스템 실행...")
        fallback_response = await generate_fallback_recommendations(test_request)
        
        print(f"✅ Plan A 실패 통합 테스트 완료")
        print(f"   - 이메일 알림: 발송됨 (로그 확인)")
        print(f"   - 폴백 응답: {fallback_response.newly_recommended_count}개 장소 반환")
        print(f"   - 폴백 이유: {fallback_response.fallback_reason}")
        
    except Exception as e:
        print(f"❌ Plan A 실패 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """메인 테스트 함수"""
    print("🚀 테스트 시작")
    
    await test_geocoding()
    await test_fallback()
    await test_email_notification()
    await test_geocoding_failure_with_email()
    await test_plan_a_failure_with_email()
    
    print("\n🏁 모든 테스트 완료")

if __name__ == "__main__":
    asyncio.run(main())