#!/usr/bin/env python3
"""
동명 지역 선택지 상세 확인
"""

import asyncio
import httpx
import json

RAILWAY_BASE_URL = "https://plango-api-production.up.railway.app"

async def test_ambiguous_options():
    """동명 지역 선택지 상세 확인"""
    print("🎯 동명 지역 선택지 상세 확인")
    
    test_cities = ["서울", "부산", "광주", "대구", "인천"]
    
    url = f"{RAILWAY_BASE_URL}/api/v1/place-recommendations/generate"
    
    for city in test_cities:
        print(f"\n  🏙️ '{city}' 테스트")
        
        payload = {
            "city": city,
            "country": "대한민국",
            "total_duration": 2,
            "travelers_count": 2,
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
                        print(f"    🎯 동명 지역 감지!")
                        print(f"    📝 메시지: {data.get('message')}")
                        
                        options = data.get("options", [])
                        print(f"    📍 선택지 ({len(options)}개):")
                        
                        for i, option in enumerate(options):
                            display_name = option.get("display_name", "N/A")
                            place_id = option.get("place_id", "N/A")
                            print(f"      {i+1}. {display_name}")
                            print(f"         Place ID: {place_id[:20]}...")
                            
                    else:
                        print(f"    ❌ 다른 400 에러: {data}")
                        
                elif response.status_code == 200:
                    data = response.json()
                    is_fallback = data.get("is_fallback", False)
                    
                    if is_fallback:
                        print(f"    ⚠️ 폴백 응답")
                        print(f"    📝 이유: {data.get('fallback_reason')}")
                    else:
                        print(f"    ✅ 정상 Plan A 응답")
                        print(f"    📊 추천 수: {data.get('newly_recommended_count')}")
                        
                else:
                    print(f"    ❌ 예상치 못한 상태: {response.status_code}")
                    print(f"    📄 응답: {response.text[:200]}")
                    
        except Exception as e:
            print(f"    💥 예외: {e}")

async def test_specific_place_id():
    """특정 place_id로 테스트 (동명 지역 해결 후)"""
    print(f"\n🎯 특정 place_id로 테스트")
    
    # 서울의 대표적인 place_id (Google Places API에서 가져온 것)
    seoul_place_id = "ChIJzWVBSgSifDUR64Pq5LTtioU"  # 서울특별시
    
    payload = {
        "city": "서울",
        "country": "대한민국", 
        "place_id": seoul_place_id,  # place_id 직접 제공
        "total_duration": 2,
        "travelers_count": 2,
        "travel_style": "관광",
        "budget_level": "중간"
    }
    
    url = f"{RAILWAY_BASE_URL}/api/v1/place-recommendations/generate"
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            print(f"  📤 요청: place_id 포함")
            print(f"  🆔 Place ID: {seoul_place_id}")
            
            response = await client.post(url, json=payload)
            
            print(f"  📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                success = data.get("success", False)
                is_fallback = data.get("is_fallback", False)
                
                print(f"  📊 성공: {success}")
                print(f"  📊 폴백: {is_fallback}")
                
                if is_fallback:
                    print(f"  ⚠️ 여전히 폴백으로 처리됨")
                    print(f"  📝 폴백 이유: {data.get('fallback_reason')}")
                    print(f"  💡 place_id를 제공해도 Plan A가 실패함")
                else:
                    print(f"  🎉 Plan A 성공!")
                    print(f"  📊 추천 수: {data.get('newly_recommended_count')}")
                    print(f"  🏙️ 도시: {data.get('city_name')}")
                    
                    # 추천 결과 샘플
                    places = data.get("places", [])
                    if places:
                        print(f"  📍 추천 장소 샘플:")
                        for i, place in enumerate(places[:3]):
                            print(f"    {i+1}. {place.get('name')} ({place.get('category')})")
                            
            elif response.status_code == 400:
                data = response.json()
                print(f"  ❌ 400 에러: {data.get('message')}")
                
            else:
                print(f"  ❌ 예상치 못한 상태: {response.text[:200]}")
                
    except asyncio.TimeoutError:
        print(f"  ⏰ 타임아웃 - Plan A 처리가 120초를 초과함")
    except Exception as e:
        print(f"  💥 예외: {e}")

async def main():
    print("🚀 동명 지역 선택지 및 Plan A 테스트")
    print("=" * 60)
    
    await test_ambiguous_options()
    await test_specific_place_id()
    
    print("\n" + "=" * 60)
    print("📋 결론:")
    print("1. 동명 지역 감지가 작동하고 있음 (400 에러)")
    print("2. place_id를 제공하면 동명 지역 문제 해결")
    print("3. place_id 제공 후에도 폴백이면 Plan A 자체에 문제")
    print("4. Plan A 성공하면 모든 시스템이 정상 작동")

if __name__ == "__main__":
    asyncio.run(main())