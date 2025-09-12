#!/usr/bin/env python3
"""
광주 동명 지역 감지 테스트
"""

import asyncio
import httpx
import json

RAILWAY_BASE_URL = "https://plango-api-production.up.railway.app"

async def test_gwangju_ambiguous():
    """광주 동명 지역 테스트"""
    print("🏙️ 광주 동명 지역 테스트")
    
    payload = {
        "city": "광주",
        "country": "대한민국",
        "total_duration": 1,
        "travelers_count": 1,
        "travel_style": "관광",
        "budget_level": "중간"
    }
    
    url = f"{RAILWAY_BASE_URL}/api/v1/place-recommendations/generate"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            print(f"  📤 광주 요청 전송 중...")
            
            response = await client.post(url, json=payload)
            
            print(f"  📊 Status Code: {response.status_code}")
            print(f"  📄 Content-Type: {response.headers.get('content-type', 'N/A')}")
            
            if response.status_code == 400:
                data = response.json()
                error_code = data.get("error_code")
                
                if error_code == "AMBIGUOUS_LOCATION":
                    print(f"  🎯 동명 지역 감지 성공!")
                    options = data.get("options", [])
                    print(f"  📍 선택지 수: {len(options)}")
                    
                    for i, option in enumerate(options):
                        display_name = option.get("display_name", "N/A")
                        formatted_address = option.get("formatted_address", "N/A")
                        print(f"    {i+1}. {display_name}")
                        print(f"       주소: {formatted_address}")
                        
                    print(f"  ✅ 폴백에서 동명 지역 감지 로직이 정상 작동!")
                else:
                    print(f"  ❌ 다른 400 에러: {data}")
                    
            elif response.status_code == 200:
                data = response.json()
                is_fallback = data.get("is_fallback", False)
                
                if is_fallback:
                    print(f"  ⚠️ 폴백 응답으로 처리됨")
                    print(f"  📝 이유: {data.get('fallback_reason')}")
                    print(f"  💡 동명 지역 감지 로직이 작동하지 않았거나 예외 발생")
                else:
                    print(f"  🎉 정상 Plan A 응답 (예상치 못함)")
                    
            else:
                print(f"  ❌ 예상치 못한 상태 코드")
                print(f"  📄 응답: {response.text[:200]}")
                
    except Exception as e:
        print(f"  💥 예외: {type(e).__name__}: {e}")

async def test_geocoding_direct():
    """Geocoding API 직접 테스트"""
    print(f"\n🔍 Geocoding API 직접 테스트")
    
    url = f"{RAILWAY_BASE_URL}/api/v1/diagnosis/test-specific-api"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{url}?api_name=geocoding", 
                json={"address": "광주, 대한민국"}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                success = data.get("success", False)
                results_count = data.get("results_count", 0)
                
                print(f"  📊 성공: {success}")
                print(f"  📊 결과 수: {results_count}")
                
                if success:
                    sample_result = data.get("sample_result", "N/A")
                    print(f"  📍 첫 번째 결과: {sample_result}")
                    
                    if results_count > 1:
                        print(f"  🎯 여러 결과 감지 - 동명 지역 가능성!")
                    else:
                        print(f"  ✅ 단일 결과 - Google이 자동 필터링")
                else:
                    error_msg = data.get("error_message", "Unknown")
                    print(f"  ❌ 실패: {error_msg}")
            else:
                print(f"  ❌ HTTP 에러: {response.status_code}")
                
    except Exception as e:
        print(f"  💥 예외: {e}")

async def main():
    print("🚀 광주 동명 지역 감지 테스트")
    print("=" * 50)
    print("📋 목표: 광주 입력 시 동명 지역 선택지가 나와야 함")
    print("- 광주광역시")
    print("- 경기도 광주시")
    print("=" * 50)
    
    await test_geocoding_direct()
    await test_gwangju_ambiguous()
    
    print("\n" + "=" * 50)
    print("📊 결과:")
    print("✅ 400 에러 + AMBIGUOUS_LOCATION: 동명 지역 감지 성공")
    print("⚠️ 200 응답 + 폴백: 동명 지역 감지 실패")

if __name__ == "__main__":
    asyncio.run(main())