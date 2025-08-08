#!/usr/bin/env python3
"""
고도화된 아키텍처 테스트 스크립트
search_strategy_v1 프롬프트가 Supabase에 있는지 확인하고, 
고도화된 추천 시스템을 테스트합니다.
"""

import asyncio
import json
from app.services.dynamic_ai_service import dynamic_ai_service
from app.services.google_places_service import GooglePlacesService
from app.services.supabase_service import supabase_service

async def test_search_strategy_prompt():
    """검색 전략 프롬프트가 Supabase에 있는지 확인"""
    print("🔍 [TEST] search_strategy_v1 프롬프트 확인 중...")
    
    try:
        prompt = await supabase_service.get_master_prompt("search_strategy_v1")
        print(f"✅ [SUCCESS] search_strategy_v1 프롬프트 발견 ({len(prompt)} 글자)")
        return True
    except Exception as e:
        print(f"❌ [ERROR] search_strategy_v1 프롬프트 없음: {e}")
        print("📝 [INFO] search_strategy_prompt.sql을 Supabase에 실행해주세요")
        return False

async def test_ai_search_queries():
    """AI 검색 계획 수립 테스트"""
    print("\n🧠 [TEST] AI 검색 계획 수립 테스트...")
    
    try:
        search_queries = await dynamic_ai_service.create_search_queries(
            city="Seoul",
            country="South Korea",
            existing_places=["경복궁", "명동", "홍대"]
        )
        
        print(f"✅ [SUCCESS] AI 검색 계획 생성 완료:")
        for category, query in search_queries.items():
            print(f"  {category}: {query}")
        
        return search_queries
    except Exception as e:
        print(f"❌ [ERROR] AI 검색 계획 실패: {e}")
        return None

async def test_parallel_places_search(search_queries):
    """병렬 Google Places API 호출 테스트"""
    if not search_queries:
        print("❌ [SKIP] 검색 쿼리가 없어서 병렬 테스트 건너뛰기")
        return
    
    print("\n🚀 [TEST] 병렬 Google Places API 호출 테스트...")
    
    try:
        google_service = GooglePlacesService()
        results = await google_service.parallel_search_by_categories(
            search_queries=search_queries,
            target_count_per_category=5  # 테스트용으로 5개만
        )
        
        print(f"✅ [SUCCESS] 병렬 검색 완료:")
        for category, places in results.items():
            print(f"  {category}: {len(places)}개 장소")
            for i, place in enumerate(places[:3]):  # 처음 3개만 표시
                print(f"    {i+1}. {place.get('name', 'Unknown')}")
        
        return results
    except Exception as e:
        print(f"❌ [ERROR] 병렬 검색 실패: {e}")
        return None

async def main():
    """전체 테스트 실행"""
    print("🎯 [START] 고도화된 아키텍처 테스트 시작\n")
    
    # 1. 프롬프트 확인
    prompt_exists = await test_search_strategy_prompt()
    
    if not prompt_exists:
        print("\n⚠️ [WARNING] 프롬프트가 없어서 AI 테스트는 건너뜁니다")
        print("search_strategy_prompt.sql을 먼저 실행해주세요")
        return
    
    # 2. AI 검색 계획 테스트
    search_queries = await test_ai_search_queries()
    
    # 3. 병렬 검색 테스트
    await test_parallel_places_search(search_queries)
    
    print("\n🎉 [COMPLETE] 고도화된 아키텍처 테스트 완료!")

if __name__ == "__main__":
    asyncio.run(main())
