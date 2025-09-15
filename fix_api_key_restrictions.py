#!/usr/bin/env python3
"""
API 키 제한 문제 해결을 위한 스크립트
"""

import os

def check_api_keys():
    print("🔑 현재 API 키 상태:")
    
    backend_key = os.getenv("MAPS_PLATFORM_API_KEY_BACKEND")
    frontend_key = os.getenv("GOOGLE_MAPS_API_KEY") 
    unrestricted_key = os.getenv("GOOGLE_MAPS_UNRESTRICTED_KEY")
    
    print(f"  - MAPS_PLATFORM_API_KEY_BACKEND: {'있음' if backend_key else '없음'}")
    print(f"  - GOOGLE_MAPS_API_KEY: {'있음' if frontend_key else '없음'}")
    print(f"  - GOOGLE_MAPS_UNRESTRICTED_KEY: {'있음' if unrestricted_key else '없음'}")
    
    if backend_key:
        print(f"  - Backend Key 앞 20자: {backend_key[:20]}...")
    if frontend_key:
        print(f"  - Frontend Key 앞 20자: {frontend_key[:20]}...")
    if unrestricted_key:
        print(f"  - Unrestricted Key 앞 20자: {unrestricted_key[:20]}...")
    
    print("\n🚨 문제: 현재 키에 Referer 제한이 있어서 서버에서 사용할 수 없습니다.")
    print("\n💡 해결 방안:")
    print("1. Google Cloud Console에서 새로운 API 키 생성")
    print("2. 새 키에는 IP 제한만 설정 (Referer 제한 제거)")
    print("3. GOOGLE_MAPS_UNRESTRICTED_KEY 환경변수로 설정")
    print("4. 또는 기존 키의 제한을 IP 제한으로 변경")

if __name__ == "__main__":
    check_api_keys()