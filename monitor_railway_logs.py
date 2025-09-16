#!/usr/bin/env python3
"""
Railway 로그 모니터링 스크립트
통합 솔루션 적용 후 로그 패턴 확인
"""

import asyncio
import httpx
import time
from datetime import datetime

# Railway 배포된 API URL
API_BASE_URL = "https://plango-api-production.up.railway.app"

def print_log_expectations():
    """예상되는 로그 패턴 출력"""
    print("🔍 [EXPECTED_LOGS] 통합 솔루션 적용 후 예상되는 로그 패턴:")
    print("=" * 70)
    print("1. 광주 테스트 시:")
    print("   📍 [STEP_1_GEOCODING] Geocoding 시작...")
    print("   🌍 [GEOCODING_QUERY] 검색 쿼리: '광주, 대한민국'")
    print("   📊 [GEOCODING_RESULTS] 결과 X개 발견")
    print("   ⚠️ [AMBIGUOUS_LOCATION] 동명 지역 감지: X개")
    print("   → 400 응답 반환 (Plan A 실행 안됨)")
    print()
    print("2. 서울 테스트 시:")
    print("   📍 [STEP_1_GEOCODING] Geocoding 시작...")
    print("   ✅ [GEOCODING_SUCCESS] 위치 표준화 성공")
    print("   🤖 [STEP_2_PLAN_A] Plan A 추천 생성 시작...")
    print("   🔍 [PLACES_API_START] Google Places 검색 시작")
    print("   → 성공 또는 실패 (하지만 Geocoding은 먼저 실행됨)")
    print()
    print("3. 존재하지 않는 도시 테스트 시:")
    print("   📍 [STEP_1_GEOCODING] Geocoding 시작...")
    print("   ❌ [GEOCODING_FAIL] 위치를 찾을 수 없습니다")
    print("   → 400 응답 반환 (Plan A 실행 안됨)")
    print("=" * 70)

async def trigger_test_requests():
    """테스트 요청들을 순차적으로 발송하여 로그 생성"""
    print("\n🚀 [TRIGGER] 테스트 요청 발송 시작")
    
    test_cases = [
        {
            "name": "광주 (동명 지역)",
            "data": {
                "city": "광주",
                "country": "대한민국",
                "total_duration": 2,
                "travelers_count": 2,
                "travel_style": ["관광"],
                "budget_level": "중간"
            }
        },
        {
            "name": "서울 (명확한 도시)",
            "data": {
                "city": "서울",
                "country": "대한민국",
                "total_duration": 3,
                "travelers_count": 2,
                "travel_style": ["관광"],
                "budget_level": "중간"
            }
        },
        {
            "name": "존재하지 않는 도시",
            "data": {
                "city": "존재하지않는도시12345",
                "country": "존재하지않는국가12345",
                "total_duration": 2,
                "travelers_count": 2,
                "travel_style": ["관광"],
                "budget_level": "중간"
            }
        }
    ]
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📤 [REQUEST_{i}] {test_case['name']} 요청 발송...")
            print(f"⏰ [TIME] {datetime.now().isoformat()}")
            
            try:
                response = await client.post(
                    f"{API_BASE_URL}/api/v1/place-recommendations/generate",
                    json=test_case['data']
                )
                
                print(f"📊 [RESPONSE_{i}] 상태: {response.status_code}")
                
                if response.status_code == 400:
                    data = response.json()
                    error_code = data.get('error_code', 'UNKNOWN')
                    print(f"📝 [ERROR_CODE_{i}] {error_code}")
                elif response.status_code == 200:
                    data = response.json()
                    new_count = data.get('newly_recommended_count', 0)
                    print(f"📝 [SUCCESS_{i}] 신규 추천: {new_count}개")
                else:
                    print(f"📝 [OTHER_{i}] {response.text[:200]}")
                    
            except Exception as e:
                print(f"❌ [ERROR_{i}] 요청 실패: {e}")
            
            # 다음 요청 전 잠시 대기
            if i < len(test_cases):
                print("⏳ [WAIT] 5초 대기...")
                await asyncio.sleep(5)

def print_railway_log_instructions():
    """Railway 로그 확인 방법 안내"""
    print("\n" + "=" * 70)
    print("📋 [INSTRUCTIONS] Railway 로그 확인 방법")
    print("=" * 70)
    print("1. Railway 대시보드 접속:")
    print("   https://railway.app/dashboard")
    print()
    print("2. plango-api 프로젝트 선택")
    print()
    print("3. 'Logs' 탭 클릭")
    print()
    print("4. 실시간 로그에서 다음 패턴들을 확인:")
    print("   - [STEP_1_GEOCODING] : Geocoding이 먼저 실행되는지")
    print("   - [AMBIGUOUS_LOCATION] : 광주에서 동명 지역 감지되는지")
    print("   - [STEP_2_PLAN_A] : Plan A가 Geocoding 이후에 실행되는지")
    print("   - [PLACES_API_START] : Google Places API 호출 로그")
    print("   - [EMAIL_START] : 이메일 발송 로그 (실패 시)")
    print()
    print("5. 중요한 확인 사항:")
    print("   ✅ Geocoding이 Plan A보다 먼저 실행되는가?")
    print("   ✅ 광주 요청 시 AMBIGUOUS_LOCATION 응답이 나오는가?")
    print("   ✅ Plan A 실패 시 이메일이 1번만 발송되는가?")
    print("   ✅ Google Places API 호출 상세 로그가 나오는가?")
    print("=" * 70)

async def main():
    """메인 실행 함수"""
    print("🔍 [MONITOR] Railway 로그 모니터링 도구")
    print(f"🌐 [API_URL] {API_BASE_URL}")
    print(f"⏰ [START_TIME] {datetime.now().isoformat()}")
    
    # 예상 로그 패턴 출력
    print_log_expectations()
    
    # Railway 로그 확인 방법 안내
    print_railway_log_instructions()
    
    # 사용자 확인
    print("\n❓ [QUESTION] Railway 로그 탭을 열어두셨나요? (y/n): ", end="")
    user_input = input().strip().lower()
    
    if user_input != 'y':
        print("📋 [INFO] Railway 로그 탭을 먼저 열어주세요.")
        print("🔗 [LINK] https://railway.app/dashboard")
        return
    
    print("\n⏳ [COUNTDOWN] 5초 후 테스트 요청을 시작합니다...")
    for i in range(5, 0, -1):
        print(f"   {i}...")
        await asyncio.sleep(1)
    
    # 테스트 요청 발송
    await trigger_test_requests()
    
    print("\n" + "=" * 70)
    print("✅ [COMPLETE] 모든 테스트 요청이 완료되었습니다!")
    print("🔍 [ACTION] 이제 Railway 로그에서 다음을 확인해주세요:")
    print("   1. Geocoding이 먼저 실행되었는지")
    print("   2. 광주에서 동명 지역이 감지되었는지")
    print("   3. Plan A 실행 순서가 올바른지")
    print("   4. Google Places API 상세 로그가 나오는지")
    print("   5. 에러 시 이메일이 중복 발송되지 않는지")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())