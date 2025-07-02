#!/usr/bin/env python3
"""
새로운 4단계 프로세스 API 테스트 스크립트
"""

import requests
import json
import time

API_BASE_URL = "http://127.0.0.1:8005"

def test_server_connection():
    """서버 연결 테스트"""
    print("🔌 서버 연결 테스트...")
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        if response.status_code == 200:
            print("✅ 서버 연결 성공!")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            return True
        else:
            print(f"❌ 서버 응답 에러: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 서버 연결 실패: {str(e)}")
        return False

def test_api_info():
    """API 정보 엔드포인트 테스트"""
    print("\n📖 API 정보 테스트...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/itinerary/info", timeout=10)
        if response.status_code == 200:
            print("✅ API 정보 조회 성공!")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            return True
        else:
            print(f"❌ API 정보 조회 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API 정보 조회 에러: {str(e)}")
        return False

def test_generate_api():
    """4단계 프로세스 /generate API 테스트"""
    print("\n🎯 4단계 프로세스 /generate API 테스트...")
    
    test_data = {
        "city": "서울",
        "duration": 2,
        "special_requests": "맛집과 문화 탐방 위주로",
        "travel_style": ["cultural", "gourmet"],
        "budget_range": "medium",
        "travelers_count": 2
    }
    
    print(f"📤 요청 데이터: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/itinerary/generate",
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ 4단계 프로세스 API 호출 성공!")
            result = response.json()
            
            # 응답 구조 확인
            print(f"📝 응답 키: {list(result.keys())}")
            print(f"📋 Plan A 제목: {result.get('plan_a', {}).get('title', 'N/A')}")
            print(f"📋 Plan B 제목: {result.get('plan_b', {}).get('title', 'N/A')}")
            print(f"🆔 Request ID: {result.get('request_id', 'N/A')}")
            
            # 전체 응답 저장
            with open('test_result.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print("💾 전체 응답을 test_result.json에 저장했습니다.")
            
            return True
        else:
            print(f"❌ API 호출 실패: {response.status_code}")
            print(f"📄 응답 내용: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ API 호출 에러: {str(e)}")
        return False

def test_optimize_api():
    """경로 최적화 /optimize API 테스트"""
    print("\n🗺️ 경로 최적화 /optimize API 테스트...")
    
    # 샘플 장소 데이터
    test_data = {
        "selected_places": [
            {
                "place_id": "test_1",
                "name": "경복궁",
                "category": "관광",
                "lat": 37.5796,
                "lng": 126.9770
            },
            {
                "place_id": "test_2", 
                "name": "명동",
                "category": "쇼핑",
                "lat": 37.5636,
                "lng": 126.9834
            },
            {
                "place_id": "test_3",
                "name": "홍대",
                "category": "놀거리",
                "lat": 37.5511,
                "lng": 126.9233
            }
        ],
        "duration": 2,
        "start_location": "서울역"
    }
    
    print(f"📤 요청 데이터: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/itinerary/optimize",
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ 경로 최적화 API 호출 성공!")
            result = response.json()
            
            print(f"📝 응답 키: {list(result.keys())}")
            print(f"📋 최적화된 계획 제목: {result.get('optimized_plan', {}).get('title', 'N/A')}")
            print(f"📏 총 거리: {result.get('total_distance', 'N/A')}")
            print(f"⏱️ 총 시간: {result.get('total_duration', 'N/A')}")
            
            return True
        else:
            print(f"❌ API 호출 실패: {response.status_code}")
            print(f"📄 응답 내용: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ API 호출 에러: {str(e)}")
        return False

def main():
    """메인 테스트 함수"""
    print("🚀 Plango API 4단계 프로세스 테스트 시작!")
    print("=" * 50)
    
    # 1. 서버 연결 테스트
    if not test_server_connection():
        print("\n❌ 서버가 실행되지 않았습니다. 먼저 서버를 시작해주세요:")
        print("cd plango-api && source venv/Scripts/activate && python main.py")
        return
    
    # 2. API 정보 테스트
    test_api_info()
    
    # 3. Generate API 테스트
    test_generate_api()
    
    # 4. Optimize API 테스트
    test_optimize_api()
    
    print("\n" + "=" * 50)
    print("🎉 API 테스트 완료!")

if __name__ == "__main__":
    main() 