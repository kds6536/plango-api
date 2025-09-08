#!/usr/bin/env python3
"""API 키 설정 상태 확인 스크립트"""

import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

print("=== 환경 변수 직접 확인 ===")
print(f"MAPS_PLATFORM_API_KEY_BACKEND: {os.getenv('MAPS_PLATFORM_API_KEY_BACKEND', 'NOT_FOUND')}")
print(f"GOOGLE_MAPS_API_KEY: {os.getenv('GOOGLE_MAPS_API_KEY', 'NOT_FOUND')}")
print(f"MAPS_PLATFORM_API_KEY: {os.getenv('MAPS_PLATFORM_API_KEY', 'NOT_FOUND')}")
print(f"MAPS_PLATFORM_API_KEY_BACKEND: {os.getenv('MAPS_PLATFORM_API_KEY_BACKEND', 'NOT_FOUND')}")

print("\n=== Settings 객체를 통한 확인 ===")
try:
    from app.config import settings
    print(f"settings.MAPS_PLATFORM_API_KEY_BACKEND: {getattr(settings, 'MAPS_PLATFORM_API_KEY_BACKEND', 'NOT_FOUND')}")
    print(f"settings.GOOGLE_MAPS_API_KEY: {getattr(settings, 'GOOGLE_MAPS_API_KEY', 'NOT_FOUND')}")
    print(f"settings.MAPS_PLATFORM_API_KEY: {getattr(settings, 'MAPS_PLATFORM_API_KEY', 'NOT_FOUND')}")
    print(f"settings.MAPS_PLATFORM_API_KEY_BACKEND: {getattr(settings, 'MAPS_PLATFORM_API_KEY_BACKEND', 'NOT_FOUND')}")
except Exception as e:
    print(f"Settings 로드 실패: {e}")

print("\n=== Google Places Service 초기화 테스트 ===")
try:
    from app.services.google_places_service import GooglePlacesService
    service = GooglePlacesService()
    print(f"GooglePlacesService API Key: {service.api_key[:20] if service.api_key else 'None'}...")
    print(f"GooglePlacesService gmaps client: {'Initialized' if service.gmaps else 'Not Initialized'}")
except Exception as e:
    print(f"GooglePlacesService 초기화 실패: {e}")