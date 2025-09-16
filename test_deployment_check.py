#!/usr/bin/env python3
"""
배포 상태 확인 테스트
"""

import asyncio
import httpx
from datetime import datetime

# Railway 배포된 API URL
API_BASE_URL = "https://plango-api-production.up.railway.app"

async def check_deployment():
    """배포 상태 확인"""
    
    print("🔍 [DEPLOYMENT_CHECK] 배포 상태 확인")
    print(f"🌐 [API_URL] {API_BASE_URL}")
    print(f"⏰ [TIME] {datetime.now().isoformat()}")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. 헬스체크
        try:
            print("\n🏥 [HEALTH_CHECK] 헬스체크 확인...")
            response = await client.get(f"{API_BASE_URL}/health")
            print(f"📊 [HEALTH] 상태 코드: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"📝 [HEALTH] 응답: {data}")
            else:
                print(f"❌ [HEALTH] 실패: {response.text}")
        except Exception as e:
            print(f"❌ [HEALTH] 에러: {e}")
        
        # 2. Place Recommendations 헬스체크
        try:
            print("\n🏥 [PLACE_HEALTH] Place Recommendations 헬스체크...")
            response = await client.get(f"{API_BASE_URL}/api/v1/place-recommendations/health")
            print(f"📊 [PLACE_HEALTH] 상태 코드: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"📝 [PLACE_HEALTH] 서비스: {data.get('service', 'Unknown')}")
                print(f"📝 [PLACE_HEALTH] 상태: {data.get('status', 'Unknown')}")
                print(f"📝 [PLACE_HEALTH] Supabase: {data.get('supabase_connected', 'Unknown')}")
            else:
                print(f"❌ [PLACE_HEALTH] 실패: {response.text}")
        except Exception as e:
            print(f"❌ [PLACE_HEALTH] 에러: {e}")
        
        # 3. 테스트 엔드포인트로 코드 버전 확인
        try:
            print("\n🧪 [VERSION_CHECK] 테스트 엔드포인트로 코드 버전 확인...")
            response = await client.post(f"{API_BASE_URL}/api/v1/place-recommendations/test-ambiguous-location")
            print(f"📊 [VERSION] 상태 코드: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"📝 [VERSION] 테스트 성공: {data}")
            else:
                print(f"📝 [VERSION] 응답: {response.text[:200]}")
        except Exception as e:
            print(f"❌ [VERSION] 에러: {e}")
        
        # 4. 간단한 추천 요청으로 실제 코드 경로 확인
        try:
            print("\n🧪 [CODE_PATH] 실제 코드 경로 확인 (존재하지 않는 도시)...")
            response = await client.post(
                f"{API_BASE_URL}/api/v1/place-recommendations/generate",
                json={
                    "city": "TestCity999",
                    "country": "TestCountry999",
                    "total_duration": 1,
                    "travelers_count": 1,
                    "travel_style": ["관광"],
                    "budget_level": "중간"
                }
            )
            print(f"📊 [CODE_PATH] 상태 코드: {response.status_code}")
            print(f"📝 [CODE_PATH] 응답: {response.text[:300]}")
            
            # 응답에서 우리가 추가한 메시지가 있는지 확인
            if "STEP_1_GEOCODING" in response.text:
                print("✅ [CODE_PATH] 새로운 코드가 실행되고 있습니다!")
            else:
                print("⚠️ [CODE_PATH] 기존 코드가 실행되고 있을 수 있습니다.")
                
        except Exception as e:
            print(f"❌ [CODE_PATH] 에러: {e}")

async def main():
    await check_deployment()

if __name__ == "__main__":
    asyncio.run(main())