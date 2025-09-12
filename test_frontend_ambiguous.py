#!/usr/bin/env python3
"""
프론트엔드 동명 지역 모달 동작 테스트
실제 프론트엔드에서 동명 지역 감지가 제대로 작동하는지 확인
"""

import requests
import json
from datetime import datetime, timedelta

def test_frontend_ambiguous_detection():
    """프론트엔드에서 사용하는 것과 동일한 API 호출로 동명 지역 감지 테스트"""
    
    print("🌐 프론트엔드 동명 지역 모달 테스트")
    print("=" * 60)
    
    # 프론트엔드에서 사용하는 API URL
    api_base = "https://plango-api-production.up.railway.app"
    endpoint = "/api/v1/place-recommendations/generate"
    url = f"{api_base}{endpoint}"
    
    # 오늘부터 3일간의 여행 일정 생성
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    
    # 프론트엔드에서 보내는 것과 동일한 요청 구조
    test_cases = [
        {
            "name": "광주 (동명 지역 - 광주광역시 vs 경기도 광주시)",
            "payload": {
                "country": "한국",
                "city": "광주",
                "total_duration": 3,
                "travelers_count": 2,
                "budget_range": "medium",
                "travel_style": ["문화", "액티비티"],
                "special_requests": "다양한 명소와 맛집을 포함해주세요",
                "language_code": "ko",
                "daily_start_time": "09:00",
                "daily_end_time": "21:00"
            },
            "expected_status": 400,
            "expected_error": "AMBIGUOUS_LOCATION"
        },
        {
            "name": "김포 (동명 지역 가능성)",
            "payload": {
                "country": "한국", 
                "city": "김포",
                "total_duration": 3,
                "travelers_count": 2,
                "budget_range": "medium",
                "travel_style": ["문화", "액티비티"],
                "special_requests": "다양한 명소와 맛집을 포함해주세요",
                "language_code": "ko",
                "daily_start_time": "09:00",
                "daily_end_time": "21:00"
            }
        },
        {
            "name": "서울 (단일 지역)",
            "payload": {
                "country": "한국",
                "city": "서울",
                "total_duration": 3,
                "travelers_count": 2,
                "budget_range": "medium", 
                "travel_style": ["문화", "액티비티"],
                "special_requests": "다양한 명소와 맛집을 포함해주세요",
                "language_code": "ko",
                "daily_start_time": "09:00",
                "daily_end_time": "21:00"
            },
            "expected_status": 200
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print("-" * 50)
        
        try:
            # 프론트엔드와 동일한 헤더 설정
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            print(f"📤 요청 URL: {url}")
            print(f"📤 요청 데이터: {json.dumps(test_case['payload'], ensure_ascii=False, indent=2)}")
            
            # API 호출 (30초 타임아웃)
            response = requests.post(
                url, 
                json=test_case['payload'],
                headers=headers,
                timeout=30
            )
            
            print(f"📥 응답 상태: {response.status_code}")
            print(f"📥 응답 헤더: {dict(response.headers)}")
            
            # 응답 데이터 파싱
            try:
                response_data = response.json()
                print(f"📥 응답 데이터: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
            except:
                print(f"📥 응답 텍스트: {response.text}")
                response_data = {}
            
            # 예상 결과와 비교
            if 'expected_status' in test_case:
                if response.status_code == test_case['expected_status']:
                    print(f"✅ 예상 상태 코드 일치: {test_case['expected_status']}")
                else:
                    print(f"❌ 상태 코드 불일치: 예상 {test_case['expected_status']}, 실제 {response.status_code}")
            
            if 'expected_error' in test_case:
                if response.status_code == 400 and response_data.get('error_code') == test_case['expected_error']:
                    print(f"✅ 예상 에러 코드 일치: {test_case['expected_error']}")
                    
                    # 동명 지역 옵션 확인
                    options = response_data.get('options', [])
                    if options:
                        print(f"🎯 동명 지역 옵션 수: {len(options)}")
                        for j, option in enumerate(options, 1):
                            display_name = option.get('display_name', '알 수 없음')
                            formatted_address = option.get('formatted_address', '주소 없음')
                            place_id = option.get('place_id', '없음')
                            print(f"   {j}. {display_name}")
                            print(f"      주소: {formatted_address}")
                            print(f"      Place ID: {place_id}")
                        
                        # 프론트엔드 모달에서 사용할 데이터 구조 시뮬레이션
                        print("\n🖥️ 프론트엔드 모달 데이터 구조:")
                        normalized_options = []
                        for option in options:
                            normalized = {
                                "display_name": option.get('display_name', '선택지'),
                                "request_body": {
                                    **test_case['payload'],
                                    "place_id": option.get('place_id'),
                                    "city": option.get('display_name', test_case['payload']['city'])
                                }
                            }
                            normalized_options.append(normalized)
                        
                        print(json.dumps(normalized_options, ensure_ascii=False, indent=2))
                        
                else:
                    print(f"❌ 예상 에러와 다름: 예상 {test_case['expected_error']}, 실제 {response_data.get('error_code', '없음')}")
            
            # 성공 응답 처리
            if response.status_code == 200:
                if response_data.get('success') and response_data.get('recommendations'):
                    print("✅ 정상 추천 응답 확인")
                    recommendations = response_data['recommendations']
                    print(f"📊 추천 카테고리 수: {len(recommendations)}")
                    for category, places in recommendations.items():
                        if isinstance(places, list):
                            print(f"   - {category}: {len(places)}개 장소")
                else:
                    print("⚠️ 200 응답이지만 예상 구조와 다름")
                    
        except requests.exceptions.Timeout:
            print("⏰ 요청 타임아웃 (30초)")
        except requests.exceptions.ConnectionError:
            print("🔌 연결 오류")
        except Exception as e:
            print(f"💥 예외 발생: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 프론트엔드 테스트 가이드")
    print("=" * 60)
    print("1. 브라우저에서 https://plango.vercel.app/create-itinerary 접속")
    print("2. 다음 테스트 시나리오 실행:")
    print("   📍 광주 입력 → 동명 지역 모달 표시 확인")
    print("   📍 김포 입력 → 동명 지역 모달 표시 가능성 확인")
    print("   📍 서울 입력 → 정상 추천 진행 확인")
    print("3. 모달에서 옵션 선택 시 정상 진행 확인")
    print("4. 최종 추천 결과 페이지 도달 확인")

if __name__ == "__main__":
    test_frontend_ambiguous_detection()