#!/usr/bin/env python3
"""
간단한 서울 테스트
"""

import asyncio
import httpx
import json

RAILWAY_BASE_URL = "https://plango-api-production.up.railway.app"

async def simple_seoul_test():
    """간단한 서울 테스트"""
    print("🏙️ 간단한 서울 테스트")
    
    payload = {
        "city": "서울",
        "country": "대한민국",
        "total_duration": 1,
        "travelers_count": 1,
        "travel_style": "관광",
        "budget_level": "중간"
    }
    
    url = f"{RAILWAY_BASE_URL}/api/v1/place-recommendations/generate"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"  📤 요청 전송 중...")
            
            response = await client.post(url, json=payload)
            
            print(f"  📊 Status Code: {response.status_code}")
            print(f"  📄 Content-Type: {response.headers.get('content-type', 'N/A')}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    success = data.get("success", False)
                    is_fallback = data.get("is_fallback", False)
                    
                    print(f"  📊 성공: {success}")
                    print(f"  📊 폴백: {is_fallback}")
                    
                    if is_fallback:
                        print(f"  ⚠️ 폴백 이유: {data.get('fallback_reason', 'N/A')}")
                    else:
                        print(f"  🎉 Plan A 성공!")
                        print(f"  📊 추천 수: {data.get('newly_recommended_count', 0)}")
                        
                except json.JSONDecodeError as e:
                    print(f"  ❌ JSON 파싱 실패: {e}")
                    print(f"  📄 Raw Response: {response.text[:200]}")
                    
            elif response.status_code == 400:
                try:
                    data = response.json()
                    error_code = data.get("error_code")
                    
                    if error_code == "AMBIGUOUS_LOCATION":
                        print(f"  🎯 동명 지역 감지됨")
                        options = data.get("options", [])
                        print(f"  📍 선택지 수: {len(options)}")
                    else:
                        print(f"  ❌ 400 에러: {data.get('message', 'N/A')}")
                        
                except json.JSONDecodeError as e:
                    print(f"  ❌ JSON 파싱 실패: {e}")
                    print(f"  📄 Raw Response: {response.text[:200]}")
                    
            elif response.status_code == 500:
                print(f"  💥 서버 에러")
                print(f"  📄 Raw Response: {response.text[:200]}")
                
            else:
                print(f"  ❓ 예상치 못한 상태 코드")
                print(f"  📄 Raw Response: {response.text[:200]}")
                
    except asyncio.TimeoutError:
        print(f"  ⏰ 타임아웃 (30초)")
    except Exception as e:
        print(f"  💥 예외: {type(e).__name__}: {e}")

async def main():
    print("🚀 간단한 서울 테스트")
    print("=" * 40)
    
    await simple_seoul_test()
    
    print("\n" + "=" * 40)
    print("📋 결과 확인")

if __name__ == "__main__":
    asyncio.run(main())