#!/usr/bin/env python3
"""
Plan A 활성화 및 동명 지역 감지 로직 테스트
⚠️ 중요: 이 테스트는 Railway 배포 환경에서만 실행 가능합니다!
로컬 환경에서는 테스트할 수 없습니다.
"""

import asyncio
import httpx
import json
from datetime import datetime

# API 기본 설정 - Railway 배포 환경에서만 테스트 가능
BASE_URL = "https://plango-api-production.up.railway.app"  # Railway 배포 URL
HEADERS = {"Content-Type": "application/json"}

async def test_plan_a_activation():
    """Plan A 활성화 테스트"""
    print("🚀 [PLAN_A_TEST] Plan A 활성화 테스트 시작")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. 일반 도시 테스트 (Plan A 정상 동작 확인)
        print("\n1️⃣ 일반 도시 테스트 (서울) - Plan A 정상 동작 확인")
        
        seoul_request = {
            "city": "서울",
            "country": "대한민국",
            "total_duration": 3,
            "travelers_count": 2,
            "travel_style": "관광",
            "budget_level": "중간"
        }
        
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/place-recommendations/generate",
                json=seoul_request,
                headers=HEADERS
            )
            
            print(f"   상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Plan A 성공: {data.get('newly_recommended_count', 0)}개 신규 추천")
                print(f"   폴백 여부: {data.get('is_fallback', False)}")
                print(f"   메인 테마: {data.get('main_theme', 'N/A')}")
            else:
                print(f"   ❌ 실패: {response.text}")
                
        except Exception as e:
            print(f"   ❌ 예외 발생: {e}")

        # 2. 동명 지역 테스트 (광주) - 400 에러 및 선택지 반환 확인
        print("\n2️⃣ 동명 지역 테스트 (광주) - 400 에러 및 선택지 반환 확인")
        
        gwangju_request = {
            "city": "광주",
            "country": "대한민국",
            "total_duration": 2,
            "travelers_count": 1,
            "travel_style": "관광",
            "budget_level": "중간"
        }
        
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/place-recommendations/generate",
                json=gwangju_request,
                headers=HEADERS
            )
            
            print(f"   상태 코드: {response.status_code}")
            
            if response.status_code == 400:
                data = response.json()
                print(f"   ✅ 동명 지역 감지 성공!")
                print(f"   에러 코드: {data.get('error_code')}")
                print(f"   메시지: {data.get('message')}")
                print(f"   선택지 개수: {len(data.get('options', []))}")
                
                for i, option in enumerate(data.get('options', []), 1):
                    print(f"     {i}. {option.get('display_name')} - {option.get('formatted_address')}")
            else:
                print(f"   ❌ 예상과 다른 응답: {response.text}")
                
        except Exception as e:
            print(f"   ❌ 예외 발생: {e}")

        # 3. place_id가 있는 경우 테스트 (동명 지역 감지 건너뛰기)
        print("\n3️⃣ place_id 제공 시 테스트 - 동명 지역 감지 건너뛰기 확인")
        
        place_id_request = {
            "city": "광주",
            "country": "대한민국",
            "place_id": "ChIJzWVBSgSifDUR64Pq5LTtioU",  # 광주광역시
            "total_duration": 2,
            "travelers_count": 1,
            "travel_style": "관광",
            "budget_level": "중간"
        }
        
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/place-recommendations/generate",
                json=place_id_request,
                headers=HEADERS
            )
            
            print(f"   상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ place_id 제공 시 정상 처리: {data.get('newly_recommended_count', 0)}개 추천")
                print(f"   폴백 여부: {data.get('is_fallback', False)}")
            else:
                print(f"   ❌ 실패: {response.text}")
                
        except Exception as e:
            print(f"   ❌ 예외 발생: {e}")

async def test_fallback_system():
    """폴백 시스템 동작 테스트"""
    print("\n🔄 [FALLBACK_TEST] 폴백 시스템 테스트 시작")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 존재하지 않는 도시로 Plan A 실패 유도
        print("\n4️⃣ 폴백 시스템 테스트 - Plan A 실패 시 폴백 동작 확인")
        
        invalid_request = {
            "city": "존재하지않는도시12345",
            "country": "존재하지않는국가12345",
            "total_duration": 2,
            "travelers_count": 1,
            "travel_style": "관광",
            "budget_level": "중간"
        }
        
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/place-recommendations/generate",
                json=invalid_request,
                headers=HEADERS
            )
            
            print(f"   상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 폴백 시스템 동작: {data.get('newly_recommended_count', 0)}개 추천")
                print(f"   폴백 여부: {data.get('is_fallback', False)}")
                print(f"   폴백 이유: {data.get('fallback_reason', 'N/A')}")
                print(f"   상태: {data.get('status', 'N/A')}")
            else:
                print(f"   ❌ 실패: {response.text}")
                
        except Exception as e:
            print(f"   ❌ 예외 발생: {e}")

async def main():
    """메인 테스트 실행"""
    print("=" * 60)
    print("🧪 Plan A 활성화 및 동명 지역 감지 로직 테스트")
    print("=" * 60)
    
    await test_plan_a_activation()
    await test_fallback_system()
    
    print("\n" + "=" * 60)
    print("✅ 모든 테스트 완료!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())