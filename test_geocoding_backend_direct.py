#!/usr/bin/env python3
"""
백엔드에서 직접 Geocoding API 테스트
API 키가 정상이라면 다른 원인을 찾아보자
"""

import os
import sys
import asyncio
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_geocoding_backend():
    """백엔드에서 직접 Geocoding 서비스 테스트"""
    
    print(f"🕐 백엔드 Geocoding 테스트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 환경 변수 확인
        print("\n🔑 환경 변수 확인")
        print("=" * 50)
        
        from app.config import settings
        
        backend_key = getattr(settings, "MAPS_PLATFORM_API_KEY_BACKEND", None)
        frontend_key = getattr(settings, "GOOGLE_MAPS_API_KEY", None)
        unrestricted_key = os.getenv("GOOGLE_MAPS_UNRESTRICTED_KEY")
        
        print(f"Backend Key: {'있음' if backend_key else '없음'}")
        print(f"Frontend Key: {'있음' if frontend_key else '없음'}")
        print(f"Unrestricted Key: {'있음' if unrestricted_key else '없음'}")
        
        if backend_key:
            print(f"Backend Key 앞 20자: {backend_key[:20]}...")
        if frontend_key:
            print(f"Frontend Key 앞 20자: {frontend_key[:20]}...")
        if unrestricted_key:
            print(f"Unrestricted Key 앞 20자: {unrestricted_key[:20]}...")
        
        # 2. API 키 매니저 테스트
        print("\n🔧 API 키 매니저 테스트")
        print("=" * 50)
        
        from app.services.api_key_manager import api_key_manager
        
        best_key = api_key_manager.get_best_key_for_service("geocoding")
        print(f"선택된 최적 키: {'있음' if best_key else '없음'}")
        if best_key:
            print(f"선택된 키 앞 20자: {best_key[:20]}...")
        
        # 3. Geocoding 서비스 직접 테스트
        print("\n🌍 Geocoding 서비스 직접 테스트")
        print("=" * 50)
        
        from app.services.geocoding_service import GeocodingService
        
        geocoding_service = GeocodingService()
        
        # 3-1. 서울 테스트
        print("📍 서울 테스트...")
        try:
            seoul_results = await geocoding_service.get_geocode_results("서울, 대한민국")
            print(f"   ✅ 서울 결과: {len(seoul_results)}개")
            if seoul_results:
                for i, result in enumerate(seoul_results[:2]):  # 처음 2개만 출력
                    print(f"   {i+1}. {result.get('formatted_address', 'N/A')}")
            else:
                print("   ⚠️ 서울 결과가 없습니다")
        except Exception as e:
            print(f"   💥 서울 테스트 실패: {e}")
        
        # 3-2. 광주 테스트 (동명 지역)
        print("\n📍 광주 테스트 (동명 지역)...")
        try:
            gwangju_results = await geocoding_service.get_geocode_results("광주, 대한민국")
            print(f"   ✅ 광주 결과: {len(gwangju_results)}개")
            if gwangju_results:
                for i, result in enumerate(gwangju_results):
                    print(f"   {i+1}. {result.get('formatted_address', 'N/A')}")
                
                # 동명 지역 감지 테스트
                is_ambiguous = geocoding_service.is_ambiguous_location(gwangju_results)
                print(f"   동명 지역 감지: {'예' if is_ambiguous else '아니오'}")
            else:
                print("   ⚠️ 광주 결과가 없습니다")
        except Exception as e:
            print(f"   💥 광주 테스트 실패: {e}")
        
        # 3-3. 존재하지 않는 도시 테스트
        print("\n📍 존재하지 않는 도시 테스트...")
        try:
            fake_results = await geocoding_service.get_geocode_results("asdfasdf, 대한민국")
            print(f"   ✅ 가짜 도시 결과: {len(fake_results)}개")
            if fake_results:
                print("   ⚠️ 예상치 못한 결과가 있습니다")
                for i, result in enumerate(fake_results):
                    print(f"   {i+1}. {result.get('formatted_address', 'N/A')}")
            else:
                print("   ✅ 예상대로 결과가 없습니다")
        except Exception as e:
            print(f"   💥 가짜 도시 테스트 실패: {e}")
        
        # 4. Google Maps 클라이언트 직접 테스트
        print("\n🗺️ Google Maps 클라이언트 직접 테스트")
        print("=" * 50)
        
        import googlemaps
        
        if best_key:
            try:
                gmaps = googlemaps.Client(key=best_key)
                direct_results = gmaps.geocode("서울, 대한민국", language='ko')
                print(f"   ✅ 직접 호출 결과: {len(direct_results)}개")
                if direct_results:
                    print(f"   첫 번째 결과: {direct_results[0].get('formatted_address', 'N/A')}")
                else:
                    print("   ⚠️ 직접 호출도 결과가 없습니다")
            except Exception as e:
                print(f"   💥 직접 호출 실패: {e}")
        else:
            print("   ❌ 사용할 API 키가 없습니다")
        
    except Exception as e:
        print(f"💥 전체 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n🕐 테스트 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(test_geocoding_backend())