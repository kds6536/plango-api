"""여행 일정 서비스"""

from typing import Dict, Optional
import time
from fastapi import Depends

from app.schemas.itinerary import ItineraryRequest, ItineraryPlan, ItineraryResponse
from app.services.ai_service import AIService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ItineraryService:
    """여행 일정 관리 서비스"""
    
    def __init__(self, ai_service: AIService = Depends(AIService)):
        self.ai_service = ai_service
        # 실제로는 데이터베이스나 캐시를 사용
        self._storage = {}
    
    async def generate_travel_plans(self, request: ItineraryRequest) -> Dict[str, ItineraryPlan]:
        """여행 계획을 생성합니다"""
        start_time = time.time()
        
        try:
            logger.info(f"여행 일정 생성 시작: {request.destination}")
            
            # AI 서비스를 통한 여행 계획 생성
            plans = await self.ai_service.generate_travel_plans(request)
            
            generation_time = time.time() - start_time
            logger.info(f"여행 일정 생성 완료: {generation_time:.2f}초")
            
            return plans
            
        except Exception as e:
            logger.error(f"여행 일정 생성 실패: {str(e)}")
            raise
    
    async def get_itinerary(self, itinerary_id: str) -> Optional[ItineraryResponse]:
        """여행 일정을 조회합니다"""
        try:
            # 실제로는 데이터베이스에서 조회
            itinerary = self._storage.get(itinerary_id)
            if itinerary:
                logger.info(f"여행 일정 조회 성공: {itinerary_id}")
            else:
                logger.warning(f"여행 일정 없음: {itinerary_id}")
            
            return itinerary
            
        except Exception as e:
            logger.error(f"여행 일정 조회 실패: {str(e)}")
            raise
    
    async def save_itinerary(self, itinerary: ItineraryResponse) -> bool:
        """여행 일정을 저장합니다"""
        try:
            # 실제로는 데이터베이스에 저장
            self._storage[itinerary.id] = itinerary
            logger.info(f"여행 일정 저장 완료: {itinerary.id}")
            return True
            
        except Exception as e:
            logger.error(f"여행 일정 저장 실패: {str(e)}")
            return False 