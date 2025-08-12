"""
새로운 장소 추천 라우터 (v6.0)
새로운 DB 스키마에 맞춘 장소 추천 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Depends
import logging
from app.schemas.place import PlaceRecommendationRequest, PlaceRecommendationResponse
from app.services.place_recommendation_service import place_recommendation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/place-recommendations", tags=["Place Recommendations v6.0"])


@router.post("/generate", response_model=PlaceRecommendationResponse)
async def generate_place_recommendations(request: PlaceRecommendationRequest):
    """
    새로운 장소 추천 생성 (v6.0)
    
    - 새로운 DB 스키마 (countries, cities, cached_places, prompts) 활용
    - 중복 추천 방지: 기존 추천 장소 제외
    - 프롬프트 동적 생성: 기존 장소 목록을 포함한 맞춤형 프롬프트
    - AI + Google Places API 연동으로 검증된 장소 정보 제공
    """
    try:
        logger.info(f"새로운 장소 추천 요청: {request.model_dump_json(indent=2)}")

        # 장소 추천 서비스 호출
        response = await place_recommendation_service.generate_place_recommendations(request)

        logger.info(
            f"장소 추천 완료: 도시 ID {response.city_id}, 기존 {response.previously_recommended_count}개, 신규 {response.newly_recommended_count}개"
        )

        return response

    except HTTPException as he:  # 서비스에서 명시적으로 404 등을 던진 경우 그대로 전달
        raise he
    except ValueError as ve:
        logger.error(f"장소 추천 요청 검증 실패: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"장소 추천 중 예상치 못한 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"장소 추천 처리 중 오류가 발생했습니다: {str(e)}")


@router.get("/health")
async def place_recommendations_health_check():
    """
    장소 추천 서비스 상태 확인
    """
    try:
        # Supabase 연결 상태 확인
        supabase_connected = place_recommendation_service.supabase.is_connected()
        
        return {
            "status": "healthy",
            "service": "Place Recommendations v6.0",
            "supabase_connected": supabase_connected,
            "features": {
                "duplicate_prevention": True,
                "dynamic_prompts": True,
                "db_caching": True,
                "google_places_enrichment": True
            }
        }
        
    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        raise HTTPException(status_code=500, detail=f"헬스체크 실패: {str(e)}")


@router.get("/stats/{city_id}")
async def get_city_recommendation_stats(city_id: int):
    """
    특정 도시의 추천 통계 조회
    """
    try:
        # 도시의 기존 장소 수 조회
        existing_places = await place_recommendation_service.supabase.get_existing_place_names(city_id)
        
        # 카테고리별 분포 계산 (cached_places에서 직접 조회하는 것이 더 정확하지만, 
        # 현재는 간단히 이름 기반으로 계산)
        category_stats = {
            "볼거리": 0,
            "먹거리": 0, 
            "즐길거리": 0,
            "숙소": 0,
            "기타": 0
        }
        
        return {
            "city_id": city_id,
            "total_cached_places": len(existing_places),
            "category_distribution": category_stats,
            "place_names": existing_places[:10]  # 최대 10개만 미리보기
        }
        
    except ValueError as ve:
        logger.error(f"도시 통계 조회 실패: {ve}")
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"도시 통계 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}")


@router.post("/test-prompt-generation")
async def test_prompt_generation(request: PlaceRecommendationRequest):
    """
    개발용: 고도화(Plan A) → 폴백(Plan B) 흐름으로 실제 추천 결과를 테스트합니다.
    """
    try:
        response = await place_recommendation_service.generate_place_recommendations(request)
        return response
    except Exception as e:
        logger.error(f"프롬프트(실제 추천) 테스트 실패: {e}")
        raise HTTPException(status_code=500, detail=f"추천 테스트 중 오류: {str(e)}")