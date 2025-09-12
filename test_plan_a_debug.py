#!/usr/bin/env python3
"""
Plan A 디버깅용 간단 테스트
Railway 환경에서만 실행 가능
"""

import asyncio
import httpx
import traceback

# Railway 배포 URL
BASE_URL = "https://plango-api-production.up.railway.app"

async def simple_test():
    """간단한 연결 테스트"""
    print("🔍 Railway API 연결 테스트 시작")
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5분 타임아웃
            # 1. 헬스체크 먼저
            print("\n1️⃣ 헬스체크 테스트")
            try:
                response = await client.get(f"{BASE_URL}/api/v1/place-recommendations/health")
                print(f"   헬스체크 상태: {response.status_code}")
                if response.status_code == 200:
                    print(f"   응답: {response.json()}")
                else:
                    print(f"   에러: {response.text}")
            except Exception as e:
                print(f"   헬스체크 실패: {e}")
                print(f"   상세: {traceback.format_exc()}")
            
            # 2. 간단한 추천 요청
            print("\n2️⃣ 간단한 추천 요청 (서울)")
            try:
                request_data = {
                    "city": "서울",
                    "country": "대한민국",
                    "total_duration": 2,
                    "travelers_count": 1,
                    "travel_style": "관광",
                    "budget_level": "중간"
                }
                
                response = await client.post(
                    f"{BASE_URL}/api/v1/place-recommendations/generate",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                print(f"   상태 코드: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ 성공: {data.get('newly_recommended_count', 0)}개 추천")
                    print(f"   폴백 여부: {data.get('is_fallback', False)}")
                    print(f"   상태: {data.get('status', 'N/A')}")
                else:
                    print(f"   ❌ 실패 응답: {response.text}")
                    
            except Exception as e:
                print(f"   추천 요청 실패: {e}")
                print(f"   상세: {traceback.format_exc()}")
            
            # 3. 동명 지역 테스트 (광주)
            print("\n3️⃣ 동명 지역 테스트 (광주)")
            try:
                request_data = {
                    "city": "광주",
                    "country": "대한민국",
                    "total_duration": 2,
                    "travelers_count": 1,
                    "travel_style": "관광",
                    "budget_level": "중간"
                }
                
                response = await client.post(
                    f"{BASE_URL}/api/v1/place-recommendations/generate",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                print(f"   상태 코드: {response.status_code}")
                
                if response.status_code == 400:
                    data = response.json()
                    print(f"   ✅ 동명 지역 감지!")
                    print(f"   에러 코드: {data.get('error_code')}")
                    print(f"   메시지: {data.get('message')}")
                    print(f"   선택지: {len(data.get('options', []))}개")
                elif response.status_code == 200:
                    data = response.json()
                    print(f"   ⚠️ 200 응답 (동명 지역 감지 안됨)")
                    print(f"   폴백 여부: {data.get('is_fallback', False)}")
                else:
                    print(f"   ❌ 예상치 못한 응답: {response.text}")
                    
            except Exception as e:
                print(f"   동명 지역 테스트 실패: {e}")
                print(f"   상세: {traceback.format_exc()}")
                
    except Exception as e:
        print(f"❌ 전체 테스트 실패: {e}")
        print(f"상세: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(simple_test())