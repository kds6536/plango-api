#!/usr/bin/env python3
"""
개별 엔드포인트 직접 테스트
"""

import asyncio
import httpx
import json

RAILWAY_BASE_URL = "https://plango-api-production.up.railway.app"

async def test_email_endpoint():
    """이메일 엔드포인트 직접 테스트"""
    print("📧 이메일 엔드포인트 직접 테스트")
    
    url = f"{RAILWAY_BASE_URL}/api/v1/place-recommendations/test-email-notification"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            print(f"  🌐 URL: {url}")
            response = await client.post(url)
            
            print(f"  📊 Status: {response.status_code}")
            print(f"  📝 Headers: {dict(response.headers)}")
            
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                print(f"  📄 Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            else:
                print(f"  📄 Raw Response: {response.text}")
                
    except Exception as e:
        print(f"  💥 Error: {e}")
        import traceback
        traceback.print_exc()

async def test_ambiguous_endpoint():
    """동명 지역 엔드포인트 직접 테스트"""
    print("\n🌍 동명 지역 엔드포인트 직접 테스트")
    
    url = f"{RAILWAY_BASE_URL}/api/v1/place-recommendations/generate"
    
    payload = {
        "city": "광주",
        "country": "대한민국", 
        "total_duration": 2,
        "travelers_count": 2,
        "travel_style": "관광",
        "budget_level": "중간"
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            print(f"  🌐 URL: {url}")
            print(f"  📤 Payload: {json.dumps(payload, ensure_ascii=False)}")
            
            response = await client.post(url, json=payload)
            
            print(f"  📊 Status: {response.status_code}")
            print(f"  📝 Headers: {dict(response.headers)}")
            
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                print(f"  📄 Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            else:
                print(f"  📄 Raw Response: {response.text}")
                
    except Exception as e:
        print(f"  💥 Error: {e}")
        import traceback
        traceback.print_exc()

async def test_geocoding_specific():
    """Geocoding 특정 테스트"""
    print("\n🧪 Geocoding 특정 테스트")
    
    url = f"{RAILWAY_BASE_URL}/api/v1/diagnosis/test-specific-api"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # 광주 테스트
            response = await client.post(f"{url}?api_name=geocoding", json={"address": "광주, 대한민국"})
            
            print(f"  📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"  📄 Geocoding Result: {json.dumps(data, indent=2, ensure_ascii=False)}")
            else:
                print(f"  📄 Error Response: {response.text}")
                
    except Exception as e:
        print(f"  💥 Error: {e}")

async def main():
    print("🚀 개별 엔드포인트 직접 테스트 시작")
    print("=" * 60)
    
    await test_email_endpoint()
    await test_ambiguous_endpoint() 
    await test_geocoding_specific()

if __name__ == "__main__":
    asyncio.run(main())