#!/usr/bin/env python3
"""
Vercel 프론트엔드에서 동명 지역 처리 테스트
"""

import asyncio
import httpx
from datetime import datetime

# Vercel 배포된 프론트엔드 URL
FRONTEND_URL = "https://plango-kappa.vercel.app"
API_URL = "https://plango-api-production.up.railway.app"

async def test_frontend_ambiguous():
    """프론트엔드에서 동명 지역 처리 테스트"""
    
    print("🌐 [FRONTEND_TEST] Vercel 프론트엔드 동명 지역 테스트")
    print(f"🔗 [FRONTEND_URL] {FRONTEND_URL}")
    print(f"🔗 [API_URL] {API_URL}")
    print(f"⏰ [TIME] {datetime.now().isoformat()}")
    print("=" * 70)
    
    print("\n📋 [INSTRUCTIONS] 프론트엔드 테스트 방법:")
    print("1. 브라우저에서 다음 URL을 엽니다:")
    print(f"   {FRONTEND_URL}")
    print()
    print("2. 여행 계획 생성 페이지로 이동합니다")
    print()
    print("3. 다음 정보를 입력합니다:")
    print("   - 도시: Springfield")
    print("   - 국가: United States")
    print("   - 기간: 2일")
    print("   - 인원: 2명")
    print()
    print("4. '추천 받기' 버튼을 클릭합니다")
    print()
    print("5. 예상 결과:")
    print("   ✅ 동명 지역 선택 모달이 나타남")
    print("   ✅ 3개의 Springfield 선택지 표시:")
    print("      - 미주리 스프링필드")
    print("      - 일리노이 스프링필드") 
    print("      - 매사추세츠 스프링필드")
    print("   ✅ 하나를 선택하면 정상적으로 추천 진행")
    print()
    
    # API 직접 테스트로 확인
    print("🧪 [API_VERIFICATION] API 직접 테스트로 검증:")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{API_URL}/api/v1/place-recommendations/generate",
                json={
                    "city": "Springfield",
                    "country": "United States",
                    "total_duration": 2,
                    "travelers_count": 2,
                    "travel_style": ["관광"],
                    "budget_level": "중간"
                }
            )
            
            print(f"📊 [API_RESPONSE] 상태 코드: {response.status_code}")
            
            if response.status_code == 400:
                data = response.json()
                error_code = data.get("error_code", "UNKNOWN")
                
                if error_code == "AMBIGUOUS_LOCATION":
                    options = data.get("options", [])
                    print(f"✅ [API_SUCCESS] 동명 지역 감지! 선택지 {len(options)}개")
                    print("📋 [OPTIONS] 프론트엔드에서 표시될 선택지들:")
                    
                    for i, option in enumerate(options):
                        display_name = option.get('display_name', 'Unknown')
                        formatted_address = option.get('formatted_address', 'Unknown')
                        print(f"   {i+1}. {display_name}")
                        print(f"      주소: {formatted_address}")
                    
                    print("\n✅ [FRONTEND_READY] 프론트엔드에서 이 선택지들이 모달로 표시됩니다!")
                    
                else:
                    print(f"❌ [API_ERROR] 예상과 다른 에러: {error_code}")
                    
            else:
                print(f"❌ [API_UNEXPECTED] 예상과 다른 응답: {response.status_code}")
                
        except Exception as e:
            print(f"❌ [API_FAIL] API 테스트 실패: {e}")
    
    print("\n" + "=" * 70)
    print("🎯 [NEXT_STEPS] 다음 단계:")
    print("1. 위의 URL로 브라우저에서 직접 테스트")
    print("2. Springfield 입력 후 동명 지역 모달 확인")
    print("3. 선택지 중 하나 선택 후 정상 진행 확인")
    print("=" * 70)

async def main():
    await test_frontend_ambiguous()

if __name__ == "__main__":
    asyncio.run(main())