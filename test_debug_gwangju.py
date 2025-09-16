#!/usr/bin/env python3
"""
광주 디버깅 테스트 - Railway 로그 실시간 확인용
"""

import asyncio
import httpx
from datetime import datetime

# Railway 배포된 API URL
API_BASE_URL = "https://plango-api-production.up.railway.app"

async def test_debug_gwangju():
    """광주 디버깅 테스트"""
    
    print("🔍 [DEBUG_GWANGJU] 광주 디버깅 테스트")
    print(f"🌐 [API_URL] {API_BASE_URL}")
    print(f"⏰ [START_TIME] {datetime.now().isoformat()}")
    print("=" * 70)
    
    print("\n📋 [INSTRUCTIONS] Railway 로그 확인 준비:")
    print("1. Railway 대시보드에서 plango-api 프로젝트 열기")
    print("2. Logs 탭 클릭")
    print("3. 실시간 로그 모니터링 시작")
    print("4. 아래 테스트 실행 시 로그에서 다음 패턴 확인:")
    print("   - 🚀 [START] 추천 생성 API 시작")
    print("   - 📍 [STEP_1_GEOCODING] Geocoding 시작...")
    print("   - 🔍 [AMBIGUOUS_CHECK] 동명 지역 감지 시작...")
    print("   - 🔍 [AMBIGUOUS_RESULT] is_ambiguous_location 결과")
    
    input("\n⏳ Railway 로그 준비가 완료되면 Enter를 눌러주세요...")
    
    print("\n🚀 [TEST_START] 광주 테스트 시작!")
    print("⏰ [TIMESTAMP] 이 시각을 기준으로 Railway 로그를 확인하세요:")
    print(f"   {datetime.now().isoformat()}")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            print("\n📤 [REQUEST] 광주 요청 발송 중...")
            
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
            print(f"⏰ [RESPONSE_TIME] {datetime.now().isoformat()}")
            
            if response.status_code == 400:
                data = response.json()
                error_code = data.get("error_code", "UNKNOWN")
                print(f"📝 [ERROR_CODE] {error_code}")
                
                if error_code == "AMBIGUOUS_LOCATION":
                    options = data.get("options", [])
                    print(f"✅ [SUCCESS] 동명 지역 감지! 선택지 {len(options)}개")
                else:
                    print(f"📝 [ERROR_DETAIL] {data.get('detail', 'Unknown error')}")
                    
            elif response.status_code == 200:
                data = response.json()
                print(f"📝 [SUCCESS] 200 응답 수신")
                print(f"   - 신규 추천: {data.get('newly_recommended_count', 0)}개")
                print(f"   - 기존 추천: {data.get('previously_recommended_count', 0)}개")
                print(f"   - 도시 ID: {data.get('city_id', 'Unknown')}")
                print(f"   - 도시명: {data.get('city_name', 'Unknown')}")
                print(f"   - 메인 테마: {data.get('main_theme', 'Unknown')}")
                
            else:
                print(f"📝 [OTHER] {response.text[:300]}")
                
        except Exception as e:
            print(f"❌ [ERROR] 요청 실패: {e}")
    
    print("\n" + "=" * 70)
    print("🔍 [LOG_CHECK] 이제 Railway 로그에서 다음을 확인하세요:")
    print("1. [START] 로그가 나타났는가?")
    print("2. [STEP_1_GEOCODING] 로그가 나타났는가?")
    print("3. [AMBIGUOUS_CHECK] 로그가 나타났는가?")
    print("4. [AMBIGUOUS_RESULT] 결과가 true인가 false인가?")
    print("5. 만약 위 로그들이 없다면, 다른 코드 경로가 실행되고 있는 것")
    print("=" * 70)

async def main():
    await test_debug_gwangju()

if __name__ == "__main__":
    asyncio.run(main())