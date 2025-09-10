"""
API 키 관리 및 우회 시스템
"""

import logging
import os
from typing import Optional, Dict, Any
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

class APIKeyManager:
    """API 키 관리 및 제한 우회를 위한 클래스"""
    
    def __init__(self):
        self.backend_key = getattr(settings, "MAPS_PLATFORM_API_KEY_BACKEND", None)
        self.frontend_key = getattr(settings, "GOOGLE_MAPS_API_KEY", None)
        self.unrestricted_key = os.getenv("GOOGLE_MAPS_UNRESTRICTED_KEY")  # 새로운 제한 없는 키
        
        logger.info(f"🔑 [API_KEY_MANAGER] 초기화 완료")
        logger.info(f"  - Backend Key: {'있음' if self.backend_key else '없음'}")
        logger.info(f"  - Frontend Key: {'있음' if self.frontend_key else '없음'}")
        logger.info(f"  - Unrestricted Key: {'있음' if self.unrestricted_key else '없음'}")
    
    def get_best_key_for_service(self, service_type: str) -> Optional[str]:
        """
        서비스 타입에 따라 최적의 API 키를 반환
        """
        if service_type in ["geocoding", "places", "directions"]:
            # 서버 사이드 API용 키 우선순위
            if self.unrestricted_key:
                logger.info(f"🔑 [KEY_SELECTION] {service_type}에 제한 없는 키 사용")
                return self.unrestricted_key
            elif self.backend_key:
                logger.info(f"🔑 [KEY_SELECTION] {service_type}에 백엔드 키 사용 (제한 있을 수 있음)")
                return self.backend_key
            else:
                logger.warning(f"⚠️ [KEY_SELECTION] {service_type}에 사용할 적절한 키가 없음")
                return self.frontend_key
        
        return self.frontend_key
    
    async def test_key_restrictions(self, api_key: str, service_type: str) -> Dict[str, Any]:
        """
        API 키의 제한사항을 테스트
        """
        test_results = {
            "key_valid": False,
            "has_restrictions": False,
            "error_message": None,
            "service_type": service_type
        }
        
        try:
            if service_type == "geocoding":
                # Geocoding API 테스트
                url = "https://maps.googleapis.com/maps/api/geocode/json"
                params = {
                    "address": "서울",
                    "key": api_key,
                    "language": "ko"
                }
                
            elif service_type == "places":
                # Places API 테스트 (Text Search)
                url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
                params = {
                    "query": "서울 맛집",
                    "key": api_key,
                    "language": "ko"
                }
            
            else:
                test_results["error_message"] = f"지원하지 않는 서비스 타입: {service_type}"
                return test_results
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "OK":
                        test_results["key_valid"] = True
                        test_results["has_restrictions"] = False
                        logger.info(f"✅ [KEY_TEST] {service_type} API 키 테스트 성공")
                    else:
                        test_results["error_message"] = data.get("error_message", data.get("status"))
                        logger.warning(f"⚠️ [KEY_TEST] {service_type} API 응답 오류: {test_results['error_message']}")
                
                elif response.status_code == 403:
                    test_results["has_restrictions"] = True
                    test_results["error_message"] = "API 키에 제한사항이 있습니다"
                    logger.warning(f"🚫 [KEY_TEST] {service_type} API 키 제한 감지")
                
                else:
                    test_results["error_message"] = f"HTTP {response.status_code}: {response.text}"
                    logger.error(f"❌ [KEY_TEST] {service_type} API 호출 실패: {test_results['error_message']}")
        
        except Exception as e:
            test_results["error_message"] = str(e)
            logger.error(f"❌ [KEY_TEST] {service_type} API 키 테스트 중 예외: {e}")
        
        return test_results
    
    async def find_working_key(self, service_type: str) -> Optional[str]:
        """
        작동하는 API 키를 찾아서 반환
        """
        keys_to_test = []
        
        if self.unrestricted_key:
            keys_to_test.append(("unrestricted", self.unrestricted_key))
        if self.backend_key:
            keys_to_test.append(("backend", self.backend_key))
        if self.frontend_key:
            keys_to_test.append(("frontend", self.frontend_key))
        
        logger.info(f"🔍 [KEY_SEARCH] {service_type}에 사용할 키 검색 중... ({len(keys_to_test)}개 후보)")
        
        for key_name, key_value in keys_to_test:
            logger.info(f"🧪 [KEY_TEST] {key_name} 키 테스트 중...")
            
            test_result = await self.test_key_restrictions(key_value, service_type)
            
            if test_result["key_valid"] and not test_result["has_restrictions"]:
                logger.info(f"✅ [KEY_FOUND] {service_type}에 사용할 키 발견: {key_name}")
                return key_value
            else:
                logger.warning(f"❌ [KEY_REJECTED] {key_name} 키 사용 불가: {test_result['error_message']}")
        
        logger.error(f"💥 [KEY_NOT_FOUND] {service_type}에 사용할 수 있는 키를 찾지 못했습니다")
        return None

# 전역 인스턴스
api_key_manager = APIKeyManager()