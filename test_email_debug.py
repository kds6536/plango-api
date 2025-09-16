#!/usr/bin/env python3
"""
이메일 서비스 디버깅 테스트
"""

import asyncio
import httpx
from datetime import datetime

# Railway 배포된 API URL
API_BASE_URL = "https://plango-api-production.up.railway.app"

async def test_email_service():
    """이메일 서비스 테스트"""
    
    print("📧 [EMAIL_TEST] 이메일 서비스 테스트 시작")
    print(f"🌐 [API_URL] {API_BASE_URL}")
    print(f"⏰ [TIME] {datetime.now().isoformat()}")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            print("🧪 [TEST_1] 이메일 알림 테스트 엔드포인트 호출...")
            
            response = await client.post(
                f"{API_BASE_URL}/api/v1/place-recommendations/test-email-notification"
            )
            
            print(f"📊 [RESPONSE] 상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ [SUCCESS] 이메일 테스트 성공!")
                print(f"📝 [RESULT] {data}")
            else:
                print(f"❌ [FAIL] 이메일 테스트 실패")
                print(f"📝 [ERROR] {response.text}")
                
        except Exception as e:
            print(f"❌ [ERROR] 테스트 실패: {e}")
    
    print("\n" + "=" * 60)
    print("🧪 [TEST_2] 실제 에러 발생시켜서 이메일 발송 테스트...")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # 존재하지 않는 도시로 에러 발생
            response = await client.post(
                f"{API_BASE_URL}/api/v1/place-recommendations/generate",
                json={
                    "city": "존재하지않는도시999",
                    "country": "존재하지않는국가999",
                    "total_duration": 2,
                    "travelers_count": 2,
                    "travel_style": ["관광"],
                    "budget_level": "중간"
                }
            )
            
            print(f"📊 [ERROR_RESPONSE] 상태 코드: {response.status_code}")
            
            if response.status_code == 400:
                print("✅ [EXPECTED_ERROR] 예상된 400 에러 발생")
                print("📧 [EMAIL_CHECK] Railway 로그에서 이메일 발송 로그 확인 필요")
            else:
                print(f"❌ [UNEXPECTED] 예상과 다른 응답: {response.status_code}")
                
        except Exception as e:
            print(f"❌ [ERROR] 에러 테스트 실패: {e}")

async def main():
    await test_email_service()

if __name__ == "__main__":
    asyncio.run(main())