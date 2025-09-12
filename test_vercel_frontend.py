#!/usr/bin/env python3
"""
Vercel 프론트엔드 테스트
"""
import requests
import json
from datetime import datetime

# Vercel 프론트엔드 URL들 (일반적인 패턴)
VERCEL_URLS = [
    "https://plango-frontend.vercel.app",
    "https://plango.vercel.app", 
    "https://plango-web.vercel.app",
    "https://plango-client.vercel.app"
]

def test_vercel_frontend():
    """Vercel 프론트엔드 접속 테스트"""
    print("🌐 Vercel 프론트엔드 테스트")
    print("=" * 50)
    
    for url in VERCEL_URLS:
        try:
            print(f"\n📍 테스트: {url}")
            response = requests.get(url, timeout=10)
            print(f"   상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ 접속 성공!")
                # HTML 내용에서 제목 추출 시도
                if "html" in response.headers.get("content-type", "").lower():
                    content = response.text
                    if "<title>" in content:
                        title_start = content.find("<title>") + 7
                        title_end = content.find("</title>", title_start)
                        if title_end > title_start:
                            title = content[title_start:title_end]
                            print(f"   페이지 제목: {title}")
                    
                    # React 앱인지 확인
                    if "react" in content.lower() or "_next" in content:
                        print(f"   ✅ Next.js/React 앱으로 확인됨")
                    
                    print(f"   응답 크기: {len(content)} bytes")
                else:
                    print(f"   응답 타입: {response.headers.get('content-type', 'N/A')}")
                    
                return url  # 성공한 URL 반환
            else:
                print(f"   ❌ 접속 실패: {response.status_code}")
                
        except Exception as e:
            print(f"   💥 예외: {e}")
    
    return None

def test_frontend_pages(base_url):
    """프론트엔드 주요 페이지 테스트"""
    if not base_url:
        print("\n❌ 사용 가능한 프론트엔드 URL이 없습니다.")
        return
        
    print(f"\n📱 프론트엔드 페이지 테스트: {base_url}")
    print("=" * 50)
    
    pages_to_test = [
        "/",
        "/create-itinerary", 
        "/itinerary-results"
    ]
    
    for page in pages_to_test:
        try:
            print(f"\n📍 페이지: {page}")
            response = requests.get(f"{base_url}{page}", timeout=10)
            print(f"   상태 코드: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ 페이지 로드 성공")
                
                # 페이지 내용 분석
                content = response.text.lower()
                
                if page == "/create-itinerary":
                    if "여행" in content or "travel" in content or "itinerary" in content:
                        print(f"   ✅ 여행 계획 페이지로 확인됨")
                    if "form" in content or "input" in content:
                        print(f"   ✅ 입력 폼이 있는 것으로 확인됨")
                        
                elif page == "/itinerary-results":
                    if "결과" in content or "result" in content or "recommendation" in content:
                        print(f"   ✅ 결과 페이지로 확인됨")
                        
            else:
                print(f"   ❌ 페이지 로드 실패: {response.status_code}")
                
        except Exception as e:
            print(f"   💥 예외: {e}")

def check_api_integration(base_url):
    """프론트엔드의 API 통합 확인"""
    if not base_url:
        return
        
    print(f"\n🔗 API 통합 확인")
    print("=" * 50)
    
    try:
        # 메인 페이지에서 API 엔드포인트 정보 찾기
        response = requests.get(base_url, timeout=10)
        if response.status_code == 200:
            content = response.text
            
            # 일반적인 API URL 패턴 찾기
            api_patterns = [
                "railway.app",
                "api.plango",
                "plango-api",
                "/api/v1/"
            ]
            
            found_apis = []
            for pattern in api_patterns:
                if pattern in content:
                    found_apis.append(pattern)
            
            if found_apis:
                print(f"   ✅ API 관련 패턴 발견: {found_apis}")
            else:
                print(f"   ⚠️ API 관련 패턴을 찾을 수 없음")
                
            # 환경 변수나 설정 확인
            if "NEXT_PUBLIC" in content:
                print(f"   ✅ Next.js 환경 변수 사용 확인됨")
                
    except Exception as e:
        print(f"   💥 API 통합 확인 실패: {e}")

if __name__ == "__main__":
    print(f"🕐 테스트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. 프론트엔드 접속 테스트
    working_url = test_vercel_frontend()
    
    # 2. 주요 페이지 테스트
    test_frontend_pages(working_url)
    
    # 3. API 통합 확인
    check_api_integration(working_url)
    
    print(f"\n🕐 테스트 완료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if working_url:
        print(f"\n✅ 사용 가능한 프론트엔드 URL: {working_url}")
        print(f"📋 테스트 가이드에 따라 수동 테스트를 진행하세요:")
        print(f"   1. {working_url}/create-itinerary 접속")
        print(f"   2. 광주, 김포 등으로 동명 지역 테스트")
        print(f"   3. 서울로 일반 도시 테스트")
    else:
        print(f"\n❌ 접속 가능한 프론트엔드 URL을 찾을 수 없습니다.")
        print(f"   Vercel 대시보드에서 실제 배포 URL을 확인해주세요.")