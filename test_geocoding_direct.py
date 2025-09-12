#!/usr/bin/env python3
"""
Geocoding 서비스 직접 테스트
"""
import requests
import json
from datetime import datetime

# Railway 백엔드 URL
RAILWAY_URL = "https://plango-api-production.up.railway.app"

def test_geocoding_with_ambiguous():
    """동명 지역 감지 테스트 - 상세 로그 확인"""
    print("🎯 동명 지역 감지 상세 테스트")
    print("=" * 50)
    
    # 광주 테스트 (확실한 동명 지역)
    test_data = {
        "country": "대한민국",
        "city": "광주",
        "total_duration": 2,
        "travelers_count": 2,
        "budget_level": "중간",
        "travel_style": "관광"
    }
    
    try:
        print("📍 광주 동명 지역 테스트 (상세)...")
        response = requests.post(
            f"{RAILWAY_URL}/api/v1/place-recommendations/generate",
            json=test_data,
            timeout=60  # 타임아웃 늘림
        )
        
        print(f"   상태 코드: {response.status_code}")
        print(f"   응답 헤더: {dict(response.headers)}")
        
        if response.status_code == 400:
            try:
                data = response.json()
                print(f"   ✅ 400 응답 받음 - 동명 지역 감지 가능성")
                print(f"   응답 데이터: {json.dumps(data, ensure_ascii=False, indent=2)}")
                
                # AMBIGUOUS_LOCATION 확인
                if isinstance(data, dict):
                    if data.get("error_code") == "AMBIGUOUS_LOCATION":
                        print("   🎉 동명 지역 감지 성공!")
                        options = data.get("options", [])
                        print(f"   감지된 옵션 수: {len(options)}")
                        for i, option in enumerate(options, 1):
                            print(f"   {i}. {option}")
                    elif "detail" in data and isinstance(data["detail"], dict):
                        detail = data["detail"]
                        if detail.get("error_code") == "AMBIGUOUS_LOCATION":
                            print("   🎉 동명 지역 감지 성공! (detail 내부)")
                            options = detail.get("options", [])
                            print(f"   감지된 옵션 수: {len(options)}")
                            for i, option in enumerate(options, 1):
                                print(f"   {i}. {option}")
                        else:
                            print(f"   ❌ 예상과 다른 detail 구조: {detail}")
                    else:
                        print(f"   ❌ 예상과 다른 400 응답 구조")
                else:
                    print(f"   ❌ 응답이 dict가 아님: {type(data)}")
                    
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON 파싱 실패: {e}")
                print(f"   원본 응답: {response.text}")
                
        elif response.status_code == 200:
            try:
                data = response.json()
                print(f"   ⚠️ 200 응답 - 폴백 시스템 작동")
                print(f"   is_fallback: {data.get('is_fallback', False)}")
                print(f"   fallback_reason: {data.get('fallback_reason', 'N/A')}")
                print(f"   message: {data.get('message', 'N/A')}")
            except:
                print(f"   ⚠️ 200 응답이지만 JSON 파싱 실패")
                print(f"   응답: {response.text[:200]}...")
        else:
            print(f"   ❌ 예상과 다른 상태 코드: {response.status_code}")
            print(f"   응답: {response.text}")
            
    except Exception as e:
        print(f"   💥 테스트 예외: {e}")

def test_normal_city():
    """일반 도시 테스트"""
    print("\n🏙️ 일반 도시 테스트 (부산)")
    print("=" * 50)
    
    test_data = {
        "country": "대한민국",
        "city": "부산",
        "total_duration": 2,
        "travelers_count": 2,
        "budget_level": "중간",
        "travel_style": "관광"
    }
    
    try:
        print("🏙️ 부산 테스트...")
        response = requests.post(
            f"{RAILWAY_URL}/api/v1/place-recommendations/generate",
            json=test_data,
            timeout=60
        )
        
        print(f"   상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("   ✅ 부산 추천 생성 성공!")
                print(f"   is_fallback: {data.get('is_fallback', False)}")
                if "recommendations" in data:
                    print(f"   추천 카테고리 수: {len(data['recommendations'])}")
            except:
                print("   ✅ 200 응답이지만 JSON 파싱 실패")
        elif response.status_code == 400:
            print("   ⚠️ 부산도 동명 지역으로 감지됨")
            try:
                data = response.json()
                print(f"   응답: {json.dumps(data, ensure_ascii=False, indent=2)}")
            except:
                print(f"   응답: {response.text}")
        else:
            print(f"   ❌ 예상과 다른 상태 코드: {response.status_code}")
            
    except Exception as e:
        print(f"   💥 부산 테스트 예외: {e}")

if __name__ == "__main__":
    print(f"🕐 Geocoding 테스트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 대상 서버: {RAILWAY_URL}")
    print()
    
    test_geocoding_with_ambiguous()
    test_normal_city()
    
    print(f"\n🕐 테스트 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")