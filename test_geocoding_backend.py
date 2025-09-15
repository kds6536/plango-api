#!/usr/bin/env python3
"""
백엔드에서 직접 Geocoding API 연결 테스트
"""

import asyncio
import os
from app.services.geocoding_service import GeocodingService
from app.services.api_key_manager import api_key_manager

async def test_geocoding_backend():
    print("🔧 백엔드 Geocoding 연결 테스트 시작")
    print("=" * 50)
    
    # API 키 상태 확인
    print("🔑 API 키 상태 확인:")
    print(f"  - Backend Key: {'있음' if api_key_manager.backend_key else '없음'}")
    print(f"  - Frontend Key: {'있음' if api_key_manager.frontend_key else '없음'}")
    print(f"  - Unrestricted Key: {'있음' if api_key_manager.unrestricted_key else '없음'}")
    
    if api_key_manager.backend_key:
        print(f"  - Backend Key 앞 20자: {api_key_manager.backend_key[:20]}...")
    
    print()
    
    # Geocoding 서비스 초기화 테스트
    print("🌍 Geocoding 서비스 초기화 테스트:")
    try:
        geocoding_service = GeocodingService()
        print("✅ Geocoding 서비스 초기화 성공")
        
        if geocoding_service.gmaps:
            print("✅ Google Maps 클라이언트 초기화 성공")
        else:
            print("❌ Google Maps 클라이언트 초기화 실패")
            return
            
    except Exception as e:
        print(f"❌ Geocoding 서비스 초기화 실패: {e}")
        return
    
    print()
    
    # 실제 API 호출 테스트
    test_queries = ["서울", "부산", "광주", "존재하지않는도시123"]
    
    for query in test_queries:
        print(f"🧪 '{query}' 테스트:")
        try:
            results = await geocoding_service.get_geocode_results(query)
            print(f"  ✅ 성공: {len(results)}개 결과")
            
            for i, result in enumerate(results[:2]):  # 최대 2개만 표시
                print(f"    {i+1}. {result.get('formatted_address', 'N/A')}")
                
        except Exception as e:
            print(f"  ❌ 실패: {e}")
        
        print()
    
    print("🔧 백엔드 Geocoding 연결 테스트 완료")

if __name__ == "__main__":
    asyncio.run(test_geocoding_backend())