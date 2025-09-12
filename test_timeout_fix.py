#!/usr/bin/env python3
"""
타임아웃 문제 해결 테스트
"""

import asyncio
import httpx
import json

RAILWAY_BASE_URL = "https://plango-api-production.up.railway.app"

async def test_with_longer_timeout():
    """더 긴 타임아웃으로 테스트"""
    print("⏰ 긴 타임아웃으로 서울 테스트")
    
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
        # 5분 타임아웃으로 테스트
        async with httpx.AsyncClient(timeout=300.0) as client:
            print(f"  📤 요청 전송 중... (5분 타임아웃)")
            
            response = await client.post(url, json=payload)
            
            print(f"  📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                is_fallback = data.get("is_fallback", False)
                
                print(f"  📊 성공: {success}")
                print(f"  📊 폴백: {is_fallback}")
                
                if is_fallback:
                    print(f"  ⚠️ 폴백 이유: {data.get('fallback_reason')}")
                else:
                    print(f"  🎉 Plan A 성공!")
                    print(f"  📊 추천 수: {data.get('newly_recommended_count')}")
                    
            elif response.status_code == 400:
                data = response.json()
                error_code = data.get("error_code")
                
                if error_code == "AMBIGUOUS_LOCATION":
                    print(f"  🎯 동명 지역 감지됨")
                    options = data.get("options", [])
                    print(f"  📍 선택지 수: {len(options)}")
                    
                    for i, option in enumerate(options[:2]):
                        display_name = option.get("display_name", "N/A")
                        print(f"    {i+1}. {display_name}")
                else:
                    print(f"  ❌ 400 에러: {data.get('message')}")
                    
            elif response.status_code == 500:
                print(f"  💥 서버 에러")
                try:
                    data = response.json()
                    print(f"  📄 에러 내용: {data.get('detail', 'N/A')}")
                except:
                    print(f"  📄 Raw Response: {response.text[:200]}")
                    
            else:
                print(f"  ❓ 예상치 못한 상태 코드")
                
    except asyncio.TimeoutError:
        print(f"  ⏰ 타임아웃 (5분 초과) - 서버에서 무한 루프 또는 심각한 성능 문제")
    except Exception as e:
        print(f"  💥 예외: {type(e).__name__}: {e}")

async def test_simple_api():
    """간단한 API 테스트"""
    print(f"\n🔍 간단한 API 테스트")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 서버 상태 확인
            response = await client.get(f"{RAILWAY_BASE_URL}/api/v1/diagnosis/server-info")
            
            if response.status_code == 200:
                print(f"  ✅ 서버 정상 작동")
            else:
                print(f"  ❌ 서버 문제: {response.status_code}")
                
    except Exception as e:
        print(f"  💥 서버 연결 실패: {e}")

async def main():
    print("🚀 타임아웃 문제 해결 테스트")
    print("=" * 50)
    
    await test_simple_api()
    await test_with_longer_timeout()
    
    print("\n" + "=" * 50)
    print("📋 결론:")
    print("1. 5분 타임아웃에도 응답 없으면 무한 루프 문제")
    print("2. 서버 에러면 Plan A 코드 수정 필요")
    print("3. 동명 지역 감지되면 새 로직 작동")

if __name__ == "__main__":
    asyncio.run(main())