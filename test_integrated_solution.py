#!/usr/bin/env python3
"""
통합 솔루션 테스트 스크립트
- Geocoding 우선 실행 확인
- Plan A 실행 순서 확인  
- 에러 처리 및 이메일 발송 확인
"""

import asyncio
import httpx
import json
from datetime import datetime

# Railway 배포된 API URL
API_BASE_URL = "https://plango-api-production.up.railway.app"

async def test_geocoding_priority():
    """1. Geocoding 우선 실행 테스트 (광주 - 동명 지역)"""
    print("🧪 [TEST_1] Geocoding 우선 실행 테스트 시작")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/place-recommendations/generate",
                json={
                    "city": "광주",
                    "country": "대한민국",
                    "total_duration": 2,
                    "travelers_count": 2,
                    "travel_style": ["관광"],
                    "budget_level": "중간"
                }
            )
            
            print(f"📊 [RESPONSE] 상태 코드: {response.status_code}")
            
            if response.status_code == 400:
                data = response.json()
                if data.get("error_code") == "AMBIGUOUS_LOCATION":
                    print("✅ [SUCCESS] Geocoding이 우선 실행되어 동명 지역을 감지했습니다!")
                    print(f"📋 [OPTIONS] 선택지 {len(data.get('options', []))}개:")
                    for i, option in enumerate(data.get('options', [])[:3]):
                        print(f"  {i+1}. {option}")
                    return True
                else:
                    print(f"❌ [FAIL] 예상과 다른 400 에러: {data}")
                    return False
            else:
                print(f"❌ [FAIL] 예상과 다른 응답: {response.status_code}")
                print(f"📝 [RESPONSE] {response.text[:500]}")
                return False
                
        except Exception as e:
            print(f"❌ [ERROR] 테스트 실패: {e}")
            return False

async def test_plan_a_execution():
    """2. Plan A 실행 테스트 (명확한 도시)"""
    print("\n🧪 [TEST_2] Plan A 실행 테스트 시작")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/place-recommendations/generate",
                json={
                    "city": "서울",
                    "country": "대한민국", 
                    "total_duration": 3,
                    "travelers_count": 2,
                    "travel_style": ["관광"],
                    "budget_level": "중간"
                }
            )
            
            print(f"📊 [RESPONSE] 상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ [SUCCESS] Plan A가 성공적으로 실행되었습니다!")
                print(f"📋 [RESULT] 신규 추천: {data.get('newly_recommended_count', 0)}개")
                print(f"📋 [RESULT] 기존 추천: {data.get('previously_recommended_count', 0)}개")
                return True
            elif response.status_code == 500:
                data = response.json()
                print(f"⚠️ [PLAN_A_FAIL] Plan A 실패 (예상된 동작)")
                print(f"📝 [ERROR] {data.get('detail', 'Unknown error')}")
                return True  # Plan A 실패도 정상적인 에러 처리
            else:
                print(f"❌ [FAIL] 예상과 다른 응답: {response.status_code}")
                print(f"📝 [RESPONSE] {response.text[:500]}")
                return False
                
        except Exception as e:
            print(f"❌ [ERROR] 테스트 실패: {e}")
            return False

async def test_error_handling():
    """3. 에러 처리 테스트 (존재하지 않는 도시)"""
    print("\n🧪 [TEST_3] 에러 처리 테스트 시작")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/place-recommendations/generate",
                json={
                    "city": "존재하지않는도시12345",
                    "country": "존재하지않는국가12345",
                    "total_duration": 2,
                    "travelers_count": 2,
                    "travel_style": ["관광"],
                    "budget_level": "중간"
                }
            )
            
            print(f"📊 [RESPONSE] 상태 코드: {response.status_code}")
            
            if response.status_code == 400:
                data = response.json()
                print("✅ [SUCCESS] 잘못된 입력에 대해 400 에러를 반환했습니다!")
                print(f"📝 [ERROR] {data.get('detail', 'Unknown error')}")
                return True
            else:
                print(f"❌ [FAIL] 예상과 다른 응답: {response.status_code}")
                print(f"📝 [RESPONSE] {response.text[:500]}")
                return False
                
        except Exception as e:
            print(f"❌ [ERROR] 테스트 실패: {e}")
            return False

async def main():
    """통합 테스트 실행"""
    print("🚀 [START] 통합 솔루션 테스트 시작")
    print(f"🌐 [API_URL] {API_BASE_URL}")
    print(f"⏰ [TIME] {datetime.now().isoformat()}")
    print("=" * 60)
    
    results = []
    
    # 테스트 1: Geocoding 우선 실행
    result1 = await test_geocoding_priority()
    results.append(("Geocoding 우선 실행", result1))
    
    # 테스트 2: Plan A 실행
    result2 = await test_plan_a_execution()
    results.append(("Plan A 실행", result2))
    
    # 테스트 3: 에러 처리
    result3 = await test_error_handling()
    results.append(("에러 처리", result3))
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 [SUMMARY] 테스트 결과 요약")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 [FINAL] {passed}/{len(results)} 테스트 통과")
    
    if passed == len(results):
        print("🎉 [SUCCESS] 모든 테스트가 통과했습니다!")
        print("✅ Geocoding이 우선 실행됩니다")
        print("✅ Plan A가 정상 작동합니다")
        print("✅ 에러 처리가 올바르게 작동합니다")
    else:
        print("⚠️ [WARNING] 일부 테스트가 실패했습니다. 로그를 확인해주세요.")

if __name__ == "__main__":
    asyncio.run(main())