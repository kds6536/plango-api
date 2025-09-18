#!/usr/bin/env python3
"""
최종 솔루션 테스트: 모든 수정사항 적용 후 테스트
"""

import asyncio
import httpx
from datetime import datetime

# Railway 배포된 API URL
API_BASE_URL = "https://plango-api-production.up.railway.app"

async def test_final_solution():
    """최종 솔루션 테스트"""
    
    print("🎯 [FINAL_TEST] 최종 솔루션 테스트")
    print(f"🌐 [API_URL] {API_BASE_URL}")
    print(f"⏰ [TIME] {datetime.now().isoformat()}")
    print("=" * 70)
    
    print("\n✅ [APPLIED_FIXES] 적용된 수정사항:")
    print("1. 프론트엔드: 순수 도시명 추출 (국가명 제거)")
    print("2. 프론트엔드: place_id 포함하여 백엔드 전송")
    print("3. 백엔드: place_id 우선 처리, Geocoding 건너뛰기")
    
    # 테스트 케이스들
    test_cases = [
        {
            "name": "place_id 포함 - 광주광역시 (수정된 방식)",
            "data": {
                "city": "광주광역시",  # 순수 도시명
                "country": "대한민국",
                "total_duration": 2,
                "travelers_count": 2,
                "travel_style": ["관광"],
                "budget_level": "중간",
                "place_id": "ChIJr6f1ASOJcTURSPUlAe3S9AU"  # 광주광역시 place_id
            },
            "expected": "place_id가 있으므로 Geocoding 건너뛰고 바로 추천 생성"
        },
        {
            "name": "place_id 포함 - 서울 (수정된 방식)",
            "data": {
                "city": "서울특별시",  # 순수 도시명
                "country": "대한민국",
                "total_duration": 3,
                "travelers_count": 2,
                "travel_style": ["관광"],
                "budget_level": "중간",
                "place_id": "ChIJzWLAgCOUfDUR64Pq5LTtioU"  # 서울 place_id
            },
            "expected": "place_id가 있으므로 Geocoding 건너뛰고 바로 추천 생성"
        },
        {
            "name": "place_id 없음 - 기존 방식 (호환성 확인)",
            "data": {
                "city": "부산",
                "country": "대한민국",
                "total_duration": 2,
                "travelers_count": 2,
                "travel_style": ["관광"],
                "budget_level": "중간"
                # place_id 없음
            },
            "expected": "기존 방식으로 처리 (Geocoding 실행)"
        }
    ]
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 [TEST_{i}] {test_case['name']}")
            print(f"📍 [DATA] {test_case['data']['city']}, {test_case['data']['country']}")
            if 'place_id' in test_case['data']:
                print(f"🆔 [PLACE_ID] {test_case['data']['place_id']}")
            else:
                print("🆔 [PLACE_ID] 없음")
            print(f"🎯 [EXPECTED] {test_case['expected']}")
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
                    
                    # 성공 여부 판단
                    if city_id != 0 and (new_count > 0 or prev_count > 0):
                        print("🎉 [ANALYSIS] 정상적으로 추천이 생성되었습니다!")
                    elif main_theme == "AMBIGUOUS":
                        print("⚠️ [ANALYSIS] 여전히 AMBIGUOUS 상태입니다.")
                    else:
                        print("🤔 [ANALYSIS] 예상과 다른 결과입니다.")
                    
                elif response.status_code == 400:
                    data = response.json()
                    error_code = data.get("error_code", "UNKNOWN")
                    
                    if error_code == "AMBIGUOUS_LOCATION":
                        options = data.get("options", [])
                        print(f"⚠️ [AMBIGUOUS] 동명 지역 감지: {len(options)}개 선택지")
                        print("🤔 [ANALYSIS] place_id가 있음에도 동명 지역 처리가 실행되었습니다.")
                    else:
                        print(f"⚠️ [CLIENT_ERROR] 400 에러: {error_code}")
                    
                elif response.status_code == 500:
                    data = response.json()
                    detail = data.get("detail", "Unknown error")
                    print(f"❌ [SERVER_ERROR] 500 에러: {detail}")
                    
                else:
                    print(f"📝 [OTHER] {response.status_code}: {response.text[:200]}")
                    
            except Exception as e:
                print(f"❌ [EXCEPTION] 요청 실패: {e}")
            
            # 다음 요청 전 잠시 대기
            if i < len(test_cases):
                print("⏳ [WAIT] 5초 대기...")
                await asyncio.sleep(5)

async def main():
    await test_final_solution()
    
    print("\n" + "=" * 70)
    print("🎯 [CONCLUSION] 결론:")
    print("1. place_id가 포함된 요청에서 정상적인 추천이 나오면 ✅ 성공")
    print("2. 여전히 AMBIGUOUS가 나오면 ⚠️ 추가 수정 필요")
    print("3. Railway 로그에서 다음 확인:")
    print("   - [PLACE_ID_PROVIDED] 로그")
    print("   - [SKIP_GEOCODING] 로그")
    print("   - [STEP_1_PLAN_A] 로그")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())