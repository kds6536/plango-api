"""
Plango v6.0 새로운 스키마 설정 라우터
새로운 데이터베이스 스키마 초기화 및 테스트용 엔드포인트
"""

from fastapi import APIRouter, HTTPException
import logging
from app.services.supabase_service import supabase_service
from app.services.place_recommendation_service import place_recommendation_service
from app.schemas.place import PlaceRecommendationRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/setup-v6", tags=["Setup v6.0"])


@router.post("/test-country-city")
async def test_country_city_creation():
    """
    국가/도시 생성 테스트
    """
    try:
        # 테스트 데이터
        test_countries = [
            ("한국", ["서울", "부산", "제주"]),
            ("일본", ["도쿄", "오사카", "교토"]),
            ("미국", ["뉴욕", "로스앤젤레스", "라스베가스"])
        ]
        
        results = []
        
        for country_name, cities in test_countries:
            country_id = await supabase_service.get_or_create_country(country_name)
            city_results = []
            
            for city_name in cities:
                country_id = await supabase_service.get_or_create_country(country_name)
                region_id = await supabase_service.get_or_create_region(country_id, "_DEFAULT_")
                city_id = await supabase_service.get_or_create_city(region_id, city_name)
                city_results.append({
                    "city_name": city_name,
                    "city_id": city_id
                })
            
            results.append({
                "country_name": country_name,
                "country_id": country_id,
                "cities": city_results
            })
        
        return {
            "success": True,
            "message": "국가/도시 생성 테스트 완료",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"국가/도시 테스트 실패: {e}")
        raise HTTPException(status_code=500, detail=f"테스트 실패: {str(e)}")


@router.post("/test-place-recommendation")
async def test_place_recommendation():
    """
    장소 추천 시스템 테스트
    """
    try:
        # 테스트 요청 생성
        test_request = PlaceRecommendationRequest(
            country="한국",
            city="서울",
            total_duration=3,
            travelers_count=2,
            budget_range="중간",
            travel_style="문화탐방",
            special_requests="한국 전통 문화 체험을 원합니다"
        )
        
        # 장소 추천 실행
        response = await place_recommendation_service.generate_place_recommendations(test_request)
        
        return {
            "success": True,
            "message": "장소 추천 테스트 완료",
            "test_request": test_request.model_dump(),
            "recommendation_response": response.model_dump()
        }
        
    except Exception as e:
        logger.error(f"장소 추천 테스트 실패: {e}")
        raise HTTPException(status_code=500, detail=f"테스트 실패: {str(e)}")


@router.get("/check-prompts")
async def check_prompts():
    """
    프롬프트 테이블 확인
    """
    try:
        # 주요 프롬프트들 확인
        prompt_names = ["place_recommendation_v1", "itinerary_generation_v1"]
        results = {}
        
        for prompt_name in prompt_names:
            try:
                prompt_value = await supabase_service.get_master_prompt(prompt_name)
                results[prompt_name] = {
                    "exists": True,
                    "length": len(prompt_value),
                    "preview": prompt_value[:200] + "..." if len(prompt_value) > 200 else prompt_value
                }
            except ValueError as e:
                results[prompt_name] = {
                    "exists": False,
                    "error": str(e)
                }
        
        return {
            "success": True,
            "prompts": results,
            "supabase_connected": supabase_service.is_connected()
        }
        
    except Exception as e:
        logger.error(f"프롬프트 확인 실패: {e}")
        raise HTTPException(status_code=500, detail=f"프롬프트 확인 실패: {str(e)}")


@router.get("/health-v6")
async def health_check_v6():
    """
    v6.0 시스템 전체 상태 확인
    """
    try:
        status = {
            "version": "6.0",
            "supabase_connected": supabase_service.is_connected(),
            "features": {
                "countries_cities_tables": True,
                "cached_places_table": True,
                "prompts_table": True,
                "duplicate_prevention": True,
                "dynamic_prompts": True
            }
        }
        
        # 추가 테스트
        if status["supabase_connected"]:
            try:
                # 테스트 국가 생성 시도
                test_country_id = await supabase_service.get_or_create_country("테스트국가")
                status["database_write_test"] = True
                status["test_country_id"] = test_country_id
            except Exception as e:
                status["database_write_test"] = False
                status["database_error"] = str(e)
        
        return status
        
    except Exception as e:
        logger.error(f"v6.0 헬스체크 실패: {e}")
        raise HTTPException(status_code=500, detail=f"헬스체크 실패: {str(e)}")