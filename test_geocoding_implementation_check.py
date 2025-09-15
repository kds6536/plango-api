#!/usr/bin/env python3
"""
현재 Railway에서 실행되는 Geocoding 구현 확인
"""

import os
import sys
import asyncio
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def check_geocoding_implementation():
    """현재 Geocoding 구현 방식 확인"""
    
    print(f"🕐 Geocoding 구현 확인 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 현재 Geocoding 서비스 파일 내용 확인
        print("\n📄 Geocoding 서비스 파일 분석")
        print("=" * 50)
        
        geocoding_file = "app/services/geocoding_service.py"
        if os.path.exists(geocoding_file):
            with open(geocoding_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            print(f"파일 크기: {len(content)} 문자")
            
            # aiohttp 사용 여부 확인
            if "aiohttp" in content:
                print("✅ aiohttp 기반 구현 발견")
            else:
                print("❌ aiohttp 기반 구현 없음")
            
            # googlemaps 라이브러리 사용 여부 확인
            if "googlemaps" in content:
                print("✅ googlemaps 라이브러리 사용")
            else:
                print("❌ googlemaps 라이브러리 미사용")
            
            # get_geocode_results 메서드 확인
            if "get_geocode_results" in content:
                print("✅ get_geocode_results 메서드 존재")
                
                # 메서드 구현 방식 확인
                lines = content.split('\n')
                in_method = False
                method_lines = []
                
                for line in lines:
                    if "async def get_geocode_results" in line:
                        in_method = True
                        method_lines.append(line.strip())
                    elif in_method:
                        if line.strip().startswith("def ") or line.strip().startswith("async def "):
                            break
                        method_lines.append(line.strip())
                        if len(method_lines) > 20:  # 처음 20줄만
                            break
                
                print("\n메서드 구현 (처음 20줄):")
                for i, line in enumerate(method_lines[:20]):
                    print(f"  {i+1:2d}: {line}")
            else:
                print("❌ get_geocode_results 메서드 없음")
        
        # 2. 실제 서비스 인스턴스 생성 및 테스트
        print("\n🔧 실제 서비스 인스턴스 테스트")
        print("=" * 50)
        
        from app.services.geocoding_service import GeocodingService
        
        # 서비스 인스턴스 생성
        service = GeocodingService()
        
        print(f"API 키 존재: {'예' if service.api_key else '아니오'}")
        print(f"Google Maps 클라이언트 존재: {'예' if service.gmaps else '아니오'}")
        
        # 메서드 존재 여부 확인
        has_get_geocode_results = hasattr(service, 'get_geocode_results')
        print(f"get_geocode_results 메서드: {'존재' if has_get_geocode_results else '없음'}")
        
        if has_get_geocode_results:
            import inspect
            method = getattr(service, 'get_geocode_results')
            is_async = inspect.iscoroutinefunction(method)
            print(f"메서드 타입: {'async' if is_async else 'sync'}")
        
        # 3. 실제 API 호출 테스트 (간단한 케이스)
        print("\n🌍 실제 API 호출 테스트")
        print("=" * 50)
        
        if has_get_geocode_results and service.api_key:
            try:
                print("서울 테스트 시작...")
                result = await service.get_geocode_results("서울")
                print(f"✅ 성공: {len(result)}개 결과")
            except Exception as e:
                print(f"💥 실패: {e}")
                
                # 에러 타입 확인
                error_type = type(e).__name__
                error_msg = str(e)
                print(f"에러 타입: {error_type}")
                print(f"에러 메시지: {error_msg}")
                
                # REQUEST_DENIED 에러인지 확인
                if "REQUEST_DENIED" in error_msg:
                    print("🚨 REQUEST_DENIED 에러 - API 키 제한 문제")
                    if "referer restrictions" in error_msg:
                        print("🚨 Referer 제한 문제")
                    elif "IP restrictions" in error_msg:
                        print("🚨 IP 제한 문제")
        
        # 4. 환경 변수 재확인
        print("\n🔑 환경 변수 상세 확인")
        print("=" * 50)
        
        from app.config import settings
        
        # 모든 관련 환경 변수 확인
        env_vars = [
            "MAPS_PLATFORM_API_KEY_BACKEND",
            "GOOGLE_MAPS_API_KEY", 
            "GOOGLE_MAPS_UNRESTRICTED_KEY"
        ]
        
        for var in env_vars:
            value = getattr(settings, var, None) or os.getenv(var)
            if value:
                print(f"{var}: {value[:20]}... (길이: {len(value)})")
            else:
                print(f"{var}: 없음")
        
    except Exception as e:
        print(f"💥 전체 확인 실패: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n🕐 확인 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(check_geocoding_implementation())