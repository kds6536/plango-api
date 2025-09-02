#!/usr/bin/env python3
"""
Plango API 외부 서비스 연결 진단 스크립트

이 스크립트는 Supabase와 Google Places API 연결 상태를 각각 독립적으로 테스트하여
어느 부분에서 연결이 실패하는지 정확히 진단합니다.

사용법: python diagnose_connections.py
"""

import asyncio
import sys
import os
from typing import Dict, Any

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.config import settings
    from supabase import create_client
    import httpx
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("필요한 패키지가 설치되지 않았거나 app.config 모듈을 찾을 수 없습니다.")
    sys.exit(1)


async def test_supabase_connection() -> Dict[str, Any]:
    """
    Supabase 연결 상태를 테스트합니다.
    
    Returns:
        Dict[str, Any]: 테스트 결과 정보
    """
    print("\n🔍 Supabase 연결 테스트 시작...")
    
    try:
        # 환경변수 확인
        supabase_url = settings.SUPABASE_URL
        supabase_key = settings.SUPABASE_KEY
        
        if not supabase_url or not supabase_key:
            return {
                "success": False,
                "error": "SUPABASE_URL 또는 SUPABASE_KEY 환경변수가 설정되지 않았습니다.",
                "supabase_url_exists": bool(supabase_url),
                "supabase_key_exists": bool(supabase_key)
            }
        
        print(f"   📍 SUPABASE_URL: {supabase_url[:50]}...")
        print(f"   🔑 SUPABASE_KEY: {supabase_key[:20]}...{supabase_key[-10:]}")
        
        # Supabase 클라이언트 초기화
        supabase = create_client(supabase_url, supabase_key)
        
        # 간단한 쿼리 테스트 - settings 테이블에서 데이터 1개 조회
        print("   🔍 settings 테이블 조회 테스트 중...")
        response = supabase.table('settings').select('*').limit(1).execute()
        
        if response.data is not None:
            print("✅ Supabase Connection: SUCCESS! Fetched data successfully.")
            print(f"   📊 조회된 데이터 수: {len(response.data)}")
            return {
                "success": True,
                "data_count": len(response.data),
                "supabase_url": supabase_url,
                "connection_type": "settings_table"
            }
        else:
            return {
                "success": False,
                "error": "Supabase 응답에서 데이터가 None입니다.",
                "response": str(response)
            }
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Supabase Connection: FAILED. Error: {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "error_type": type(e).__name__
        }


