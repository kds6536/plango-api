#!/usr/bin/env python3
"""
Railway Geocoding 상세 테스트
"""

import asyncio
import httpx
import json

RAILWAY_BASE_URL = "https://plango-api-production.up.railway.app"

async def test_geocoding_detailed():
    """Railway에서 Geocoding 상세 결과 확인"""
    print("🌍 Railway Geocoding 상세 테스트")
    
    test_cities = ["서울", "부산", "인천"]
    
    url = f"{RAILWAY_BASE_URL}/api/v1/diagnosis/test-specific-api"
    
    for city in test_cities:
        print(f"\n  🏙️ '{city}' Geocoding 테스트")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{url}?api_name=geocoding", 
                    json={"address": city}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    success = data.get("success", False)
                    results_count = data.get("results_count", 0)
                    
                    print(f"    📊 성공: {success}")
                    print(f"    📊 결과 수: {results_count}")
                    
                    if success:
                        sample_result = data.get("sample_result", "N/A")
                        print(f"    📍 첫 번째 결과: {sample_result}")
                        
                        # 상세 결과가 있다면 출력
                        if "detailed_results" in data:
                            detailed = data["detailed_results"]
                            print(f"    📋 상세 결과:")
                            for i, result in enumerate(detailed[:3]):  # 처음 3개만
                                print(f"      {i+1}. {result}")
                                
                        if results_count > 1:
                            print(f"    ⚠️ 여러 결과 - 중복 제거 로직 확인 필요")
                        else:
                            print(f"    ✅ 단일 결과 - 정상")
                    else:
                        error_msg = data.get("error_message", "Unknown")
                        print(f"    ❌ 실패: {error_msg}")
                else:
                    print(f"    ❌ HTTP 에러: {response.status_code}")
                    print(f"    📄 응답: {response.text[:200]}")
                    
        except Exception as e:
            print(f"    💥 예외: {e}")

async def test_place_recommendations_simple():
    """간단한 장소 추천 테스트"""
    print(f"\n🎯 간단한 장소 추천 테스트")
    
    # 인천은 이전에 성공했으므로 다시 테스트
    payload = {
        "city": "인천",
        "country": "대한민국",
        "total_duration": 1,
        "travelers_count": 1,
        "travel_style": "관광",
        "budget_level": "중간"
    }
    
    url = f"{RAILWAY_BASE_URL}/api/v1/place-recommendations/generate"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            print(f"  📤 요청: 인천 (이전에 성공한 도시)")
            
            response = await client.post(url, json=payload)
            
            print(f"  📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                success = data.get("success", False)
                is_fallback = data.get("is_fallback", False)
                
                print(f"  📊 성공: {success}")
                print(f"  📊 폴백: {is_fallback}")
                
                if is_fallback:
                    print(f"  ⚠️ 폴백 처리됨")
                    print(f"  📝 이유: {data.get('fallback_reason')}")
                else:
                    print(f"  🎉 Plan A 성공!")
                    print(f"  📊 추천 수: {data.get('newly_recommended_count')}")
                    
                    # 추천 결과 샘플
                    places = data.get("places", [])
                    if places:
                        print(f"  📍 추천 장소 샘플 (처음 3개):")
                        for i, place in enumerate(places[:3]):
                            print(f"    {i+1}. {place.get('name')} ({place.get('category')})")
                            
            elif response.status_code == 400:
                data = response.json()
                error_code = data.get("error_code")
                
                if error_code == "AMBIGUOUS_LOCATION":
                    print(f"  🎯 동명 지역 감지됨 (예상치 못함)")
                    options = data.get("options", [])
                    print(f"  📍 선택지: {len(options)}개")
                else:
                    print(f"  ❌ 400 에러: {data.get('message')}")
                    
            else:
                print(f"  ❌ 예상치 못한 상태: {response.text[:200]}")
                
    except Exception as e:
        print(f"  💥 예외: {e}")

async def main():
    print("🚀 Railway Geocoding 및 장소 추천 상세 테스트")
    print("=" * 60)
    
    await test_geocoding_detailed()
    await test_place_recommendations_simple()
    
    print("\n" + "=" * 60)
    print("📋 분석:")
    print("1. Geocoding에서 여러 결과가 나오면 중복 제거 로직 미작동")
    print("2. 인천이 성공하면 Plan A 자체는 정상 작동")
    print("3. 서울/부산이 실패하면 중복 제거 로직 문제")

if __name__ == "__main__":
    asyncio.run(main())