#!/usr/bin/env python3
"""
Railway API 직접 테스트
"""

import asyncio
import httpx
import json

RAILWAY_BASE_URL = "https://plango-api-production.up.railway.app"

async def test_direct_api_calls():
    """Railway API 직접 호출 테스트"""
    print("🌐 Railway API 직접 테스트")
    
    # 1. 서버 상태 확인
    print(f"\n  🖥️ 서버 상태 확인")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{RAILWAY_BASE_URL}/api/v1/diagnosis/server-info")
            
            if response.status_code == 200:
                data = response.json()
                print(f"    ✅ 서버 정상 작동")
                print(f"    🐍 Python: {data.get('python_version')}")
                print(f"    🖥️ 플랫폼: {data.get('platform')}")
                
                env_vars = data.get('environment_variables', {})
                backend_key = env_vars.get('MAPS_PLATFORM_API_KEY_BACKEND')
                print(f"    🔑 Backend API Key: {'있음' if backend_key else '없음'}")
            else:
                print(f"    ❌ 서버 에러: {response.status_code}")
                
    except Exception as e:
        print(f"    💥 서버 연결 실패: {e}")
    
    # 2. Google API 상태 확인
    print(f"\n  🔍 Google API 상태 확인")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{RAILWAY_BASE_URL}/api/v1/diagnosis/google-apis")
            
            if response.status_code == 200:
                data = response.json()
                api_tests = data.get("api_tests", {})
                
                for api_name, result in api_tests.items():
                    success = result.get("success", False)
                    status = "✅" if success else "❌"
                    print(f"    {status} {api_name}: {'성공' if success else '실패'}")
                    
                    if not success:
                        error = result.get("error_message", "")
                        print(f"      📝 에러: {error[:100]}")
                        
                summary = data.get("summary", {})
                print(f"    📊 총 {summary.get('working_apis')}/{summary.get('total_apis')} APIs 작동")
            else:
                print(f"    ❌ API 진단 실패: {response.status_code}")
                
    except Exception as e:
        print(f"    💥 API 진단 실패: {e}")
    
    # 3. 서울 장소 추천 직접 테스트
    print(f"\n  🏙️ 서울 장소 추천 직접 테스트")
    try:
        payload = {
            "city": "서울",
            "country": "대한민국",
            "total_duration": 1,
            "travelers_count": 1,
            "travel_style": "관광",
            "budget_level": "중간"
        }
        
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{RAILWAY_BASE_URL}/api/v1/place-recommendations/generate",
                json=payload
            )
            
            print(f"    📊 Status Code: {response.status_code}")
            print(f"    📄 Content-Type: {response.headers.get('content-type')}")
            
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                
                if response.status_code == 400:
                    error_code = data.get("error_code")
                    if error_code == "AMBIGUOUS_LOCATION":
                        print(f"    🎯 동명 지역 감지됨")
                        options = data.get("options", [])
                        print(f"    📍 선택지 수: {len(options)}")
                        
                        for i, option in enumerate(options[:2]):
                            display_name = option.get("display_name", "N/A")
                            place_id = option.get("place_id", "N/A")
                            print(f"      {i+1}. {display_name}")
                            print(f"         ID: {place_id[:30]}...")
                    else:
                        print(f"    ❌ 400 에러: {data.get('message')}")
                        
                elif response.status_code == 200:
                    success = data.get("success", False)
                    is_fallback = data.get("is_fallback", False)
                    
                    print(f"    📊 성공: {success}")
                    print(f"    📊 폴백: {is_fallback}")
                    
                    if is_fallback:
                        print(f"    ⚠️ 폴백 이유: {data.get('fallback_reason')}")
                    else:
                        print(f"    🎉 Plan A 성공!")
                        print(f"    📊 추천 수: {data.get('newly_recommended_count')}")
                        
                else:
                    print(f"    ❌ 예상치 못한 상태: {response.status_code}")
                    print(f"    📄 응답: {json.dumps(data, ensure_ascii=False, indent=2)[:300]}")
            else:
                print(f"    📄 Raw Response: {response.text[:300]}")
                
    except asyncio.TimeoutError:
        print(f"    ⏰ 타임아웃 (90초 초과)")
    except Exception as e:
        print(f"    💥 예외: {e}")

async def main():
    print("🚀 Railway API 직접 테스트")
    print("=" * 60)
    
    await test_direct_api_calls()
    
    print("\n" + "=" * 60)
    print("📋 결론:")
    print("1. 서버와 Google API 상태 확인")
    print("2. 서울 요청의 정확한 응답 확인")
    print("3. 동명 지역 감지 vs Plan A 성공 vs 폴백 구분")

if __name__ == "__main__":
    asyncio.run(main())