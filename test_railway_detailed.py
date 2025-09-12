#!/usr/bin/env python3
"""
Railway 백엔드 상세 테스트
"""
import requests
import json
from datetime import datetime

# Railway 백엔드 URL
RAILWAY_URL = "https://plango-api-production.up.railway.app"

def test_detailed_error():
    """상세한 에러 정보 확인"""
    print("🔍 상세 에러 분석")
    print("=" * 50)
    
    test_data = {
        "country": "대한민국",
        "city": "서울",
        "total_duration": 1,
        "travelers_count": 1,
        "budget_level": "중간",
        "travel_style": "관광"
    }
    
    try:
        print("📍 서울 테스트 (상세 에러 확인)...")
        response = requests.post(
            f"{RAILWAY_URL}/api/v1/place-recommendations/generate",
            json=test_data,
            timeout=30
        )
        
        print(f"   상태 코드: {response.status_code}")
        print(f"   응답 헤더: {dict(response.headers)}")
        
        if response.text:
            print(f"   응답 내용: {response.text}")
        
        if response.status_code == 500:
            try:
                error_data = response.json()
                print(f"   에러 상세: {json.dumps(error_data, ensure_ascii=False, indent=2)}")
            except:
                print(f"   에러 텍스트: {response.text}")
                
    except Exception as e:
        print(f"   💥 테스트 예외: {e}")

def test_health_endpoints():
    """헬스체크 엔드포인트들 테스트"""
    print("\n🏥 헬스체크 엔드포인트 테스트")
    print("=" * 50)
    
    endpoints = [
        "/api/v1/health",
        "/api/v1/health/memory", 
        "/api/v1/health/deep",
        "/api/v1/place-recommendations/health"
    ]
    
    for endpoint in endpoints:
        try:
            print(f"\n📍 테스트: {endpoint}")
            response = requests.get(f"{RAILWAY_URL}{endpoint}", timeout=10)
            print(f"   상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   ✅ 성공: {data}")
                except:
                    print(f"   ✅ 성공: {response.text[:100]}...")
            else:
                print(f"   ❌ 실패: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   💥 예외: {e}")

if __name__ == "__main__":
    print(f"🕐 상세 테스트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 대상 서버: {RAILWAY_URL}")
    print()
    
    test_health_endpoints()
    test_detailed_error()
    
    print(f"\n🕐 테스트 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")