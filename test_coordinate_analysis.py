#!/usr/bin/env python3
"""
서울 좌표 분석 테스트
"""

import asyncio
import httpx
import json

RAILWAY_BASE_URL = "https://plango-api-production.up.railway.app"

async def analyze_seoul_coordinates():
    """서울의 실제 좌표 분석"""
    print("🔍 서울 좌표 상세 분석")
    
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
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            
            if response.status_code == 400:
                data = response.json()
                error_code = data.get("error_code")
                
                if error_code == "AMBIGUOUS_LOCATION":
                    options = data.get("options", [])
                    print(f"  📍 총 {len(options)}개 선택지:")
                    
                    for i, option in enumerate(options):
                        display_name = option.get("display_name", "N/A")
                        place_id = option.get("place_id", "N/A")
                        lat = option.get("lat")
                        lng = option.get("lng")
                        formatted_address = option.get("formatted_address", "N/A")
                        
                        print(f"\n    🏛️ 선택지 {i+1}:")
                        print(f"      📝 표시명: {display_name}")
                        print(f"      📍 좌표: {lat}, {lng}")
                        print(f"      🆔 Place ID: {place_id}")
                        print(f"      📧 전체 주소: {formatted_address}")
                        
                        # 좌표 반올림 확인
                        if lat is not None and lng is not None:
                            rounded_lat = round(lat, 2)
                            rounded_lng = round(lng, 2)
                            print(f"      🔄 반올림 좌표: {rounded_lat}, {rounded_lng}")
                    
                    # 좌표 비교 분석
                    if len(options) >= 2:
                        print(f"\n  🔍 좌표 비교 분석:")
                        
                        for i in range(len(options)):
                            for j in range(i+1, len(options)):
                                opt1 = options[i]
                                opt2 = options[j]
                                
                                lat1, lng1 = opt1.get("lat"), opt1.get("lng")
                                lat2, lng2 = opt2.get("lat"), opt2.get("lng")
                                
                                if lat1 is not None and lng1 is not None and lat2 is not None and lng2 is not None:
                                    # 원본 좌표 차이
                                    lat_diff = abs(lat1 - lat2)
                                    lng_diff = abs(lng1 - lng2)
                                    
                                    # 반올림 좌표 비교
                                    rounded_lat1 = round(lat1, 2)
                                    rounded_lng1 = round(lng1, 2)
                                    rounded_lat2 = round(lat2, 2)
                                    rounded_lng2 = round(lng2, 2)
                                    
                                    same_rounded = (rounded_lat1 == rounded_lat2) and (rounded_lng1 == rounded_lng2)
                                    
                                    print(f"    📊 선택지 {i+1} vs {j+1}:")
                                    print(f"      원본 차이: lat={lat_diff:.6f}, lng={lng_diff:.6f}")
                                    print(f"      반올림 동일: {same_rounded}")
                                    
                                    if same_rounded:
                                        print(f"      💡 중복으로 제거되어야 함!")
                                    else:
                                        print(f"      ✅ 서로 다른 위치")
                else:
                    print(f"  ❌ 다른 400 에러: {data.get('message')}")
            else:
                print(f"  ❌ 예상치 못한 상태 코드: {response.status_code}")
                
    except Exception as e:
        print(f"  💥 예외: {e}")

async def test_geocoding_raw():
    """Geocoding API 원본 결과 확인"""
    print(f"\n🌍 Geocoding API 원본 결과 확인")
    
    url = f"{RAILWAY_BASE_URL}/api/v1/diagnosis/test-specific-api"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{url}?api_name=geocoding", 
                json={"address": "서울"}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                success = data.get("success", False)
                results_count = data.get("results_count", 0)
                
                print(f"  📊 성공: {success}")
                print(f"  📊 결과 수: {results_count}")
                
                if success:
                    sample_result = data.get("sample_result", "N/A")
                    print(f"  📍 첫 번째 결과: {sample_result}")
                    
                    # API 진단에서 더 상세한 정보를 제공하도록 수정 필요
                    print(f"  💡 API 진단에서는 상세 좌표 정보를 제공하지 않음")
                    print(f"  💡 실제 중복 제거는 place-recommendations 엔드포인트에서 확인 필요")
                else:
                    error_msg = data.get("error_message", "Unknown")
                    print(f"  ❌ 실패: {error_msg}")
            else:
                print(f"  ❌ HTTP 에러: {response.status_code}")
                
    except Exception as e:
        print(f"  💥 예외: {e}")

async def main():
    print("🚀 서울 좌표 및 중복 제거 분석")
    print("=" * 60)
    
    await analyze_seoul_coordinates()
    await test_geocoding_raw()
    
    print("\n" + "=" * 60)
    print("📋 분석 결과:")
    print("1. 두 선택지의 좌표가 동일하면 중복 제거 로직 문제")
    print("2. 좌표가 다르면 실제로 서로 다른 지역")
    print("3. 반올림 후에도 다르면 중복 제거 임계값 조정 필요")

if __name__ == "__main__":
    asyncio.run(main())