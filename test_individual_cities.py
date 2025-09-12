#!/usr/bin/env python3
"""
개별 도시 테스트
"""

import asyncio
import httpx
import json

RAILWAY_BASE_URL = "https://plango-api-production.up.railway.app"

async def test_single_city(city, country="대한민국"):
    """단일 도시 테스트"""
    print(f"\n🏙️ '{city}' 테스트")
    
    payload = {
        "city": city,
        "country": country,
        "total_duration": 1,
        "travelers_count": 1,
        "travel_style": "관광",
        "budget_level": "중간"
    }
    
    url = f"{RAILWAY_BASE_URL}/api/v1/place-recommendations/generate"
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            
            print(f"  📊 Status: {response.status_code}")
            
            if response.status_code == 400:
                data = response.json()
                error_code = data.get("error_code")
                
                if error_code == "AMBIGUOUS_LOCATION":
                    options = data.get("options", [])
                    print(f"  🎯 동명 지역 감지! 선택지 {len(options)}개")
                    
                    for i, option in enumerate(options[:2]):
                        display_name = option.get("display_name", "N/A")
                        print(f"    {i+1}. {display_name}")
                        
                    return "AMBIGUOUS"
                else:
                    print(f"  ❌ 400 에러: {data.get('message', 'N/A')}")
                    return "ERROR"
                    
            elif response.status_code == 200:
                data = response.json()
                is_fallback = data.get("is_fallback", False)
                
                if is_fallback:
                    print(f"  ⚠️ 폴백 응답")
                    return "FALLBACK"
                else:
                    print(f"  🎉 Plan A 성공!")
                    count = data.get("newly_recommended_count", 0)
                    print(f"  📊 추천 수: {count}")
                    return "SUCCESS"
                    
            else:
                print(f"  ❌ 예상치 못한 상태: {response.status_code}")
                return "ERROR"
                
    except Exception as e:
        print(f"  💥 예외: {type(e).__name__}: {str(e)[:100]}")
        return "EXCEPTION"

async def main():
    print("🚀 개별 도시 테스트")
    print("=" * 50)
    
    # 한국 도시들
    korean_cities = ["서울", "부산", "광주", "인천", "대구"]
    
    results = {}
    
    for city in korean_cities:
        result = await test_single_city(city)
        results[city] = result
        
        # 각 테스트 사이에 잠시 대기
        await asyncio.sleep(2)
    
    print("\n" + "=" * 50)
    print("📊 결과 요약:")
    
    for city, result in results.items():
        status_emoji = {
            "SUCCESS": "🎉",
            "FALLBACK": "⚠️", 
            "AMBIGUOUS": "🎯",
            "ERROR": "❌",
            "EXCEPTION": "💥"
        }.get(result, "❓")
        
        print(f"  {status_emoji} {city}: {result}")
    
    print("\n📋 분석:")
    print("🎉 SUCCESS: Plan A 성공 (새 로직으로 같은 지역 인식)")
    print("🎯 AMBIGUOUS: 동명 지역 감지 (새 로직 작동)")
    print("⚠️ FALLBACK: Plan A 실패 (별도 문제)")
    print("❌ ERROR: API 에러")
    print("💥 EXCEPTION: 네트워크 또는 코드 문제")

if __name__ == "__main__":
    asyncio.run(main())