#!/usr/bin/env python3
"""
API 엔드포인트 테스트 스크립트
"""

import asyncio
import aiohttp
import json

BASE_URL = "http://localhost:8000"

async def test_email_notification_endpoint():
    """이메일 알림 엔드포인트 테스트"""
    print("📧 이메일 알림 엔드포인트 테스트 시작")
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{BASE_URL}/api/v1/place-recommendations/test-email-notification"
            
            async with session.post(url) as response:
                status = response.status
                data = await response.json()
                
                print(f"응답 상태: {status}")
                print(f"응답 데이터: {json.dumps(data, indent=2, ensure_ascii=False)}")
                
                if status == 200:
                    print("✅ 이메일 알림 엔드포인트 테스트 성공")
                else:
                    print(f"❌ 이메일 알림 엔드포인트 테스트 실패: {status}")
                    
    except Exception as e:
        print(f"❌ 이메일 알림 엔드포인트 테스트 에러: {e}")

async def test_geocoding_failure_endpoint():
    """Geocoding 실패 엔드포인트 테스트"""
    print("\n🚨 Geocoding 실패 엔드포인트 테스트 시작")
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{BASE_URL}/api/v1/place-recommendations/test-geocoding-failure"
            
            async with session.post(url) as response:
                status = response.status
                data = await response.json()
                
                print(f"응답 상태: {status}")
                print(f"응답 데이터: {json.dumps(data, indent=2, ensure_ascii=False)}")
                
                if status == 200:
                    print("✅ Geocoding 실패 엔드포인트 테스트 성공")
                    if data.get('is_fallback'):
                        print("✅ 폴백 시스템 정상 작동 확인")
                else:
                    print(f"❌ Geocoding 실패 엔드포인트 테스트 실패: {status}")
                    
    except Exception as e:
        print(f"❌ Geocoding 실패 엔드포인트 테스트 에러: {e}")

async def test_ambiguous_location_endpoint():
    """동명 지역 엔드포인트 테스트"""
    print("\n🔍 동명 지역 엔드포인트 테스트 시작")
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{BASE_URL}/api/v1/place-recommendations/test-ambiguous-location"
            
            async with session.post(url) as response:
                status = response.status
                data = await response.json()
                
                print(f"응답 상태: {status}")
                print(f"응답 데이터: {json.dumps(data, indent=2, ensure_ascii=False)}")
                
                if status in [200, 400]:  # 400은 AMBIGUOUS_LOCATION 응답
                    print("✅ 동명 지역 엔드포인트 테스트 성공")
                    if data.get('error_code') == 'AMBIGUOUS_LOCATION':
                        print("✅ 동명 지역 감지 기능 정상 작동")
                else:
                    print(f"❌ 동명 지역 엔드포인트 테스트 실패: {status}")
                    
    except Exception as e:
        print(f"❌ 동명 지역 엔드포인트 테스트 에러: {e}")

async def test_real_recommendation_with_fallback():
    """실제 추천 요청으로 폴백 시스템 테스트"""
    print("\n🎯 실제 추천 요청 폴백 테스트 시작")
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{BASE_URL}/api/v1/place-recommendations/generate"
            
            # 존재하지 않는 도시로 요청하여 폴백 트리거
            payload = {
                "city": "존재하지않는도시12345",
                "country": "존재하지않는국가12345",
                "total_duration": 3,
                "travelers_count": 2,
                "travel_style": "관광",
                "budget_level": "중간"
            }
            
            async with session.post(url, json=payload) as response:
                status = response.status
                data = await response.json()
                
                print(f"응답 상태: {status}")
                print(f"응답 데이터: {json.dumps(data, indent=2, ensure_ascii=False)}")
                
                if status == 200:
                    print("✅ 실제 추천 요청 테스트 성공")
                    if data.get('is_fallback'):
                        print("✅ 폴백 시스템이 실제 요청에서도 정상 작동")
                        print(f"   - 폴백 이유: {data.get('fallback_reason')}")
                        print(f"   - 추천 장소 수: {data.get('newly_recommended_count')}")
                else:
                    print(f"❌ 실제 추천 요청 테스트 실패: {status}")
                    
    except Exception as e:
        print(f"❌ 실제 추천 요청 테스트 에러: {e}")

async def main():
    """메인 테스트 함수"""
    print("🚀 API 엔드포인트 테스트 시작")
    print(f"서버 URL: {BASE_URL}")
    print("⚠️  서버가 실행 중인지 확인하세요: uvicorn app.main:app --reload")
    print()
    
    await test_email_notification_endpoint()
    await test_geocoding_failure_endpoint()
    await test_ambiguous_location_endpoint()
    await test_real_recommendation_with_fallback()
    
    print("\n🏁 모든 API 엔드포인트 테스트 완료")

if __name__ == "__main__":
    asyncio.run(main())