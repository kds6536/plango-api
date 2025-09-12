#!/usr/bin/env python3
"""
광주 다양한 검색어 테스트
"""

import asyncio
import httpx
import json

RAILWAY_BASE_URL = "https://plango-api-production.up.railway.app"

async def test_geocoding_variations():
    """다양한 광주 검색어 테스트"""
    print("🔍 다양한 광주 검색어 테스트")
    
    search_queries = [
        "광주",
        "광주, 대한민국",
        "광주시",
        "광주광역시",
        "경기도 광주시",
        "Gwangju",
        "Gwangju, South Korea",
        "Gwangju Metropolitan City",
        "Gwangju, Gyeonggi Province"
    ]
    
    url = f"{RAILWAY_BASE_URL}/api/v1/diagnosis/test-specific-api"
    
    for query in search_queries:
        print(f"\n  🔍 '{query}' 테스트")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{url}?api_name=geocoding", 
                    json={"address": query}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    success = data.get("success", False)
                    results_count = data.get("results_count", 0)
                    
                    print(f"    📊 성공: {success}, 결과 수: {results_count}")
                    
                    if success:
                        sample_result = data.get("sample_result", "N/A")
                        print(f"    📍 결과: {sample_result}")
                        
                        if results_count > 1:
                            print(f"    🎯 여러 결과! 동명 지역 감지 가능")
                        else:
                            print(f"    ✅ 단일 결과")
                    else:
                        error_msg = data.get("error_message", "Unknown")
                        print(f"    ❌ 실패: {error_msg}")
                else:
                    print(f"    ❌ HTTP 에러: {response.status_code}")
                    
        except Exception as e:
            print(f"    💥 예외: {e}")

async def main():
    print("🚀 광주 검색어 변형 테스트")
    print("=" * 60)
    print("📋 목표: 여러 결과를 반환하는 검색어 찾기")
    print("=" * 60)
    
    await test_geocoding_variations()
    
    print("\n" + "=" * 60)
    print("📊 결론:")
    print("1. 여러 결과가 나오는 검색어가 있으면 그것을 사용")
    print("2. 모든 검색어가 단일 결과면 하드코딩된 동명 지역 목록 필요")

if __name__ == "__main__":
    asyncio.run(main())