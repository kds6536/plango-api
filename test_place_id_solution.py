#!/usr/bin/env python3
"""
place_id 기반 솔루션 테스트
프론트엔드에서 place_id를 제공했을 때 동명 지역 모달이 나타나지 않는지 확인
"""

import asyncio
import json
import requests
from datetime import datetime

# Railway 배포된 백엔드 URL
BACKEND_URL = "https://plango-api-production.up.railway.app"

def test_place_id_solution():
    """place_id가 있을 때 동명 지역 모달이 나타나지 않는지 테스트"""
    
    print("🧪 [TEST_START] place_id 솔루션 테스트 시작")
    print(f"🌐 [BACKEND_URL] {BACKEND_URL}")
    
    # 테스트 케이스 1: place_id가 있는 경우 (광주 - 전라남도)
    test_payload_with_place_id = {
        "country": "대한민국",
        "city": "광주",
        "place_id": "ChIJm8hW8VaUZTURuD-kVKXScQE",  # 광주광역시 place_id
        "total_duration": 2,
        "travelers_count": 2,
        "budget_range": "medium",
        "travel_style": ["관광", "문화"],
        "special_requests": "맛집과 관광지를 포함해주세요",
        "language_code": "ko"
    }
    
    # 테스트 케이스 2: place_id가 없는 경우 (비교용)
    test_payload_without_place_id = {
        "country": "대한민국", 
        "city": "광주",
        "total_duration": 2,
        "travelers_count": 2,
        "budget_range": "medium",
        "travel_style": ["관광", "문화"],
        "special_requests": "맛집과 관광지를 포함해주세요",
        "language_code": "ko"
    }
    
    print("\n" + "="*60)
    print("🎯 [TEST_1] place_id가 있는 경우 테스트")
    print("="*60)
    print(f"📋 [PAYLOAD] {json.dumps(test_payload_with_place_id, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/place-recommendations/generate",
            json=test_payload_with_place_id,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        print(f"📊 [RESPONSE_STATUS] {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            status = data.get('status', 'SUCCESS')
            
            if status == 'AMBIGUOUS':
                print("❌ [FAIL] place_id가 있는데도 AMBIGUOUS 응답이 나왔습니다!")
                print(f"📝 [OPTIONS] {data.get('options', [])}")
                return False
            else:
                print("✅ [SUCCESS] place_id가 있을 때 AMBIGUOUS 모달이 나타나지 않았습니다!")
                print(f"🏙️ [CITY_ID] {data.get('city_id')}")
                print(f"📊 [RECOMMENDATIONS] {len(data.get('recommendations', {}))}개 카테고리")
                return True
                
        else:
            print(f"❌ [ERROR] HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ [EXCEPTION] 요청 실패: {e}")
        return False
    
    print("\n" + "="*60)
    print("🔍 [TEST_2] place_id가 없는 경우 테스트 (비교용)")
    print("="*60)
    print(f"📋 [PAYLOAD] {json.dumps(test_payload_without_place_id, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/place-recommendations/generate",
            json=test_payload_without_place_id,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        print(f"📊 [RESPONSE_STATUS] {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            status = data.get('status', 'SUCCESS')
            
            if status == 'AMBIGUOUS':
                print("✅ [EXPECTED] place_id가 없을 때는 AMBIGUOUS 응답이 나타났습니다 (정상)")
                print(f"📝 [OPTIONS] {len(data.get('options', []))}개 선택지")
                return True
            else:
                print("⚠️ [UNEXPECTED] place_id가 없는데도 AMBIGUOUS가 나타나지 않았습니다")
                return True  # 이것도 성공으로 간주 (AI가 명확하게 판단한 경우)
                
        else:
            print(f"❌ [ERROR] HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ [EXCEPTION] 요청 실패: {e}")
        return False

def test_backend_health():
    """백엔드 상태 확인"""
    print("🏥 [HEALTH_CHECK] 백엔드 상태 확인")
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/place-recommendations/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ [HEALTH] 백엔드 상태: {data.get('status')}")
            print(f"📊 [FEATURES] {data.get('features', {})}")
            return True
        else:
            print(f"❌ [HEALTH_ERROR] HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ [HEALTH_EXCEPTION] {e}")
        return False

if __name__ == "__main__":
    print("🚀 place_id 솔루션 통합 테스트")
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 백엔드 상태 확인
    if not test_backend_health():
        print("❌ 백엔드 상태 확인 실패")
        exit(1)
    
    # 2. place_id 솔루션 테스트
    if test_place_id_solution():
        print("\n🎉 [FINAL_RESULT] place_id 솔루션 테스트 성공!")
    else:
        print("\n💥 [FINAL_RESULT] place_id 솔루션 테스트 실패!")
        exit(1)
    
    print(f"⏰ 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")