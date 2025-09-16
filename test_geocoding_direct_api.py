#!/usr/bin/env python3
"""
Google Geocoding API 직접 테스트
"""

import asyncio
import httpx
import os
from datetime import datetime

async def test_geocoding_direct():
    """Google Geocoding API 직접 호출 테스트"""
    
    print("🌍 [GEOCODING_DIRECT] Google Geocoding API 직접 테스트")
    print(f"⏰ [TIME] {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Google Geocoding API 키 (환경변수에서 가져오기)
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        print("❌ [ERROR] GOOGLE_MAPS_API_KEY 환경변수가 설정되지 않았습니다.")
        return
    
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    
    # 테스트할 쿼리들
    test_queries = [
        "광주, 대한민국",
        "광주",
        "Gwangju, South Korea", 
        "Gwangju",
        "광주시, 대한민국",
        "Springfield, United States",
        "Springfield",
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, query in enumerate(test_queries, 1):
            print(f"\n🧪 [TEST_{i}] 쿼리: '{query}'")
            
            try:
                params = {
                    "address": query,
                    "key": api_key,
                    "language": "ko"
                }
                
                response = await client.get(base_url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status", "UNKNOWN")
                    results = data.get("results", [])
                    
                    print(f"📊 [RESULT] 상태: {status}")
                    print(f"📊 [RESULT] 결과 개수: {len(results)}")
                    
                    if status == "OK" and results:
                        for j, result in enumerate(results[:3]):  # 최대 3개만 표시
                            formatted_address = result.get("formatted_address", "Unknown")
                            place_id = result.get("place_id", "Unknown")
                            types = result.get("types", [])
                            
                            print(f"  {j+1}. {formatted_address}")
                            print(f"     Place ID: {place_id}")
                            print(f"     Types: {types}")
                        
                        # 동명 지역 여부 판단
                        if len(results) > 1:
                            print(f"✅ [AMBIGUOUS] 동명 지역 감지! {len(results)}개 결과")
                        else:
                            print(f"ℹ️ [SINGLE] 단일 결과")
                    else:
                        print(f"❌ [ERROR] API 오류: {status}")
                        
                else:
                    print(f"❌ [HTTP_ERROR] HTTP 오류: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ [EXCEPTION] 예외 발생: {e}")
            
            # 다음 요청 전 잠시 대기 (API 제한 방지)
            if i < len(test_queries):
                await asyncio.sleep(1)

async def main():
    await test_geocoding_direct()

if __name__ == "__main__":
    asyncio.run(main())