#!/usr/bin/env python3
"""
상세한 API 진단 스크립트
"""

import asyncio
import sys
import os
import httpx
import json

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings

class DetailedAPIDiagnosis:
    def __init__(self):
        self.backend_key = getattr(settings, "MAPS_PLATFORM_API_KEY_BACKEND", None)
        self.frontend_key = getattr(settings, "MAPS_PLATFORM_API_KEY", None)
        
        print("🔍 상세 API 진단 시작")
        print("=" * 60)
        print(f"🔑 Backend Key: {self.backend_key[:20]}...{self.backend_key[-10:]}" if self.backend_key else "❌ No Backend Key")
        print(f"🔑 Frontend Key: {self.frontend_key[:20]}...{self.frontend_key[-10:]}" if self.frontend_key else "❌ No Frontend Key")
        print(f"🔍 Keys are same: {self.backend_key == self.frontend_key}")
        print()

    async def test_api_with_detailed_error(self, api_name, url, params=None, headers=None, method="GET", json_data=None):
        """API 호출 상세 테스트"""
        print(f"🧪 [{api_name}] 테스트 시작")
        print(f"  📍 URL: {url}")
        
        if params:
            print(f"  📊 Params: {params}")
        if headers:
            print(f"  📊 Headers: {headers}")
        if json_data:
            print(f"  📊 JSON Data: {json_data}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    response = await client.get(url, params=params, headers=headers)
                else:
                    response = await client.post(url, params=params, headers=headers, json=json_data)
                
                print(f"  📊 Status Code: {response.status_code}")
                print(f"  📊 Response Headers: {dict(response.headers)}")
                
                # 응답 내용 분석
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    try:
                        data = response.json()
                        print(f"  📊 Response JSON:")
                        print(json.dumps(data, indent=4, ensure_ascii=False))
                        
                        # 에러 상세 분석
                        if response.status_code != 200:
                            if 'error' in data:
                                error = data['error']
                                print(f"  🚨 Error Code: {error.get('code')}")
                                print(f"  🚨 Error Message: {error.get('message')}")
                                print(f"  🚨 Error Status: {error.get('status')}")
                                
                                if 'details' in error:
                                    for detail in error['details']:
                                        print(f"  🔍 Detail Type: {detail.get('@type')}")
                                        print(f"  🔍 Detail Reason: {detail.get('reason')}")
                                        if 'metadata' in detail:
                                            print(f"  🔍 Metadata: {detail['metadata']}")
                        
                        return response.status_code == 200 and data.get('status') == 'OK'
                        
                    except json.JSONDecodeError:
                        print(f"  ❌ JSON 파싱 실패")
                        print(f"  📝 Raw Response: {response.text[:500]}...")
                        return False
                else:
                    print(f"  📝 Raw Response: {response.text[:500]}...")
                    return response.status_code == 200
                    
        except Exception as e:
            print(f"  💥 Exception: {e}")
            return False

    async def test_geocoding_detailed(self):
        """Geocoding API 상세 테스트"""
        print("\n" + "="*20 + " GEOCODING API 상세 테스트 " + "="*20)
        
        # 테스트 1: 백엔드 키로 간단한 주소
        await self.test_api_with_detailed_error(
            "Geocoding - Backend Key - 서울",
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={
                "address": "서울",
                "key": self.backend_key,
                "language": "ko"
            }
        )
        
        # 테스트 2: 프론트엔드 키로 동일한 요청
        await self.test_api_with_detailed_error(
            "Geocoding - Frontend Key - 서울",
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={
                "address": "서울",
                "key": self.frontend_key,
                "language": "ko"
            }
        )
        
        # 테스트 3: 동명 지역 테스트
        await self.test_api_with_detailed_error(
            "Geocoding - Backend Key - 광주",
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={
                "address": "광주, 대한민국",
                "key": self.backend_key,
                "language": "ko"
            }
        )

    async def test_places_detailed(self):
        """Places API 상세 테스트"""
        print("\n" + "="*20 + " PLACES API 상세 테스트 " + "="*20)
        
        # 테스트 1: Text Search (Old API)
        await self.test_api_with_detailed_error(
            "Places Text Search - Backend Key",
            "https://maps.googleapis.com/maps/api/place/textsearch/json",
            params={
                "query": "서울 맛집",
                "key": self.backend_key,
                "language": "ko"
            }
        )
        
        # 테스트 2: New Places API
        await self.test_api_with_detailed_error(
            "Places New API - Backend Key",
            "https://places.googleapis.com/v1/places:searchText",
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.backend_key,
                "X-Goog-FieldMask": "places.displayName,places.formattedAddress"
            },
            method="POST",
            json_data={
                "textQuery": "서울 맛집",
                "languageCode": "ko"
            }
        )

    async def test_directions_detailed(self):
        """Directions API 상세 테스트"""
        print("\n" + "="*20 + " DIRECTIONS API 상세 테스트 " + "="*20)
        
        await self.test_api_with_detailed_error(
            "Directions - Backend Key",
            "https://maps.googleapis.com/maps/api/directions/json",
            params={
                "origin": "서울역",
                "destination": "강남역",
                "key": self.backend_key,
                "language": "ko"
            }
        )

    async def test_key_info(self):
        """API 키 정보 확인"""
        print("\n" + "="*20 + " API 키 정보 확인 " + "="*20)
        
        # 키 정보 API 호출 (실제로는 존재하지 않지만 에러 메시지로 정보 확인 가능)
        await self.test_api_with_detailed_error(
            "Key Info Check",
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={
                "address": "",  # 빈 주소로 테스트
                "key": self.backend_key
            }
        )

    async def run_full_diagnosis(self):
        """전체 진단 실행"""
        await self.test_key_info()
        await self.test_geocoding_detailed()
        await self.test_places_detailed()
        await self.test_directions_detailed()
        
        print("\n" + "="*60)
        print("📊 진단 완료")
        print("="*60)
        print("🔍 위 결과를 바탕으로 정확한 문제점을 파악할 수 있습니다.")
        print("📝 특히 error.details 섹션의 reason과 metadata를 확인해주세요.")

async def main():
    diagnosis = DetailedAPIDiagnosis()
    await diagnosis.run_full_diagnosis()

if __name__ == "__main__":
    asyncio.run(main())