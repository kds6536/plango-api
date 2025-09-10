#!/usr/bin/env python3
"""
새로운 동명 지역 감지 로직 테스트
"""

import asyncio
import httpx
import json

RAILWAY_BASE_URL = "https://plango-api-production.up.railway.app"

async def test_korean_cities():
    """한국 도시들 테스트"""
    print("🇰🇷 한국 도시 테스트")
    
    test_cities = [
        {"city": "서울", "expected": "같은 지역 (Plan A 진행)"},
        {"city": "부산", "expected": "같은 지역 (Plan A 진행)"},
        {"city": "광주", "expected": "동명 지역 (선택지 제공)"},
        {"city": "인천", "expected": "같은 지역 (Plan A 진행)"},
    ]
    
    url = f"{RAILWAY_BASE_URL}/api/v1/place-recommendations/generate"
    
    for test_case in test_cities:
        city = test_case["city"]
        expected = test_case["expected"]
        
        print(f"\n  🏙️ '{city}' 테스트 (예상: {expected})")
        
        payload = {
            "city": city,
            "country": "대한민국",
            "total_duration": 1,
            "travelers_count": 1,
            "travel_style": "관광",
            "budget_level": "중간"
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
                
                print(f"    📊 Status Code: {response.status_code}")
                
                if response.status_code == 400:
                    data = response.json()
                    error_code = data.get("error_code")
                    
                    if error_code == "AMBIGUOUS_LOCATION":
                        options = data.get("options", [])
                        print(f"    🎯 동명 지역 감지됨! 선택지 {len(options)}개")
                        
                        for i, option in enumerate(options[:2]):
                            display_name = option.get("display_name", "N/A")
                            print(f"      {i+1}. {display_name}")
                            
                        if "동명 지역" in expected:
                            print(f"    ✅ 예상대로 동명 지역 감지!")
                        else:
                            print(f"    ❌ 예상과 다름: 동명 지역으로 감지됨")
                    else:
                        print(f"    ❌ 다른 400 에러: {data.get('message')}")
                        
                elif response.status_code == 200:
                    data = response.json()
                    is_fallback = data.get("is_fallback", False)
                    
                    if is_fallback:
                        print(f"    ⚠️ 폴백 응답")
                        print(f"    📝 이유: {data.get('fallback_reason')}")
                        
                        if "Plan A 진행" in expected:
                            print(f"    ❌ 예상과 다름: Plan A 실패로 폴백")
                        else:
                            print(f"    ⚠️ 예상치 못한 폴백")
                    else:
                        print(f"    🎉 Plan A 성공!")
                        print(f"    📊 추천 수: {data.get('newly_recommended_count')}")
                        
                        if "Plan A 진행" in expected:
                            print(f"    ✅ 예상대로 Plan A 성공!")
                        else:
                            print(f"    ❌ 예상과 다름: Plan A로 진행됨")
                            
                else:
                    print(f"    ❌ 예상치 못한 상태: {response.status_code}")
                    
        except Exception as e:
            print(f"    💥 예외: {e}")

async def test_international_cities():
    """해외 도시들 테스트"""
    print(f"\n🌍 해외 도시 테스트")
    
    test_cities = [
        {"city": "Paris", "country": "France", "expected": "같은 지역 또는 동명 지역"},
        {"city": "Springfield", "country": "USA", "expected": "동명 지역 (여러 주에 존재)"},
        {"city": "Cambridge", "country": "UK", "expected": "동명 지역 (UK vs USA)"},
    ]
    
    url = f"{RAILWAY_BASE_URL}/api/v1/place-recommendations/generate"
    
    for test_case in test_cities:
        city = test_case["city"]
        country = test_case["country"]
        expected = test_case["expected"]
        
        print(f"\n  🏙️ '{city}, {country}' 테스트 (예상: {expected})")
        
        payload = {
            "city": city,
            "country": country,
            "total_duration": 1,
            "travelers_count": 1,
            "travel_style": "관광",
            "budget_level": "중간"
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
                
                print(f"    📊 Status Code: {response.status_code}")
                
                if response.status_code == 400:
                    data = response.json()
                    error_code = data.get("error_code")
                    
                    if error_code == "AMBIGUOUS_LOCATION":
                        options = data.get("options", [])
                        print(f"    🎯 동명 지역 감지됨! 선택지 {len(options)}개")
                        
                        for i, option in enumerate(options[:2]):
                            display_name = option.get("display_name", "N/A")
                            print(f"      {i+1}. {display_name}")
                    else:
                        print(f"    ❌ 다른 400 에러: {data.get('message')}")
                        
                elif response.status_code == 200:
                    data = response.json()
                    is_fallback = data.get("is_fallback", False)
                    
                    if is_fallback:
                        print(f"    ⚠️ 폴백 응답")
                    else:
                        print(f"    🎉 Plan A 성공!")
                        print(f"    📊 추천 수: {data.get('newly_recommended_count')}")
                        
                else:
                    print(f"    ❌ 예상치 못한 상태: {response.status_code}")
                    
        except Exception as e:
            print(f"    💥 예외: {e}")

async def main():
    print("🚀 새로운 동명 지역 감지 로직 테스트")
    print("=" * 60)
    print("📋 테스트 목표:")
    print("1. 서울/부산: 같은 지역으로 인식 → Plan A 진행")
    print("2. 광주: 동명 지역으로 인식 → 선택지 제공")
    print("3. 해외 도시: 패턴에 따라 적절히 처리")
    print("=" * 60)
    
    await test_korean_cities()
    await test_international_cities()
    
    print("\n" + "=" * 60)
    print("📊 결과 분석:")
    print("✅ 성공: 예상대로 작동")
    print("❌ 실패: 예상과 다른 결과")
    print("⚠️ 폴백: Plan A 실패 (별도 문제)")

if __name__ == "__main__":
    asyncio.run(main())