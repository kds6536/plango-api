#!/usr/bin/env python3
"""실제 사용되는 API 키 디버깅"""

import os
import asyncio
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

async def debug_api_key_usage():
    """실제 사용되는 API 키와 호출 과정 디버깅"""
    
    print("=== 환경 변수 상태 ===")
    backend_key = os.getenv('MAPS_PLATFORM_API_KEY_BACKEND')
    frontend_key = os.getenv('MAPS_PLATFORM_API_KEY')
    google_key = os.getenv('GOOGLE_MAPS_API_KEY')
    
    print(f"MAPS_PLATFORM_API_KEY_BACKEND: {backend_key[:20] if backend_key else 'None'}...{backend_key[-10:] if backend_key else ''}")
    print(f"MAPS_PLATFORM_API_KEY: {frontend_key[:20] if frontend_key else 'None'}...{frontend_key[-10:] if frontend_key else ''}")
    print(f"GOOGLE_MAPS_API_KEY: {google_key[:20] if google_key else 'None'}...{google_key[-10:] if google_key else ''}")
    
    print(f"\n키 값 비교:")
    print(f"BACKEND == FRONTEND: {backend_key == frontend_key if backend_key and frontend_key else 'N/A'}")
    print(f"BACKEND == GOOGLE: {backend_key == google_key if backend_key and google_key else 'N/A'}")
    
    print("\n=== Google Places Service 초기화 과정 ===")
    try:
        from app.services.google_places_service import GooglePlacesService
        from app.config import settings
        
        # Settings에서 실제 값 확인
        print(f"settings.MAPS_PLATFORM_API_KEY_BACKEND: {getattr(settings, 'MAPS_PLATFORM_API_KEY_BACKEND', 'NOT_FOUND')[:20] if getattr(settings, 'MAPS_PLATFORM_API_KEY_BACKEND', None) else 'None'}...")
        print(f"settings.GOOGLE_MAPS_API_KEY: {getattr(settings, 'GOOGLE_MAPS_API_KEY', 'NOT_FOUND')[:20] if getattr(settings, 'GOOGLE_MAPS_API_KEY', None) else 'None'}...")
        
        # 서비스 초기화
        service = GooglePlacesService()
        actual_key = service.api_key
        print(f"실제 사용되는 키: {actual_key[:20] if actual_key else 'None'}...{actual_key[-10:] if actual_key else ''}")
        
        # 키 매칭 확인
        if actual_key == backend_key:
            print("✅ BACKEND 키 사용 중")
        elif actual_key == frontend_key:
            print("❌ FRONTEND 키 사용 중 (문제!)")
        elif actual_key == google_key:
            print("⚠️ GOOGLE_MAPS_API_KEY 사용 중")
        else:
            print("❓ 알 수 없는 키 사용 중")
            
        print(f"Google Maps Client 초기화: {'성공' if service.gmaps else '실패'}")
        
    except Exception as e:
        print(f"서비스 초기화 실패: {e}")
        import traceback
        print(traceback.format_exc())

    print("\n=== 실제 API 호출 테스트 ===")
    try:
        from app.services.google_places_service import GooglePlacesService
        import httpx
        
        service = GooglePlacesService()
        if not service.api_key:
            print("❌ API 키가 없습니다")
            return
            
        # 직접 HTTP 요청으로 테스트
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": service.api_key,
            "X-Goog-FieldMask": "places.id,places.displayName"
        }
        data = {"textQuery": "Seoul", "languageCode": "ko"}
        
        print(f"요청 URL: {url}")
        print(f"사용 키: {service.api_key[:20]}...{service.api_key[-10:]}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, json=data)
            print(f"응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                places_count = len(result.get('places', []))
                print(f"✅ 성공: {places_count}개 장소 발견")
            else:
                print(f"❌ 실패: {response.text}")
                
    except Exception as e:
        print(f"API 호출 테스트 실패: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(debug_api_key_usage())