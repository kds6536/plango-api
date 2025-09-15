#!/usr/bin/env python3
"""
Railway 환경에서 실제 환경 변수 확인
"""

import requests
import json
from datetime import datetime

def test_railway_environment():
    """Railway 환경의 환경 변수 및 API 키 확인"""
    
    print(f"🕐 Railway 환경 확인 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 대상 서버: https://plango-api-production.up.railway.app")
    
    try:
        # Railway에 환경 변수 확인 엔드포인트 요청
        url = "https://plango-api-production.up.railway.app/api/v1/diagnosis/environment"
        
        print(f"\n📡 환경 변수 확인 요청...")
        
        response = requests.get(url, timeout=30)
        
        print(f"   상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("   ✅ 환경 변수 정보 수신 성공")
                print(f"   응답 데이터: {json.dumps(data, ensure_ascii=False, indent=2)}")
            except:
                print(f"   응답 텍스트: {response.text}")
        else:
            print(f"   ❌ 요청 실패")
            print(f"   응답: {response.text}")
            
    except Exception as e:
        print(f"   💥 테스트 예외: {e}")
    
    # Geocoding 직접 테스트도 시도
    try:
        print(f"\n🌍 Railway Geocoding 직접 테스트...")
        
        url = "https://plango-api-production.up.railway.app/api/v1/diagnosis/geocoding-test"
        
        response = requests.get(url, timeout=30)
        
        print(f"   상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("   ✅ Geocoding 테스트 성공")
                print(f"   응답 데이터: {json.dumps(data, ensure_ascii=False, indent=2)}")
            except:
                print(f"   응답 텍스트: {response.text}")
        else:
            print(f"   ❌ Geocoding 테스트 실패")
            print(f"   응답: {response.text}")
            
    except Exception as e:
        print(f"   💥 Geocoding 테스트 예외: {e}")
    
    print(f"\n🕐 테스트 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    test_railway_environment()