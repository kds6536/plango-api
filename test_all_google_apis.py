#!/usr/bin/env python3
"""
모든 Google API 서비스 테스트 스크립트
"""

import asyncio
import sys
import os
import httpx
import json

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings

class GoogleAPITester:
    def __init__(self):
        self.backend_key = getattr(settings, "MAPS_PLATFORM_API_KEY_BACKEND", None)
        self.frontend_key = getattr(settings, "GOOGLE_MAPS_API_KEY", None)
        
        print(f"🔑 Backend Key: {self.backend_key[:20]}..." if self.backend_key else "❌ No Backend Key")
        print(f"🔑 Frontend Key: {self.frontend_key[:20]}..." if self.frontend_key else "❌ No Frontend Key")
        print()

    async def test_geocoding_api(self):
        """Geocoding API 테스트"""
        print("🌍 [GEOCODING API] 테스트 시작")
        
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": "광주, 대한민국",
            "key": self.backend_key,
            "language": "ko"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                
                print(f"  📊 Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    results_count = len(data.get("results", []))
                    
                    print(f"  📊 API Status: {status}")
                    print(f"  📊 Results Count: {results_count}")
                    
                    if status == "OK" and results_count > 0:
                        print("  ✅ Geocoding API 성공")
                        # 첫 번째 결과 출력
                        first_result = data["results"][0]
                        print(f"  📍 첫 번째 결과: {first_result.get('formatted_address')}")
                        return True
                    else:
                        print(f"  ❌ Geocoding API 실패: {status}")
                        return False
                else:
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                    print(f"  ❌ HTTP Error: {error_data}")
                    return False
                    
        except Exception as e:
            print(f"  💥 Exception: {e}")
            return False

    async def test_places_api_text_search(self):
        """Places API Text Search 테스트"""
        print("🏢 [PLACES API - Text Search] 테스트 시작")
        
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": "서울 맛집",
            "key": self.backend_key,
            "language": "ko"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                
                print(f"  📊 Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    results_count = len(data.get("results", []))
                    
                    print(f"  📊 API Status: {status}")
                    print(f"  📊 Results Count: {results_count}")
                    
                    if status == "OK" and results_count > 0:
                        print("  ✅ Places Text Search API 성공")
                        # 첫 번째 결과 출력
                        first_result = data["results"][0]
                        print(f"  🍽️ 첫 번째 결과: {first_result.get('name')}")
                        return True
                    else:
                        print(f"  ❌ Places Text Search API 실패: {status}")
                        return False
                else:
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                    print(f"  ❌ HTTP Error: {error_data}")
                    return False
                    
        except Exception as e:
            print(f"  💥 Exception: {e}")
            return False

    async def test_places_api_new(self):
        """Places API (New) 테스트"""
        print("🏢 [PLACES API - New] 테스트 시작")
        
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.backend_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating"
        }
        
        payload = {
            "textQuery": "서울 맛집",
            "languageCode": "ko"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                
                print(f"  📊 Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    places_count = len(data.get("places", []))
                    
                    print(f"  📊 Places Count: {places_count}")
                    
                    if places_count > 0:
                        print("  ✅ Places API (New) 성공")
                        # 첫 번째 결과 출력
                        first_place = data["places"][0]
                        print(f"  🍽️ 첫 번째 결과: {first_place.get('displayName', {}).get('text')}")
                        return True
                    else:
                        print("  ❌ Places API (New) 실패: 결과 없음")
                        return False
                else:
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                    print(f"  ❌ HTTP Error: {error_data}")
                    return False
                    
        except Exception as e:
            print(f"  💥 Exception: {e}")
            return False

    async def test_directions_api(self):
        """Directions API 테스트"""
        print("🚗 [DIRECTIONS API] 테스트 시작")
        
        url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            "origin": "서울역",
            "destination": "강남역",
            "key": self.backend_key,
            "language": "ko"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                
                print(f"  📊 Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    routes_count = len(data.get("routes", []))
                    
                    print(f"  📊 API Status: {status}")
                    print(f"  📊 Routes Count: {routes_count}")
                    
                    if status == "OK" and routes_count > 0:
                        print("  ✅ Directions API 성공")
                        # 첫 번째 경로 정보 출력
                        first_route = data["routes"][0]
                        duration = first_route["legs"][0]["duration"]["text"]
                        distance = first_route["legs"][0]["distance"]["text"]
                        print(f"  🚗 경로 정보: {duration}, {distance}")
                        return True
                    else:
                        print(f"  ❌ Directions API 실패: {status}")
                        return False
                else:
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                    print(f"  ❌ HTTP Error: {error_data}")
                    return False
                    
        except Exception as e:
            print(f"  💥 Exception: {e}")
            return False

    async def test_places_details_api(self):
        """Places Details API 테스트"""
        print("🏢 [PLACES DETAILS API] 테스트 시작")
        
        # 먼저 place_id를 얻기 위해 간단한 검색
        search_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        search_params = {
            "input": "경복궁",
            "inputtype": "textquery",
            "fields": "place_id",
            "key": self.backend_key
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # 1. place_id 검색
                search_response = await client.get(search_url, params=search_params)
                
                if search_response.status_code != 200:
                    print(f"  ❌ Place ID 검색 실패: {search_response.status_code}")
                    return False
                
                search_data = search_response.json()
                if not search_data.get("candidates"):
                    print("  ❌ Place ID를 찾을 수 없음")
                    return False
                
                place_id = search_data["candidates"][0]["place_id"]
                print(f"  📍 Place ID 획득: {place_id[:20]}...")
                
                # 2. Place Details 조회
                details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                details_params = {
                    "place_id": place_id,
                    "fields": "name,formatted_address,rating,opening_hours",
                    "key": self.backend_key,
                    "language": "ko"
                }
                
                details_response = await client.get(details_url, params=details_params)
                
                print(f"  📊 Status Code: {details_response.status_code}")
                
                if details_response.status_code == 200:
                    data = details_response.json()
                    status = data.get("status")
                    
                    print(f"  📊 API Status: {status}")
                    
                    if status == "OK" and "result" in data:
                        print("  ✅ Places Details API 성공")
                        result = data["result"]
                        print(f"  🏛️ 장소명: {result.get('name')}")
                        print(f"  📍 주소: {result.get('formatted_address')}")
                        print(f"  ⭐ 평점: {result.get('rating')}")
                        return True
                    else:
                        print(f"  ❌ Places Details API 실패: {status}")
                        return False
                else:
                    error_data = details_response.json() if details_response.headers.get('content-type', '').startswith('application/json') else details_response.text
                    print(f"  ❌ HTTP Error: {error_data}")
                    return False
                    
        except Exception as e:
            print(f"  💥 Exception: {e}")
            return False

    async def run_all_tests(self):
        """모든 API 테스트 실행"""
        print("🚀 Google APIs 전체 테스트 시작")
        print("=" * 60)
        
        tests = [
            ("Geocoding API", self.test_geocoding_api),
            ("Places API - Text Search", self.test_places_api_text_search),
            ("Places API - New", self.test_places_api_new),
            ("Directions API", self.test_directions_api),
            ("Places Details API", self.test_places_details_api),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                success = await test_func()
                results[test_name] = success
            except Exception as e:
                print(f"💥 {test_name} 테스트 중 예외 발생: {e}")
                results[test_name] = False
            
            print()
        
        # 결과 요약
        print("=" * 60)
        print("📊 테스트 결과 요약")
        print("=" * 60)
        
        success_count = 0
        for test_name, success in results.items():
            status = "✅ 성공" if success else "❌ 실패"
            print(f"{test_name}: {status}")
            if success:
                success_count += 1
        
        print(f"\n총 {len(tests)}개 테스트 중 {success_count}개 성공")
        
        if success_count == 0:
            print("🚨 모든 API가 실패했습니다. API 키 제한 문제일 가능성이 높습니다.")
        elif success_count < len(tests):
            print("⚠️ 일부 API만 작동합니다. 특정 API에 제한이 있을 수 있습니다.")
        else:
            print("🎉 모든 API가 정상 작동합니다!")
        
        return results

async def main():
    tester = GoogleAPITester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())