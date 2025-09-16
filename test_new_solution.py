#!/usr/bin/env python3
"""
새로운 솔루션 테스트: 프론트엔드 Autocomplete + 백엔드 단순화
"""

import asyncio
import httpx
from datetime import datetime

# Railway 배포된 API URL
API_BASE_URL = "https://plango-api-production.up.railway.app"

async def test_new_solution():
    """새로운 솔루션 테스트"""
    
    print("🚀 [NEW_SOLUTION] 새로운 솔루션 테스트")
    print(f"🌐 [API_URL] {API_BASE_URL}")
    print(f"⏰ [TIME] {datetime.now().isoformat()}")
    print("=" * 70)
    
    print("\n📋 [SOLUTION_OVERVIEW] 새로운 솔루션 개요:")
    print("1. 프론트엔드: Google Places Autocomplete로 명확한 도시 선택")
    print("2. 백엔드: Geocoding 로직 제거, 바로 캐시 확인 → Plan A")
    print("3. 장점: 동명 지역 문제 원천 차단, 백엔드 로직 단순화")
    
    # 테스트 케이스들
    test_cases = [
        {
            "name": "place_id 없는 기존 방식 (서울)",
            "data": {
                "city": "서울",
                "country": "대한민국",
                "total_duration": 2,
                "travelers_count": 2,
                "travel_style": ["관광"],
                "budget_level": "중간"
            }
        },
        {
            "name": "place_id 포함된 새로운 방식 (광주광역시)",
            "data": {
                "city": "광주광역시",
                "country": "대한민국",
                "total_duration": 2,
                "travelers_count": 2,
                "travel_style": ["관광"],
                "budget_level": "중간",
                "place_id": "ChIJr6f1ASOJcTURSPUlAe3S9AU"  # 광주광역시 place_id
            }
        },
        {
            "name": "존재하지 않는 도시 (에러 처리 확인)",
            "data": {
                "city": "존재하지않는도시999",
                "country": "존재하지않는국가999",
                "total_duration": 2,
                "travelers_count": 2,
                "travel_style": ["관광"],
                "budget_level": "중간"
            }
        }
    ]
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 [TEST_{i}] {test_case['name']}")
            print(f"📍 [DATA] {test_case['data']['city']}, {test_case['data']['country']}")
            if 'place_id' in test_case['data']:
                print(f"🆔 [PLACE_ID] {test_case['data']['place_id']}")
            print(f"⏰ [TIME] {datetime.now().isoformat()}")
            
            try:
                response = await client.post(
                    f"{API_BASE_URL}/api/v1/place-recommendations/generate",
                    json=test_case['data']
                )
                
                print(f"📊 [RESPONSE] 상태 코드: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    new_count = data.get("newly_recommended_count", 0)
                    prev_count = data.get("previously_recommended_count", 0)
                    city_id = data.get("city_id", "Unknown")
                    main_theme = data.get("main_theme", "Unknown")
                    
                    print(f"✅ [SUCCESS] 추천 성공!")
                    print(f"   - 도시 ID: {city_id}")
                    print(f"   - 신규 추천: {new_count}개")
                    print(f"   - 기존 추천: {prev_count}개")
                    print(f"   - 메인 테마: {main_theme}")
                    
                elif response.status_code == 400:
                    data = response.json()
                    error_code = data.get("error_code", "UNKNOWN")
                    detail = data.get("detail", "Unknown error")
                    
                    print(f"⚠️ [CLIENT_ERROR] 400 에러")
                    print(f"   - 에러 코드: {error_code}")
                    print(f"   - 상세: {detail}")
                    
                elif response.status_code == 500:
                    data = response.json()
                    detail = data.get("detail", "Unknown error")
                    
                    print(f"❌ [SERVER_ERROR] 500 에러")
                    print(f"   - 상세: {detail}")
                    
                else:
                    print(f"📝 [OTHER] {response.status_code}: {response.text[:200]}")
                    
            except Exception as e:
                print(f"❌ [EXCEPTION] 요청 실패: {e}")
            
            # 다음 요청 전 잠시 대기
            if i < len(test_cases):
                print("⏳ [WAIT] 3초 대기...")
                await asyncio.sleep(3)

async def main():
    await test_new_solution()
    
    print("\n" + "=" * 70)
    print("🎯 [NEXT_STEPS] 다음 단계:")
    print("1. 프론트엔드에서 Google Places Autocomplete 테스트")
    print("2. 실제 브라우저에서 도시 선택 후 추천 요청")
    print("3. Railway 로그에서 새로운 실행 경로 확인")
    print("   - [STEP_1_PLAN_A] 로그 확인 (Geocoding 건너뛰기)")
    print("   - place_id 로깅 확인")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())