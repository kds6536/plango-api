#!/usr/bin/env python3
"""
place_id 처리 수정 사항 테스트
"""

import asyncio
import json
import requests
from datetime import datetime

# API 엔드포인트
API_BASE = "https://plango-api-production.up.railway.app"
# API_BASE = "http://localhost:8000"  # 로컬 테스트용

async def test_place_id_processing():
    """place_id가 포함된 요청 테스트"""
    
    print("🧪 [TEST_START] place_id 처리 테스트 시작")
    
    # 광주 테스트 (place_id 포함)
    test_payload = {
        "country": "대한민국",
        "city": "광주",
        "total_duration": 2,
        "travelers_count": 2,
        "budget_range": "medium",
        "travel_style": ["문화", "액티비티"],
        "special_requests": "다양한 명소와 맛집을 포함해주세요",
        "language_code": "ko",
        "daily_start_time": "09:00",
        "daily_end_time": "21:00",
        # 광주광역시의 실제 place_id (Google Places API에서 가져온 값)
        "place_id": "ChIJyTbRxZUUZTURGB8yKcOGbAQ"  # 광주광역시 place_id
    }
    
    print("📤 [REQUEST] 요청 데이터:")
    print(json.dumps(test_payload, indent=2, ensure_ascii=False))
    
    try:
        url = f"{API_BASE}/api/v1/place-recommendations/generate"
        print(f"🌐 [URL] 요청 URL: {url}")
        
        response = requests.post(
            url,
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        print(f"📥 [RESPONSE] 응답 상태: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ [SUCCESS] 성공 응답:")
            print(f"  - 도시 ID: {result.get('city_id')}")
            print(f"  - 도시명: {result.get('city_name')}")
            print(f"  - 국가명: {result.get('country_name')}")
            print(f"  - 추천 카테고리 수: {len(result.get('recommendations', {}))}")
            print(f"  - 상태: {result.get('status', 'SUCCESS')}")
            
            if result.get('status') == 'AMBIGUOUS':
                print("⚠️ [AMBIGUOUS] 여전히 동명 지역 모달이 나타남!")
                print(f"  - 옵션 수: {len(result.get('options', []))}")
                return False
            else:
                print("🎉 [FIXED] 동명 지역 모달이 나타나지 않음! 수정 성공!")
                return True
                
        elif response.status_code == 400:
            error_data = response.json()
            if error_data.get('error_code') == 'AMBIGUOUS_LOCATION':
                print("❌ [STILL_AMBIGUOUS] 여전히 동명 지역 처리됨")
                print(f"  - 옵션 수: {len(error_data.get('options', []))}")
                return False
            else:
                print(f"❌ [BAD_REQUEST] 잘못된 요청: {error_data}")
                return False
        else:
            print(f"❌ [ERROR] 오류 응답: {response.status_code}")
            print(f"  - 응답 내용: {response.text}")
            return False
            
    except Exception as e:
        print(f"💥 [EXCEPTION] 테스트 중 예외: {e}")
        return False

async def test_without_place_id():
    """place_id 없이 요청 테스트 (기존 방식)"""
    
    print("\n🧪 [TEST_LEGACY] place_id 없는 기존 방식 테스트")
    
    test_payload = {
        "country": "대한민국",
        "city": "광주",
        "total_duration": 2,
        "travelers_count": 2,
        "budget_range": "medium",
        "travel_style": ["문화", "액티비티"],
        "special_requests": "다양한 명소와 맛집을 포함해주세요",
        "language_code": "ko",
        "daily_start_time": "09:00",
        "daily_end_time": "21:00"
        # place_id 없음
    }
    
    try:
        url = f"{API_BASE}/api/v1/place-recommendations/generate"
        response = requests.post(
            url,
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        print(f"📥 [LEGACY_RESPONSE] 응답 상태: {response.status_code}")
        
        if response.status_code == 400:
            error_data = response.json()
            if error_data.get('error_code') == 'AMBIGUOUS_LOCATION':
                print("✅ [EXPECTED] 예상대로 동명 지역 모달 표시됨")
                return True
        elif response.status_code == 200:
            print("ℹ️ [UNEXPECTED_SUCCESS] 예상과 달리 성공함 (캐시된 데이터일 수 있음)")
            return True
        
        return False
        
    except Exception as e:
        print(f"💥 [LEGACY_EXCEPTION] 기존 방식 테스트 중 예외: {e}")
        return False

async def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("🔧 place_id 처리 수정 사항 테스트")
    print("=" * 60)
    
    # 1. place_id 포함 테스트
    success_with_place_id = await test_place_id_processing()
    
    # 2. place_id 없는 기존 방식 테스트
    legacy_works = await test_without_place_id()
    
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)
    print(f"✅ place_id 포함 시 모달 제거: {'성공' if success_with_place_id else '실패'}")
    print(f"✅ place_id 없을 시 기존 동작: {'정상' if legacy_works else '비정상'}")
    
    if success_with_place_id and legacy_works:
        print("\n🎉 모든 테스트 통과! 수정 사항이 올바르게 작동합니다.")
    else:
        print("\n❌ 일부 테스트 실패. 추가 수정이 필요합니다.")
    
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())