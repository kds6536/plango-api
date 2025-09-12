#!/usr/bin/env python3
"""
Geocoding API 기반 동명 지역 감지 테스트
Railway 환경에서만 실행 가능
"""

import asyncio
import httpx
import json

BASE_URL = "https://plango-api-production.up.railway.app"

async def test_geocoding_ambiguous():
    """Geocoding API 기반 동명 지역 감지 테스트"""
    print("🌍 Geocoding API 기반 동명 지역 감지 테스트")
    
    test_cases = [
        {
            "name": "광주 (동명 지역 예상)",
            "city": "광주",
            "country": "대한민국",
            "expected": "AMBIGUOUS"
        },
        {
            "name": "김포 (단일 지역 예상)",
            "city": "김포",
            "country": "대한민국", 
            "expected": "SUCCESS"
        },
        {
            "name": "서울 (단일 지역 예상)",
            "city": "서울",
            "country": "대한민국",
            "expected": "SUCCESS"
        },
        {
            "name": "부산 (단일 지역 예상)",
            "city": "부산",
            "country": "대한민국",
            "expected": "SUCCESS"
        }
    ]
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}️⃣ {test_case['name']}")
            
            request_data = {
                "city": test_case["city"],
                "country": test_case["country"],
                "total_duration": 2,
                "travelers_count": 1,
                "travel_style": "관광",
                "budget_level": "중간"
            }
            
            try:
                response = await client.post(
                    f"{BASE_URL}/api/v1/place-recommendations/generate",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                print(f"   상태 코드: {response.status_code}")
                
                if response.status_code == 400:
                    # 동명 지역 감지된 경우
                    data = response.json()
                    error_code = data.get("error_code")
                    
                    if error_code == "AMBIGUOUS_LOCATION":
                        options = data.get("options", [])
                        print(f"   ✅ 동명 지역 감지! {len(options)}개 선택지")
                        
                        for j, option in enumerate(options[:3], 1):
                            display_name = option.get("display_name", "N/A")
                            formatted_address = option.get("formatted_address", "N/A")
                            print(f"     {j}. {display_name} - {formatted_address}")
                            
                        if test_case["expected"] == "AMBIGUOUS":
                            print(f"   🎯 예상 결과와 일치!")
                        else:
                            print(f"   ⚠️ 예상과 다름 (예상: {test_case['expected']})")
                    else:
                        print(f"   ❌ 다른 400 에러: {error_code}")
                        
                elif response.status_code == 200:
                    # 정상 처리된 경우
                    data = response.json()
                    is_fallback = data.get("is_fallback", False)
                    newly_recommended = data.get("newly_recommended_count", 0)
                    
                    print(f"   ✅ 정상 처리! 추천: {newly_recommended}개")
                    print(f"   폴백 여부: {is_fallback}")
                    
                    if test_case["expected"] == "SUCCESS":
                        print(f"   🎯 예상 결과와 일치!")
                    else:
                        print(f"   ⚠️ 예상과 다름 (예상: {test_case['expected']})")
                        
                else:
                    print(f"   ❌ 예상치 못한 상태 코드: {response.status_code}")
                    print(f"   응답: {response.text[:200]}")
                    
            except Exception as e:
                print(f"   💥 요청 실패: {e}")
                import traceback
                print(f"   상세: {traceback.format_exc()}")

async def test_specific_geocoding():
    """특정 도시의 Geocoding 결과 확인"""
    print("\n🔍 특정 도시 Geocoding 결과 확인")
    
    # Geocoding 서비스 직접 테스트
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 진단 API로 Geocoding 결과 확인
        try:
            response = await client.get(f"{BASE_URL}/api/v1/diagnosis/test-geocoding?city=광주&country=대한민국")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Geocoding 테스트 성공")
                print(f"   결과 수: {data.get('results_count', 0)}")
                print(f"   동명 지역 여부: {data.get('is_ambiguous', False)}")
                
                results = data.get('results', [])
                for i, result in enumerate(results[:3], 1):
                    formatted_address = result.get('formatted_address', 'N/A')
                    print(f"     {i}. {formatted_address}")
            else:
                print(f"   ❌ Geocoding 테스트 실패: {response.status_code}")
                
        except Exception as e:
            print(f"   💥 Geocoding 테스트 예외: {e}")

if __name__ == "__main__":
    asyncio.run(test_geocoding_ambiguous())
    asyncio.run(test_specific_geocoding())