#!/usr/bin/env python3
"""Google API 실제 호출 테스트"""

import asyncio
import json
from app.services.google_places_service import GooglePlacesService

async def test_google_places_api():
    """Google Places API 실제 호출 테스트"""
    print("=== Google Places API 테스트 시작 ===")
    
    service = GooglePlacesService()
    print(f"API Key 설정: {'✅' if service.api_key else '❌'}")
    print(f"Google Maps Client: {'✅' if service.gmaps else '❌'}")
    
    if not service.api_key:
        print("❌ API 키가 설정되지 않았습니다.")
        return
    
    # 간단한 텍스트 검색 테스트
    try:
        print("\n=== 텍스트 검색 테스트 ===")
        fields = [
            "places.id",
            "places.displayName",
            "places.formattedAddress",
            "places.rating"
        ]
        
        result = await service.search_places_text(
            text_query="서울 명동",
            fields=fields,
            language_code="ko"
        )
        
        if result and "places" in result:
            print(f"✅ 검색 성공: {len(result['places'])}개 장소 발견")
            for i, place in enumerate(result['places'][:3]):  # 처음 3개만 출력
                name = place.get('displayName', {}).get('text', 'Unknown')
                address = place.get('formattedAddress', 'No address')
                print(f"  {i+1}. {name} - {address}")
        else:
            print("❌ 검색 결과가 없습니다.")
            print(f"응답: {result}")
            
    except Exception as e:
        print(f"❌ API 호출 실패: {e}")
        import traceback
        print(f"상세 에러: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_google_places_api())