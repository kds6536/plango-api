#!/usr/bin/env python3
"""
V2 최적화된 아키텍처 테스트
Google Places Autocomplete 전제 하에서의 단순화된 흐름 검증
"""

import asyncio
import json
import requests
from datetime import datetime

# Railway 배포된 백엔드 URL
BACKEND_URL = "https://plango-api-production.up.railway.app"

def test_v2_optimized_flow():
    """V2 최적화된 흐름 테스트"""
    
    print("🚀 [V2_TEST_START] 최적화된 아키텍처 테스트 시작")
    print(f"🌐 [BACKEND_URL] {BACKEND_URL}")
    
    # 테스트 케이스: place_id가 있는 정상적인 요청
    test_payload = {
        "country": "대한민국",
        "city": "광주광역시",
        "place_id": "ChIJm8hW8VaUZTURuD-kVKXScQE",  # 광주광역시 place_id
        "total_duration": 2,
        "travelers_count": 2,
        "budget_range": "medium",
        "travel_style": ["관광", "문화"],
        "special_requests": "가족과 함께 즐길 수 있는 맛집과 관광지를 포함해주세요",
        "language_code": "ko"
    }
    
    print("\n" + "="*60)
    print("🎯 [V2_TEST] 최적화된 추천 생성 테스트")
    print("="*60)
    print(f"📋 [PAYLOAD] {json.dumps(test_payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/place-recommendations/generate",
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        print(f"📊 [RESPONSE_STATUS] {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # V2 응답 검증
            print("✅ [V2_SUCCESS] 최적화된 추천 생성 성공!")
            print(f"🏙️ [CITY_ID] {data.get('city_id')}")
            print(f"🎯 [MAIN_THEME] {data.get('main_theme')}")
            print(f"📊 [CATEGORIES] {len(data.get('recommendations', {}))}개 카테고리")
            
            # 카테고리별 결과 확인
            recommendations = data.get('recommendations', {})
            for category, places in recommendations.items():
                print(f"  - {category}: {len(places)}개 장소")
                if len(places) > 10:
                    print(f"    ⚠️ [WARNING] {category}에 10개 초과 결과 ({len(places)}개)")
                else:
                    print(f"    ✅ [LIMIT_OK] {category} 제한 준수")
            
            # 기대하지 않는 필드들 확인
            status = data.get('status')
            options = data.get('options')
            
            if status == 'AMBIGUOUS':
                print("❌ [V2_FAIL] AMBIGUOUS 상태가 나타났습니다! (V2에서는 발생하지 않아야 함)")
                return False
            
            if options:
                print("❌ [V2_FAIL] options 필드가 있습니다! (V2에서는 불필요)")
                return False
            
            print("🎉 [V2_VALIDATION] 모든 V2 검증 통과!")
            return True
                
        else:
            print(f"❌ [ERROR] HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ [EXCEPTION] 요청 실패: {e}")
        return False

def test_v2_health_check():
    """V2 헬스체크 테스트"""
    print("\n🏥 [V2_HEALTH_CHECK] V2 서비스 상태 확인")
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/place-recommendations/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            service_name = data.get('service', '')
            
            if 'v2.0' in service_name.lower() or 'optimized' in service_name.lower():
                print(f"✅ [V2_HEALTH] V2 서비스 확인: {service_name}")
                
                features = data.get('features', {})
                v2_features = [
                    'google_places_autocomplete_required',
                    'simplified_architecture', 
                    'no_geocoding_needed',
                    'no_ambiguous_handling'
                ]
                
                for feature in v2_features:
                    if features.get(feature):
                        print(f"  ✅ {feature}: 활성화")
                    else:
                        print(f"  ❌ {feature}: 비활성화")
                
                return True
            else:
                print(f"⚠️ [V2_HEALTH] 아직 V1 서비스: {service_name}")
                return False
        else:
            print(f"❌ [HEALTH_ERROR] HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ [HEALTH_EXCEPTION] {e}")
        return False

def test_missing_place_id():
    """place_id가 없을 때의 에러 처리 테스트"""
    print("\n🧪 [MISSING_PLACE_ID_TEST] place_id 누락 테스트")
    
    test_payload = {
        "country": "대한민국",
        "city": "서울",
        # place_id 의도적으로 누락
        "total_duration": 2,
        "travelers_count": 2,
        "budget_range": "medium",
        "travel_style": ["관광"],
        "language_code": "ko"
    }
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/place-recommendations/generate",
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 400:
            error_detail = response.json().get('detail', '')
            if 'place_id' in error_detail:
                print("✅ [VALIDATION_OK] place_id 누락 시 적절한 에러 반환")
                return True
            else:
                print(f"⚠️ [VALIDATION_PARTIAL] 400 에러이지만 메시지가 다름: {error_detail}")
                return False
        else:
            print(f"❌ [VALIDATION_FAIL] 예상과 다른 응답: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ [VALIDATION_EXCEPTION] {e}")
        return False

if __name__ == "__main__":
    print("🚀 V2 최적화된 아키텍처 통합 테스트")
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success_count = 0
    total_tests = 3
    
    # 1. 헬스체크
    if test_v2_health_check():
        success_count += 1
    
    # 2. 정상 흐름 테스트
    if test_v2_optimized_flow():
        success_count += 1
    
    # 3. place_id 누락 테스트
    if test_missing_place_id():
        success_count += 1
    
    print(f"\n📊 [FINAL_RESULT] {success_count}/{total_tests} 테스트 통과")
    
    if success_count == total_tests:
        print("🎉 [SUCCESS] 모든 V2 테스트 성공!")
    else:
        print("💥 [PARTIAL_SUCCESS] 일부 테스트 실패")
        exit(1)
    
    print(f"⏰ 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")