#!/usr/bin/env python3
"""
간단한 헬스체크 테스트
"""

import asyncio
import httpx

BASE_URL = "https://plango-api-production.up.railway.app"

async def test_health():
    """헬스체크 테스트"""
    print("🏥 헬스체크 테스트")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{BASE_URL}/api/v1/place-recommendations/health")
            print(f"   상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 헬스체크 성공")
                print(f"   서비스: {data.get('service')}")
                print(f"   Supabase 연결: {data.get('supabase_connected')}")
            else:
                print(f"   ❌ 헬스체크 실패: {response.text}")
                
        except Exception as e:
            print(f"   💥 헬스체크 예외: {e}")

async def test_root():
    """루트 엔드포인트 테스트"""
    print("\n🌐 루트 엔드포인트 테스트")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(BASE_URL)
            print(f"   상태 코드: {response.status_code}")
            print(f"   응답: {response.text[:100]}")
        except Exception as e:
            print(f"   💥 루트 테스트 예외: {e}")

if __name__ == "__main__":
    asyncio.run(test_health())
    asyncio.run(test_root())