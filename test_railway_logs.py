#!/usr/bin/env python3
"""
Railway 로그 추적을 위한 특별한 테스트
폴백에서 Geocoding이 호출되는지 확인
"""

import requests
import json
import time
from datetime import datetime

def test_fallback_geocoding_logs():
    """Railway 로그에서 추적 가능한 특별한 요청 전송"""
    
    print("🔍 Railway 로그 추적 테스트")
    print("=" * 60)
    
    # 특별한 식별자 생성
    test_id = f"LOG_TEST_{int(time.time())}"
    print(f"🏷️ 테스트 ID: {test_id}")
    
    api_base = "https://plango-api-production.up.railway.app"
    endpoint = "/api/v1/place-recommendations/generate"
    url = f"{api_base}{endpoint}"
    
    # 광주 테스트 (동명 지역)
    payload = {
        "country": "한국",
        "city": "광주",  # 동명 지역
        "total_duration": 3,
        "travelers_count": 2,
        "budget_range": "medium",
        "travel_style": ["문화", "액티비티"],
        "special_requests": f"[{test_id}] Railway 로그 추적용 테스트 요청",
        "language_code": "ko",
        "daily_start_time": "09:00",
        "daily_end_time": "21:00"
    }
    
    print(f"📤 요청 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📤 요청 URL: {url}")
    print(f"📤 특별 요청 내용: {payload['special_requests']}")
    
    try:
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Test-ID': test_id  # 헤더에도 테스트 ID 추가
        }
        
        response = requests.post(
            url, 
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print(f"📥 응답 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📥 응답 상태: {response.status_code}")
        
        try:
            response_data = response.json()
            print(f"📥 응답 데이터:")
            print(json.dumps(response_data, ensure_ascii=False, indent=2))
            
            # 폴백 응답인지 확인
            if response_data.get('is_fallback'):
                print("\n🔍 폴백 시스템 작동 확인됨!")
                print("📋 Railway 로그에서 다음 키워드들을 찾아보세요:")
                print(f"   - {test_id}")
                print("   - [FALLBACK_START]")
                print("   - [FALLBACK_DEBUG]")
                print("   - [FALLBACK_GEOCODING]")
                print("   - [FALLBACK_AMBIGUOUS_CHECK]")
                print("   - [FALLBACK_CONTINUE]")
                
            # 동명 지역 감지 확인
            if response.status_code == 400 and response_data.get('error_code') == 'AMBIGUOUS_LOCATION':
                print("\n✅ 동명 지역 감지 성공!")
                options = response_data.get('options', [])
                print(f"   감지된 옵션 수: {len(options)}")
                
        except Exception as parse_error:
            print(f"❌ 응답 파싱 실패: {parse_error}")
            print(f"📥 Raw 응답: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ 요청 타임아웃")
    except Exception as e:
        print(f"💥 요청 실패: {e}")
    
    print("\n" + "=" * 60)
    print("🔍 Railway 로그 확인 방법:")
    print("1. Railway 대시보드 접속")
    print("2. plango-api 프로젝트 선택")
    print("3. Deployments 탭 → 최신 배포 선택")
    print("4. View Logs 클릭")
    print(f"5. '{test_id}' 또는 '[FALLBACK_' 키워드로 검색")
    print("\n📋 확인해야 할 로그:")
    print("   - 폴백 시작: [FALLBACK_START]")
    print("   - Geocoding 호출: [FALLBACK_GEOCODING]")
    print("   - 동명 지역 감지: [FALLBACK_AMBIGUOUS_CHECK]")
    print("   - 일반 추천 진행: [FALLBACK_CONTINUE]")

if __name__ == "__main__":
    test_fallback_geocoding_logs()