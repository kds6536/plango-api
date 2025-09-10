#!/usr/bin/env python3
"""
Railway 서버 엔드포인트 테스트 스크립트
"""

import asyncio
import httpx
import json
from datetime import datetime

# Railway 도메인 (실제 도메인으로 변경 필요)
RAILWAY_BASE_URL = "https://plango-api-production.up.railway.app"

class RailwayTester:
    def __init__(self):
        self.base_url = RAILWAY_BASE_URL
        
    async def test_email_notification(self):
        """이메일 알림 시스템 테스트"""
        print("📧 [EMAIL_TEST] 이메일 알림 시스템 테스트 시작")
        
        url = f"{self.base_url}/api/v1/place-recommendations/test-email-notification"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url)
                
                print(f"  📊 Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"  ✅ 응답: {json.dumps(data, indent=2, ensure_ascii=False)}")
                    
                    if data.get("status") == "success":
                        print(f"  🎉 이메일 발송 성공! 관리자 이메일 확인: {data.get('admin_email')}")
                        return True
                    else:
                        print(f"  ⚠️ 이메일 발송 실패: {data.get('message')}")
                        return False
                else:
                    print(f"  ❌ HTTP 에러: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"  💥 예외 발생: {e}")
            return False
    
    async def test_ambiguous_location(self):
        """동명 지역 처리 테스트"""
        print("\n🌍 [AMBIGUOUS_TEST] 동명 지역 처리 테스트 시작")
        
        url = f"{self.base_url}/api/v1/place-recommendations/generate"
        
        # 광주로 테스트 (경기도 광주 vs 전라도 광주)
        payload = {
            "city": "광주",
            "country": "대한민국",
            "total_duration": 2,
            "travelers_count": 2,
            "travel_style": "관광",
            "budget_level": "중간"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                
                print(f"  📊 Status Code: {response.status_code}")
                
                if response.status_code == 400:
                    data = response.json()
                    if data.get("error_code") == "AMBIGUOUS_LOCATION":
                        print(f"  ✅ 동명 지역 감지 성공!")
                        print(f"  📝 메시지: {data.get('message')}")
                        print(f"  📍 선택지 수: {len(data.get('options', []))}")
                        
                        for i, option in enumerate(data.get('options', [])):
                            print(f"    {i+1}. {option.get('display_name')}")
                        
                        return True
                    else:
                        print(f"  ❌ 예상과 다른 400 에러: {data}")
                        return False
                        
                elif response.status_code == 200:
                    data = response.json()
                    print(f"  ⚠️ 동명 지역이 감지되지 않고 정상 응답 반환")
                    print(f"  📊 폴백 여부: {data.get('is_fallback', False)}")
                    print(f"  📊 추천 수: {data.get('newly_recommended_count', 0)}")
                    return False
                    
                else:
                    print(f"  ❌ 예상치 못한 상태 코드: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"  💥 예외 발생: {e}")
            return False
    
    async def test_fallback_system(self):
        """폴백 시스템 테스트"""
        print("\n🔄 [FALLBACK_TEST] 폴백 시스템 테스트 시작")
        
        url = f"{self.base_url}/api/v1/place-recommendations/test-geocoding-failure"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url)
                
                print(f"  📊 Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"  ✅ 응답: {json.dumps(data, indent=2, ensure_ascii=False)}")
                    
                    if data.get("is_fallback"):
                        print(f"  🎉 폴백 시스템 정상 작동!")
                        print(f"  📊 폴백 이유: {data.get('fallback_reason')}")
                        return True
                    else:
                        print(f"  ⚠️ 폴백이 아닌 정상 응답")
                        return False
                else:
                    print(f"  ❌ HTTP 에러: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"  💥 예외 발생: {e}")
            return False
    
    async def test_google_api_diagnosis(self):
        """Google API 진단 테스트"""
        print("\n🔍 [API_DIAGNOSIS] Google API 진단 테스트 시작")
        
        url = f"{self.base_url}/api/v1/diagnosis/google-apis"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                
                print(f"  📊 Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 서버 정보
                    server_info = data.get("server_info", {})
                    print(f"  🖥️ 서버 정보:")
                    print(f"    - Backend Key: {'있음' if server_info.get('backend_key_exists') else '없음'}")
                    print(f"    - Frontend Key: {'있음' if server_info.get('frontend_key_exists') else '없음'}")
                    
                    # API 테스트 결과
                    api_tests = data.get("api_tests", {})
                    print(f"  🧪 API 테스트 결과:")
                    
                    for api_name, result in api_tests.items():
                        status = "✅ 성공" if result.get("success") else "❌ 실패"
                        error = result.get("error_message", "")
                        print(f"    - {api_name}: {status}")
                        if error:
                            print(f"      에러: {error}")
                    
                    # 요약
                    summary = data.get("summary", {})
                    print(f"  📊 요약: {summary.get('working_apis')}/{summary.get('total_apis')} APIs 작동")
                    print(f"  🎯 전체 상태: {summary.get('overall_status')}")
                    
                    return True
                else:
                    print(f"  ❌ HTTP 에러: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"  💥 예외 발생: {e}")
            return False
    
    async def test_server_info(self):
        """서버 정보 테스트"""
        print("\n🖥️ [SERVER_INFO] Railway 서버 정보 테스트 시작")
        
        url = f"{self.base_url}/api/v1/diagnosis/server-info"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                
                print(f"  📊 Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"  ✅ 서버 정보: {json.dumps(data, indent=2, ensure_ascii=False)}")
                    return True
                else:
                    print(f"  ❌ HTTP 에러: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"  💥 예외 발생: {e}")
            return False
    
    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("🚀 Railway 엔드포인트 테스트 시작")
        print(f"🌐 Base URL: {self.base_url}")
        print("=" * 60)
        
        tests = [
            ("서버 정보", self.test_server_info),
            ("Google API 진단", self.test_google_api_diagnosis),
            ("이메일 알림", self.test_email_notification),
            ("동명 지역 처리", self.test_ambiguous_location),
            ("폴백 시스템", self.test_fallback_system),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            try:
                success = await test_func()
                results[test_name] = success
            except Exception as e:
                print(f"💥 {test_name} 테스트 중 예외: {e}")
                results[test_name] = False
        
        # 결과 요약
        print("\n" + "=" * 60)
        print("📊 테스트 결과 요약")
        print("=" * 60)
        
        success_count = 0
        for test_name, success in results.items():
            status = "✅ 성공" if success else "❌ 실패"
            print(f"{test_name}: {status}")
            if success:
                success_count += 1
        
        print(f"\n총 {len(tests)}개 테스트 중 {success_count}개 성공")
        
        if success_count == len(tests):
            print("🎉 모든 테스트가 성공했습니다!")
        elif success_count > 0:
            print("⚠️ 일부 테스트가 실패했습니다. 로그를 확인해주세요.")
        else:
            print("🚨 모든 테스트가 실패했습니다. 시스템 점검이 필요합니다.")

async def main():
    tester = RailwayTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())