#!/usr/bin/env python3
"""
Railway 백엔드 엔드포인트 확인
"""
import requests
import json
from datetime import datetime

# Railway 백엔드 URL
RAILWAY_URL = "https://plango-api-production.up.railway.app"

def test_available_endpoints():
    """사용 가능한 엔드포인트 확인"""
    print("🔍 Railway 엔드포인트 확인")
    print("=" * 50)
    
    endpoints_to_test = [
        "/",
        "/health",
        "/api/v1/place-recommendations/health",
        "/docs",
        "/openapi.json"
    ]
    
    for endpoint in endpoints_to_test:
        try:
            print(f"\n📍 테스트: {endpoint}")
            response = requests.get(f"{RAILWAY_URL}{endpoint}", timeout=10)
            print(f"   상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ 접속 성공")
                if endpoint == "/":
                    try:
                        data = response.json()
                        print(f"   응답: {data}")
                    except:
                        print(f"   응답: {response.text[:100]}...")
                elif endpoint == "/openapi.json":
                    try:
                        data = response.json()
                        print(f"   API 제목: {data.get('info', {}).get('title', 'N/A')}")
                        print(f"   API 버전: {data.get('info', {}).get('version', 'N/A')}")
                        if 'paths' in data:
                            paths = list(data['paths'].keys())[:5]  # 처음 5개만
                            print(f"   사용 가능한 경로 (일부): {paths}")
                    except:
                        print(f"   OpenAPI 스키마 파싱 실패")
            else:
                print(f"   ❌ 접속 실패: {response.status_code}")
                
        except Exception as e:
            print(f"   💥 예외: {e}")

def test_simple_request():
    """간단한 요청 테스트"""
    print("\n🧪 간단한 API 요청 테스트")
    print("=" * 50)
    
    # 가장 간단한 요청으로 테스트
    test_data = {
        "country": "대한민국",
        "city": "서울",
        "total_duration": 1,
        "travelers_count": 1,
        "budget_level": "중간",
        "travel_style": "관광"
    }
    
    try:
        print("📍 간단한 서울 추천 요청...")
        response = requests.post(
            f"{RAILWAY_URL}/api/v1/place-recommendations/generate",
            json=test_data,
            timeout=60  # 타임아웃 늘림
        )
        
        print(f"   상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ 추천 생성 성공!")
            data = response.json()
            print(f"   신규 추천 수: {data.get('newly_recommended_count', 'N/A')}")
        elif response.status_code == 400:
            print("   ⚠️ 400 응답 (동명 지역 또는 검증 오류)")
            try:
                data = response.json()
                print(f"   응답: {json.dumps(data, ensure_ascii=False, indent=2)}")
            except:
                print(f"   응답 텍스트: {response.text}")
        else:
            print(f"   ❌ 예상과 다른 상태 코드: {response.status_code}")
            print(f"   응답: {response.text[:200]}...")
            
    except Exception as e:
        print(f"   💥 간단한 요청 예외: {e}")

if __name__ == "__main__":
    print(f"🕐 테스트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 대상 서버: {RAILWAY_URL}")
    print()
    
    test_available_endpoints()
    test_simple_request()
    
    print(f"\n🕐 테스트 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")