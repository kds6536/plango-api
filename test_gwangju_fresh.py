#!/usr/bin/env python3
"""
광주 동명 지역 테스트 - 캐시 우회
"""

import asyncio
import httpx
from datetime import datetime

# Railway 배포된 API URL
API_BASE_URL = "https://plango-api-production.up.railway.app"

async def test_gwangju_variations():
    """광주의 다양한 표기법으로 테스트"""
    
    # 광주의 다양한 표기법들
    test_cases = [
        {"city": "광주", "country": "한국", "description": "광주, 한국"},
        {"city": "Gwangju", "country": "South Korea", "description": "Gwangju, South Korea"},
        {"city": "광주시", "country": "대한민국", "description": "광주시, 대한민국"},
        {"city": "Gwangju City", "country": "Korea", "description": "Gwangju City, Korea"},
    ]
    
    print("🔍 [GWANGJU_TEST] 광주 동명 지역 테스트 (다양한 표기법)")
    print(f"🌐 [API_URL] {API_BASE_URL}")
    print(f"⏰ [START_TIME] {datetime.now().isoformat()}")
    print("=" * 70)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 [TEST_{i}] {test_case['description']} 테스트")
            print(f"📍 [INPUT] 도시: '{test_case['city']}', 국가: '{test_case['country']}'")
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
                            display_name = option.get('display_name', 'Unknown')
                            formatted_address = option.get('formatted_address', 'Unknown')
                            print(f"  {j+1}. {display_name}")
                            print(f"     주소: {formatted_address}")
                        return True
                    else:
                        print(f"📝 [ERROR_DETAIL] {data.get('detail', 'Unknown error')}")
                        
                elif response.status_code == 200:
                    data = response.json()
                    new_count = data.get("newly_recommended_count", 0)
                    prev_count = data.get("previously_recommended_count", 0)
                    print(f"📝 [SUCCESS] 추천 성공: 신규 {new_count}개, 기존 {prev_count}개")
                    
                    if prev_count > 0:
                        print("ℹ️ [CACHE_HIT] 캐시된 데이터가 있어서 동명 지역 체크를 건너뛴 것 같습니다.")
                    else:
                        print("ℹ️ [NO_AMBIGUOUS] 동명 지역으로 감지되지 않았습니다.")
                    
                else:
                    print(f"📝 [OTHER] {response.text[:200]}")
                    
            except Exception as e:
                print(f"❌ [ERROR] 요청 실패: {e}")
            
            # 다음 요청 전 잠시 대기
            if i < len(test_cases):
                print("⏳ [WAIT] 2초 대기...")
                await asyncio.sleep(2)
    
    return False

async def main():
    success = await test_gwangju_variations()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ [SUCCESS] 광주에서 동명 지역이 감지되었습니다!")
    else:
        print("⚠️ [INFO] 광주에서 동명 지역이 감지되지 않았습니다.")
        print("💡 [ANALYSIS] 가능한 원인:")
        print("   1. 이미 캐시된 데이터가 있어서 Geocoding을 건너뜀")
        print("   2. Google Geocoding API가 광주를 명확한 단일 결과로 반환")
        print("   3. is_ambiguous_location 로직이 광주를 동명 지역으로 판단하지 않음")
        print()
        print("🔍 [RECOMMENDATION] Railway 로그에서 다음을 확인:")
        print("   - [STEP_1_GEOCODING] 로그가 나타나는지")
        print("   - [AMBIGUOUS_CHECK] 로그와 결과")
        print("   - [GEOCODING_RESULTS] 결과 개수")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())