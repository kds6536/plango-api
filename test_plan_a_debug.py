#!/usr/bin/env python3
"""
Plan A 실패 원인 상세 디버깅
"""

import asyncio
import httpx
import json

RAILWAY_BASE_URL = "https://plango-api-production.up.railway.app"

async def test_plan_a_detailed():
    """Plan A 실패 원인 상세 분석"""
    print("🔍 Plan A 실패 원인 상세 분석")
    
    # 간단한 테스트 케이스
    test_cases = [
        {
            "name": "서울 기본 테스트",
            "payload": {
                "city": "서울",
                "country": "대한민국",
                "total_duration": 2,
                "travelers_count": 2,
                "travel_style": "관광",
                "budget_level": "중간"
            }
        },
        {
            "name": "부산 기본 테스트", 
            "payload": {
                "city": "부산",
                "country": "대한민국",
                "total_duration": 1,
                "travelers_count": 1,
                "travel_style": "휴양",
                "budget_level": "저렴"
            }
        }
    ]
    
    url = f"{RAILWAY_BASE_URL}/api/v1/place-recommendations/generate"
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n  🧪 테스트 {i}: {test_case['name']}")
        print(f"    📤 요청: {json.dumps(test_case['payload'], ensure_ascii=False)}")
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:  # 긴 타임아웃
                response = await client.post(url, json=test_case["payload"])
                
                print(f"    📊 Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    success = data.get("success", False)
                    is_fallback = data.get("is_fallback", False)
                    
                    print(f"    📊 성공: {success}")
                    print(f"    📊 폴백: {is_fallback}")
                    
                    if is_fallback:
                        print(f"    ⚠️ 폴백 이유: {data.get('fallback_reason')}")
                        print(f"    💡 Plan A가 실패했음을 의미")
                    else:
                        print(f"    ✅ Plan A 성공!")
                        print(f"    📊 추천 수: {data.get('newly_recommended_count')}")
                        
                    # 응답 구조 확인
                    print(f"    📋 응답 키들: {list(data.keys())}")
                    
                elif response.status_code == 400:
                    data = response.json()
                    error_code = data.get("error_code")
                    
                    if error_code == "AMBIGUOUS_LOCATION":
                        print(f"    🎯 동명 지역 감지됨")
                        options = data.get("options", [])
                        print(f"    📍 선택지: {len(options)}개")
                    else:
                        print(f"    ❌ 400 에러: {data.get('message')}")
                        
                elif response.status_code == 500:
                    print(f"    💥 서버 에러: {response.text[:200]}")
                    
                else:
                    print(f"    ❓ 예상치 못한 상태 코드: {response.text[:200]}")
                    
        except asyncio.TimeoutError:
            print(f"    ⏰ 타임아웃 - Plan A 처리 시간이 너무 오래 걸림")
        except Exception as e:
            print(f"    💥 예외: {e}")

async def test_individual_services():
    """개별 서비스 테스트"""
    print("\n🔧 개별 서비스 상태 확인")
    
    # 서비스별 테스트 엔드포인트들
    test_endpoints = [
        {
            "name": "서버 정보",
            "url": f"{RAILWAY_BASE_URL}/api/v1/diagnosis/server-info",
            "method": "GET"
        },
        {
            "name": "Google API 진단",
            "url": f"{RAILWAY_BASE_URL}/api/v1/diagnosis/google-apis",
            "method": "GET"
        },
        {
            "name": "Geocoding 테스트",
            "url": f"{RAILWAY_BASE_URL}/api/v1/diagnosis/test-specific-api?api_name=geocoding",
            "method": "POST",
            "json": {"address": "서울"}
        }
    ]
    
    for test in test_endpoints:
        print(f"\n  🔍 {test['name']} 테스트")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if test["method"] == "GET":
                    response = await client.get(test["url"])
                else:
                    response = await client.post(test["url"], json=test.get("json", {}))
                
                print(f"    📊 Status: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"    ✅ 성공")
                    
                    # 중요한 정보만 출력
                    if "google-apis" in test["url"]:
                        data = response.json()
                        summary = data.get("summary", {})
                        print(f"    📊 API 상태: {summary.get('working_apis')}/{summary.get('total_apis')} 작동")
                        
                else:
                    print(f"    ❌ 실패: {response.text[:100]}")
                    
        except Exception as e:
            print(f"    💥 예외: {e}")

async def main():
    print("🚀 Plan A 실패 원인 상세 디버깅")
    print("=" * 60)
    
    await test_individual_services()
    await test_plan_a_detailed()
    
    print("\n" + "=" * 60)
    print("📋 분석 포인트:")
    print("1. Plan A가 실패하면 항상 폴백으로 처리됨")
    print("2. 타임아웃이 발생하면 처리 시간 문제")
    print("3. 500 에러가 발생하면 서버 내부 오류")
    print("4. Google API는 성공하지만 Plan A에서 다른 문제 발생 가능")

if __name__ == "__main__":
    asyncio.run(main())