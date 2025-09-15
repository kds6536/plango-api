#!/usr/bin/env python3
"""
Geocoding API 직접 테스트 - 실패 원인 파악
"""

import requests
import os
import json
from datetime import datetime

def test_geocoding_api():
    """Railway에서 Geocoding API 직접 테스트"""
    
    print(f"🕐 Geocoding 디버그 테스트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 대상 서버: https://plango-api-production.up.railway.app")
    
    # 1. 간단한 서울 테스트
    print("\n🏙️ 서울 Geocoding 테스트")
    print("=" * 50)
    
    try:
        url = "https://plango-api-production.up.railway.app/api/v1/place-recommendations/generate"
        
        payload = {
            "city": "서울",
            "country": "대한민국",
            "total_duration": 1,
            "travelers_count": 2,
            "travel_style": "관광",
            "budget_level": "중간"
        }
        
        print(f"📡 요청 데이터: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        response = requests.post(url, json=payload, timeout=60)
        
        print(f"   상태 코드: {response.status_code}")
        print(f"   응답 헤더: {dict(response.headers)}")
        
        if response.status_code == 500:
            print("   ✅ 500 에러 - 예상된 결과 (Geocoding 실패)")
            try:
                error_data = response.json()
                print(f"   에러 데이터: {json.dumps(error_data, ensure_ascii=False, indent=2)}")
            except:
                print(f"   에러 텍스트: {response.text}")
        else:
            print(f"   예상치 못한 상태 코드: {response.status_code}")
            print(f"   응답: {response.text}")
            
    except Exception as e:
        print(f"   💥 테스트 예외: {e}")
    
    # 2. 존재하지 않는 도시 테스트
    print("\n🚫 존재하지 않는 도시 테스트")
    print("=" * 50)
    
    try:
        payload = {
            "city": "asdfasdf",
            "country": "대한민국", 
            "total_duration": 1,
            "travelers_count": 2,
            "travel_style": "관광",
            "budget_level": "중간"
        }
        
        print(f"📡 요청 데이터: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        response = requests.post(url, json=payload, timeout=60)
        
        print(f"   상태 코드: {response.status_code}")
        
        if response.status_code == 400:
            print("   ✅ 400 에러 - 사용자 입력 오류로 처리됨")
            try:
                error_data = response.json()
                print(f"   에러 데이터: {json.dumps(error_data, ensure_ascii=False, indent=2)}")
            except:
                print(f"   에러 텍스트: {response.text}")
        elif response.status_code == 500:
            print("   ⚠️ 500 에러 - 시스템 오류로 처리됨")
            try:
                error_data = response.json()
                print(f"   에러 데이터: {json.dumps(error_data, ensure_ascii=False, indent=2)}")
            except:
                print(f"   에러 텍스트: {response.text}")
        else:
            print(f"   예상치 못한 상태 코드: {response.status_code}")
            print(f"   응답: {response.text}")
            
    except Exception as e:
        print(f"   💥 테스트 예외: {e}")
    
    print(f"\n🕐 테스트 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    test_geocoding_api()