async def test_google_places_connection() -> Dict[str, Any]:
    """
    Google Places API 연결 상태를 테스트합니다.
    
    Returns:
        Dict[str, Any]: 테스트 결과 정보
    """
    print("\n🔍 Google Places API 연결 테스트 시작...")
    
    try:
        # 환경변수 확인 (올바른 환경변수명 사용)
        google_api_key = settings.MAPS_PLATFORM_API_KEY_BACKEND
        
        if not google_api_key:
            return {
                "success": False,
                "error": "MAPS_PLATFORM_API_KEY_BACKEND 환경변수가 설정되지 않았습니다.",
                "api_key_exists": False
            }
        
        print(f"   🔑 MAPS_PLATFORM_API_KEY_BACKEND: {google_api_key[:20]}...{google_api_key[-10:]}")
        
        # Google Places API (New) Text Search 테스트
        url = f"https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": google_api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.rating"
        }
        data = {
            "textQuery": "Eiffel Tower, Paris"
        }
        
        print("   🌐 Google Places API 요청 전송 중...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=data)
            
            print(f"   📡 HTTP 상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Places API (New) 응답 형식 확인
                places = response_data.get('places', [])
                
                if len(places) > 0:
                    print("✅ Google Places API Connection: SUCCESS! Received a valid response.")
                    print(f"   📊 검색 결과 수: {len(places)}")
                    first_place = places[0]
                    first_name = first_place.get('displayName', {}).get('text', 'Unknown')
                    print(f"   🏛️ 첫 번째 결과: {first_name}")
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "api_version": "Places API (New)",
                        "results_count": len(places),
                        "first_result": first_name
                    }
                else:
                    error = response_data.get('error', {})
                    error_message = error.get('message', '상세 오류 정보 없음')
                    error_code = error.get('code', 'UNKNOWN')
                    print(f"❌ Google Places API Error Code: {error_code}")
                    print(f"   🔍 Error Message: {error_message}")
                    return {
                        "success": False,
                        "error": f"Google API 오류 발생. Code: {error_code}",
                        "status_code": response.status_code,
                        "error_code": error_code,
                        "error_message": error_message,
                        "response_data": response_data
                    }
            else:
                response_text = response.text[:500]  # 처음 500자만 출력
                print(f"❌ Google Places API Connection: FAILED. Status Code: {response.status_code}, Response: {response_text}")
                return {
                    "success": False,
                    "error": f"HTTP 상태 코드 {response.status_code}",
                    "status_code": response.status_code,
                    "response_text": response_text
                }
                
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Google Places API Connection: FAILED. Error: {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "error_type": type(e).__name__
        }


async def test_v6_schema_tables() -> Dict[str, Any]:
    """
    v6.0 새로운 데이터베이스 스키마 테이블 존재 여부를 테스트합니다.
    
    Returns:
        Dict[str, Any]: 테스트 결과 정보
    """
    print("\n🔍 v6.0 데이터베이스 스키마 테스트 시작...")
    
    try:
        # 환경변수 확인
        supabase_url = settings.SUPABASE_URL
        supabase_key = settings.SUPABASE_KEY
        
        if not supabase_url or not supabase_key:
            return {
                "success": False,
                "error": "Supabase 환경변수가 설정되지 않았습니다."
            }
        
        # Supabase 클라이언트 초기화
        supabase = create_client(supabase_url, supabase_key)
        
        # v6.0 테이블들 확인
        v6_tables = ['countries', 'cities', 'cached_places', 'prompts']
        table_status = {}
        
        for table_name in v6_tables:
            try:
                print(f"   🔍 {table_name} 테이블 확인 중...")
                response = supabase.table(table_name).select('*').limit(1).execute()
                
                if response.data is not None:
                    table_status[table_name] = {
                        "exists": True,
                        "record_count": len(response.data)
                    }
                    print(f"   ✅ {table_name}: 존재함 (데이터 {len(response.data)}개)")
                else:
                    table_status[table_name] = {
                        "exists": False,
                        "error": "데이터가 None"
                    }
                    print(f"   ❌ {table_name}: 데이터 없음")
                    
            except Exception as e:
                table_status[table_name] = {
                    "exists": False,
                    "error": str(e)
                }
                print(f"   ❌ {table_name}: 오류 - {str(e)}")
        
        # 모든 테이블이 존재하는지 확인
        all_exist = all(status.get("exists", False) for status in table_status.values())
        
        if all_exist:
            print("✅ v6.0 Database Schema: SUCCESS! 모든 필수 테이블이 존재합니다.")
        else:
            print("❌ v6.0 Database Schema: INCOMPLETE! 일부 테이블이 누락되었습니다.")
        
        return {
            "success": all_exist,
            "table_status": table_status,
            "missing_tables": [name for name, status in table_status.items() if not status.get("exists", False)]
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ v6.0 Database Schema: FAILED. Error: {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "error_type": type(e).__name__
        }


async def main():
    """
    메인 진단 함수 - 모든 연결 테스트를 순서대로 실행합니다.
    """
    print("🚀 Plango API 외부 서비스 연결 진단 시작")
    print("=" * 60)
    
    # 환경변수 기본 정보 출력
    print(f"📍 현재 작업 디렉토리: {os.getcwd()}")
    print(f"🐍 Python 버전: {sys.version}")
    
    # 테스트 결과 저장
    results = {}
    
    # 1. Supabase 연결 테스트
    results["supabase"] = await test_supabase_connection()
    
    # 2. Google Places API 연결 테스트
    results["google_places"] = await test_google_places_connection()
    
    # 3. v6.0 데이터베이스 스키마 테스트 (Supabase 연결이 성공한 경우에만)
    if results["supabase"]["success"]:
        results["v6_schema"] = await test_v6_schema_tables()
    else:
        print("\n⚠️  Supabase 연결이 실패하여 v6.0 스키마 테스트를 건너뜁니다.")
        results["v6_schema"] = {"success": False, "error": "Supabase 연결 실패로 테스트 불가"}
    
    # 종합 결과 출력
    print("\n" + "=" * 60)
    print("📋 진단 결과 요약")
    print("=" * 60)
    
    supabase_status = "✅ 정상" if results["supabase"]["success"] else "❌ 실패"
    google_status = "✅ 정상" if results["google_places"]["success"] else "❌ 실패"
    schema_status = "✅ 정상" if results["v6_schema"]["success"] else "❌ 실패"
    
    print(f"🗄️  Supabase 연결: {supabase_status}")
    print(f"🌐 Google Places API: {google_status}")
    print(f"📊 v6.0 데이터베이스 스키마: {schema_status}")
    
    # 실패한 항목들의 원인 출력
    if not results["supabase"]["success"]:
        print(f"\n🔍 Supabase 실패 원인: {results['supabase']['error']}")
    
    if not results["google_places"]["success"]:
        print(f"\n🔍 Google Places API 실패 원인: {results['google_places']['error']}")
    
    if not results["v6_schema"]["success"]:
        print(f"\n🔍 v6.0 스키마 실패 원인: {results['v6_schema']['error']}")
        if "missing_tables" in results["v6_schema"]:
            missing = results["v6_schema"]["missing_tables"]
            if missing:
                print(f"   누락된 테이블: {', '.join(missing)}")
    
    # 권장 해결 방안 제시
    print("\n" + "=" * 60)
    print("💡 권장 해결 방안")
    print("=" * 60)
    
    if not results["supabase"]["success"]:
        print("1. Railway 환경변수에서 SUPABASE_URL과 SUPABASE_KEY 확인")
        print("2. Supabase 프로젝트가 활성화되어 있는지 확인")
        print("3. Supabase API 키 권한 확인")
    
    if not results["google_places"]["success"]:
        print("1. Railway 환경변수에서 MAPS_PLATFORM_API_KEY_BACKEND 확인")
        print("2. Google Cloud Console에서 Places API 활성화 확인")
        print("3. API 키 사용량 한도 확인")
    
    if not results["v6_schema"]["success"] and results["supabase"]["success"]:
        print("1. setup_new_schema.sql 스크립트를 Supabase에서 실행")
        print("2. 필요한 테이블과 초기 데이터 생성")
    
    print("\n🏁 진단 완료!")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())