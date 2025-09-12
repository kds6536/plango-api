#!/usr/bin/env python3
"""
Railway 백엔드 상태 테스트
"""
import requests
import json
from datetime import datetime

# Railway 백엔드 URL
RAILWAY_URL = "https://plango-api-production.up.railway.app"

def test_railway_health():
    """Railway 백엔드 헬스체크"""
    print("🚂 Railway 백엔드 테스트")
    print("=" * 50)
    
    try:
        # 헬스체크
        print("🏥 헬스체크 테스트...")
        response = requests.get(f"{RAILWAY_URL}/health", timeout=10)
        print(f"   상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 헬스체크 성공")
            print(f"   서비스: {data.get('service', 'N/A')}")
            print(f"   Supabase 연결: {data.get('supabase_connected', 'N/A')}")
        else:
            print(f"   ❌ 헬스체크 실패: {response.status_code}")
            
    except Exception as e:
        print(f"   💥 헬스체크 예외: {e}")
    
    try:
        # 루트 엔드포인트
        print("\n🌐 루트 엔드포인트 테스트...")
        response = requests.get(f"{RAILWAY_URL}/", timeout=10)
        print(f"   상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 루트 접속 성공")
            print(f"   메시지: {data.get('message', 'N/A')}")
        else:
            print(f"   ❌ 루트 접속 실패: {response.status_code}")
            
    except Exception as e:
        print(f"   💥 루트 테스트 예외: {e}")

def test_ambiguous_location():
    """동명 지역 감지 테스트"""
    print("\n🎯 동명 지역 감지 테스트")
    print("=" * 50)
    
    test_data = {
        "country": "대한민국",
        "city": "광주",
        "total_duration": 3,
        "travelers_count": 2,
        "budget_level": "중간",
        "travel_style": "관광"
    }
    
    try:
        print("📍 광주 동명 지역 테스트...")
        response = requests.post(
            f"{RAILWAY_URL}/api/v1/place-recommendations/generate",
            json=test_data,
            timeout=30
        )
        
        print(f"   상태 코드: {response.status_code}")
        
        if response.status_code == 400:
            data = response.json()
            if data.get("detail", {}).get("error_code") == "AMBIGUOUS_LOCATION":
                print("   ✅ 동명 지역 감지 성공!")
                options = data["detail"]["options"]
                print(f"   감지된 옵션 수: {len(options)}")
                for i, option in enumerate(options, 1):
                    print(f"   {i}. {option['display_name']} - {option['formatted_address']}")
            else:
                print(f"   ❌ 예상과 다른 400 응답: {data}")
        else:
            print(f"   ❌ 예상과 다른 상태 코드: {response.status_code}")
            if response.text:
                print(f"   응답: {response.text[:200]}...")
                
    except Exception as e:
        print(f"   💥 동명 지역 테스트 예외: {e}")

def test_normal_city():
    """일반 도시 테스트"""
    print("\n🏙️ 일반 도시 테스트 (서울)")
    print("=" * 50)
    
    test_data = {
        "country": "대한민국", 
        "city": "서울",
        "total_duration": 2,
        "travelers_count": 2,
        "budget_level": "중간",
        "travel_style": "관광"
    }
    
    try:
        print("🏙️ 서울 테스트...")
        response = requests.post(
            f"{RAILWAY_URL}/api/v1/place-recommendations/generate",
            json=test_data,
            timeout=30
        )
        
        print(f"   상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ 서울 추천 생성 성공!")
            data = response.json()
            if "recommendations" in data:
                print(f"   추천 장소 수: {len(data['recommendations'])}")
        elif response.status_code == 400:
            data = response.json()
            print(f"   ❌ 400 에러: {data}")
        else:
            print(f"   ❌ 예상과 다른 상태 코드: {response.status_code}")
            
    except Exception as e:
        print(f"   💥 서울 테스트 예외: {e}")

if __name__ == "__main__":
    print(f"🕐 테스트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 대상 서버: {RAILWAY_URL}")
    print()
    
    test_railway_health()
    test_ambiguous_location()
    test_normal_city()
    
    print(f"\n🕐 테스트 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")