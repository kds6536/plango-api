#!/usr/bin/env python3
"""
동명 지역 테스트 스크립트
광주 대신 다른 동명 지역으로 테스트
"""

import asyncio
import httpx
from datetime import datetime

# Railway 배포된 API URL
API_BASE_URL = "https://plango-api-production.up.railway.app"

async def test_ambiguous_cities():
    """다양한 동명 지역 테스트"""
    
    # 실제 동명 도시들
    test_cities = [
        {"city": "광주", "country": "대한민국", "description": "광주광역시 vs 경기도 광주시"},
        {"city": "Springfield", "country": "United States", "description": "미국의 여러 Springfield 도시들"},
        {"city": "Cambridge", "country": "United States", "description": "매사추세츠 Cambridge vs 다른 주의 Cambridge"},
        {"city": "Richmond", "country": "United States", "description": "버지니아 Richmond vs 캘리포니아 Richmond"},
        {"city": "Portland", "country": "United States", "description": "오레곤 Portland vs 메인 Portland"},
    ]
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        for i, test_case in enumerate(test_cities, 1):
            print(f"\n🧪 [TEST_{i}] {test_case['description']} 테스트")
            print(f"📍 [CITY] {test_case['city']}, {test_case['country']}")
            print(f"⏰ [TIME] {datetime.now().isoformat()}")
            
            try:
                response = await client.post(
                    f"{API_BASE_URL}/api/v1/place-recommendations/generate",
                    json={
                        "city": test_case['city'],
                        "country": test_case['country'],
                        "total_duration": 2,
                        "travelers_count": 2,
                        "travel_style": ["관광"],
                        "budget_level": "중간"
                    }
                )
                
                print(f"📊 [RESPONSE] 상태 코드: {response.status_code}")
                
                if response.status_code == 400:
                    data = response.json()
                    error_code = data.get("error_code", "UNKNOWN")
                    print(f"📝 [ERROR_CODE] {error_code}")
                    
                    if error_code == "AMBIGUOUS_LOCATION":
                        options = data.get("options", [])
                        print(f"✅ [SUCCESS] 동명 지역 감지! 선택지 {len(options)}개:")
                        for j, option in enumerate(options[:3]):
                            print(f"  {j+1}. {option}")
                        return True
                    else:
                        print(f"📝 [ERROR_DETAIL] {data.get('detail', 'Unknown error')}")
                        
                elif response.status_code == 200:
                    data = response.json()
                    new_count = data.get("newly_recommended_count", 0)
                    print(f"📝 [SUCCESS] 추천 성공: 신규 {new_count}개")
                    print("ℹ️ [INFO] 이미 캐시된 데이터가 있거나 동명 지역이 아닙니다.")
                    
                else:
                    print(f"📝 [OTHER] {response.text[:200]}")
                    
            except Exception as e:
                print(f"❌ [ERROR] 요청 실패: {e}")
            
            # 다음 요청 전 잠시 대기
            if i < len(test_cities):
                print("⏳ [WAIT] 3초 대기...")
                await asyncio.sleep(3)
    
    return False

async def main():
    """메인 실행 함수"""
    print("🔍 [AMBIGUOUS_TEST] 동명 지역 감지 테스트")
    print(f"🌐 [API_URL] {API_BASE_URL}")
    print(f"⏰ [START_TIME] {datetime.now().isoformat()}")
    print("=" * 60)
    
    success = await test_ambiguous_cities()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ [SUCCESS] 동명 지역 감지 기능이 정상 작동합니다!")
    else:
        print("⚠️ [INFO] 테스트한 도시들에서 동명 지역이 감지되지 않았습니다.")
        print("💡 [TIP] 이는 다음 이유일 수 있습니다:")
        print("   1. 이미 캐시된 데이터가 있음")
        print("   2. Geocoding API가 명확한 결과만 반환함")
        print("   3. 동명 지역 감지 로직이 더 엄격함")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())