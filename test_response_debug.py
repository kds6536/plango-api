#!/usr/bin/env python3
"""
응답 구조 디버깅 테스트
"""

import asyncio
import httpx
import json

BASE_URL = "https://plango-api-production.up.railway.app"

async def debug_gwangju_response():
    """광주 응답 구조 디버깅"""
    print("🔍 광주 응답 구조 디버깅")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        request_data = {
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
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"상태 코드: {response.status_code}")
            print(f"응답 헤더: {dict(response.headers)}")
            
            # 원본 텍스트 확인
            response_text = response.text
            print(f"응답 텍스트 길이: {len(response_text)}")
            print(f"응답 텍스트 (처음 500자): {response_text[:500]}")
            
            # JSON 파싱 시도
            try:
                data = response.json()
                print(f"JSON 파싱 성공!")
                print(f"응답 키들: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                if isinstance(data, dict):
                    for key, value in data.items():
                        if key == 'options' and isinstance(value, list):
                            print(f"  {key}: {len(value)}개 항목")
                            for i, option in enumerate(value[:2]):
                                print(f"    {i+1}. {option}")
                        else:
                            print(f"  {key}: {value}")
                            
            except Exception as json_error:
                print(f"JSON 파싱 실패: {json_error}")
                
        except Exception as e:
            print(f"요청 실패: {e}")
            import traceback
            print(f"상세: {traceback.format_exc()}")

async def debug_seoul_response():
    """서울 응답 구조 디버깅"""
    print("\n🔍 서울 응답 구조 디버깅")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        request_data = {
            "city": "서울",
            "country": "대한민국",
            "total_duration": 2,
            "travelers_count": 1,
            "travel_style": "관광",
            "budget_level": "중간"
        }
        
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/place-recommendations/generate",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"응답 키들: {list(data.keys())}")
                
                # 중요 필드들 확인
                important_fields = ['success', 'is_fallback', 'status', 'newly_recommended_count', 'main_theme']
                for field in important_fields:
                    print(f"  {field}: {data.get(field, 'N/A')}")
                    
                # recommendations 구조 확인
                recommendations = data.get('recommendations', {})
                if isinstance(recommendations, dict):
                    print(f"  recommendations 카테고리: {list(recommendations.keys())}")
                    for category, places in recommendations.items():
                        print(f"    {category}: {len(places) if isinstance(places, list) else 'Not a list'}개")
                        
        except Exception as e:
            print(f"요청 실패: {e}")

if __name__ == "__main__":
    asyncio.run(debug_gwangju_response())
    asyncio.run(debug_seoul_response())