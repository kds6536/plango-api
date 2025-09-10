"""
Google Geocoding API 서비스
동명 지역 구분을 위한 지오코딩 서비스
"""

import logging
from typing import List, Dict, Any, Optional
import googlemaps
from app.config import settings

logger = logging.getLogger(__name__)

class GeocodingService:
    def __init__(self, api_key: Optional[str] = None):
        """GeocodingService 초기화"""
        backend_key = getattr(settings, "MAPS_PLATFORM_API_KEY_BACKEND", None)
        google_key = getattr(settings, "GOOGLE_MAPS_API_KEY", None)
        
        self.api_key = api_key or backend_key or google_key
        
        # 🚨 디버깅: 실제 사용되는 키 로깅
        if self.api_key:
            key_source = "provided" if api_key else ("BACKEND" if backend_key else "GOOGLE")
            logger.info(f"🔑 [GEOCODING_API_KEY_SOURCE] 사용 중인 키 소스: {key_source}")
            logger.info(f"🔑 [GEOCODING_API_KEY_PREFIX] 키 앞 20자: {self.api_key[:20]}...")
        else:
            logger.error("❌ [GEOCODING_NO_API_KEY] 사용 가능한 API 키가 없습니다")
        self.gmaps = None
        if self.api_key:
            try:
                self.gmaps = googlemaps.Client(key=self.api_key)
                logger.info("✅ Google Geocoding 클라이언트 초기화 성공")
            except Exception as e:
                logger.error(f"💥 Google Geocoding 클라이언트 초기화 실패: {e}")
        else:
            logger.warning("⚠️ MAPS_PLATFORM_API_KEY_BACKEND가 설정되지 않았습니다.")

    async def get_geocode_results(self, location_query: str) -> List[Dict[str, Any]]:
        """
        지역명으로 지오코딩 결과를 가져옵니다.
        동명 지역이 있는 경우 여러 결과를 반환합니다.
        """
        try:
            if not self.gmaps:
                logger.error("❌ [GEOCODING_CLIENT_ERROR] Google Maps 클라이언트가 초기화되지 않았습니다.")
                raise Exception("Google Maps 클라이언트 초기화 실패")

            logger.info(f"🌍 [GEOCODING_API_CALL] Geocoding API 호출 시작: '{location_query}'")
            
            # Geocoding API 호출
            geocode_results = self.gmaps.geocode(location_query, language='ko')
            
            logger.info(f"📊 [GEOCODING_RAW_RESULTS] 원본 결과 수: {len(geocode_results)}")
            
            if not geocode_results:
                logger.warning(f"⚠️ [GEOCODING_NO_RESULTS] 지오코딩 결과가 없습니다: {location_query}")
                raise Exception(f"'{location_query}'에 대한 지오코딩 결과가 없습니다")

            # 결과를 표준화된 형태로 변환
            standardized_results = []
            for i, result in enumerate(geocode_results):
                try:
                    logger.info(f"🔍 [GEOCODING_RESULT_{i+1}] 결과 {i+1} 처리 중...")
                    
                    standardized_result = {
                        "place_id": result.get("place_id"),
                        "formatted_address": result.get("formatted_address"),
                        "display_name": result.get("formatted_address"),
                        "geometry": result.get("geometry"),
                        "types": result.get("types", []),
                        "address_components": result.get("address_components", [])
                    }
                    
                    # 위도, 경도 추출
                    if result.get("geometry", {}).get("location"):
                        location = result["geometry"]["location"]
                        standardized_result["lat"] = location.get("lat")
                        standardized_result["lng"] = location.get("lng")
                        logger.info(f"📍 [GEOCODING_RESULT_{i+1}] 좌표: {standardized_result['lat']}, {standardized_result['lng']}")
                    
                    # 주소 구성요소 로깅
                    address_components = result.get("address_components", [])
                    admin_areas = []
                    for component in address_components:
                        types = component.get("types", [])
                        if any(t in types for t in ["administrative_area_level_1", "administrative_area_level_2", "locality"]):
                            admin_areas.append(component.get("long_name"))
                    
                    logger.info(f"🏛️ [GEOCODING_RESULT_{i+1}] 행정구역: {' > '.join(admin_areas)}")
                    logger.info(f"📝 [GEOCODING_RESULT_{i+1}] 전체 주소: {standardized_result['formatted_address']}")
                    
                    standardized_results.append(standardized_result)
                    
                except Exception as result_error:
                    logger.error(f"❌ [GEOCODING_RESULT_{i+1}_ERROR] 결과 {i+1} 처리 실패: {result_error}")
                    continue

            logger.info(f"✅ [GEOCODING_SUCCESS] 지오코딩 결과 {len(standardized_results)}개 반환: {location_query}")
            
            # 결과가 없으면 예외 발생
            if not standardized_results:
                raise Exception("유효한 지오코딩 결과를 처리할 수 없습니다")
                
            return standardized_results

        except Exception as e:
            logger.error(f"❌ [GEOCODING_API_ERROR] 지오코딩 API 호출 실패: {e}")
            # 예외를 다시 발생시켜서 상위에서 폴백 처리할 수 있도록 함
            raise Exception(f"Geocoding API 실패: {str(e)}")

    def is_ambiguous_location(self, results: List[Dict[str, Any]]) -> bool:
        """
        지오코딩 결과가 동명 지역인지 판단합니다.
        """
        if len(results) <= 1:
            logger.info(f"🔍 [AMBIGUOUS_CHECK] 결과 {len(results)}개 - 동명 지역 아님")
            return False
        
        logger.info(f"🔍 [AMBIGUOUS_CHECK] 총 {len(results)}개 결과에서 동명 지역 여부 확인 중...")
        
        # 행정구역 레벨의 결과만 필터링 (도시, 구, 군 등)
        administrative_results = []
        for i, result in enumerate(results):
            types = result.get("types", [])
            admin_types = [t for t in types if t in ["locality", "administrative_area_level_1", "administrative_area_level_2", "sublocality"]]
            
            if admin_types:
                administrative_results.append(result)
                logger.info(f"  📍 [ADMIN_RESULT_{i+1}] 행정구역 결과: {result.get('formatted_address')} (타입: {admin_types})")
            else:
                logger.info(f"  🏢 [NON_ADMIN_RESULT_{i+1}] 비행정구역 결과: {result.get('formatted_address')} (타입: {types})")
        
        is_ambiguous = len(administrative_results) >= 2
        
        if is_ambiguous:
            logger.warning(f"⚠️ [AMBIGUOUS_DETECTED] 동명 지역 감지! 행정구역 결과 {len(administrative_results)}개")
            for i, result in enumerate(administrative_results):
                logger.warning(f"  🏛️ [OPTION_{i+1}] {result.get('formatted_address')}")
        else:
            logger.info(f"✅ [NOT_AMBIGUOUS] 동명 지역 아님 (행정구역 결과 {len(administrative_results)}개)")
        
        return is_ambiguous

    def format_location_options(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        지오코딩 결과를 프론트엔드에서 사용할 수 있는 형태로 포맷팅합니다.
        """
        options = []
        for result in results:
            # 주소 구성요소에서 더 명확한 이름 생성
            address_components = result.get("address_components", [])
            
            # 시/도, 구/군 정보 추출
            city_info = []
            for component in address_components:
                types = component.get("types", [])
                if "locality" in types or "administrative_area_level_2" in types:
                    city_info.append(component.get("long_name"))
                elif "administrative_area_level_1" in types:
                    city_info.append(component.get("long_name"))
            
            # 더 명확한 표시명 생성
            display_name = result.get("formatted_address", "")
            if city_info:
                display_name = " ".join(city_info)
            
            option = {
                "place_id": result.get("place_id"),
                "display_name": display_name,
                "formatted_address": result.get("formatted_address"),
                "lat": result.get("lat"),
                "lng": result.get("lng")
            }
            options.append(option)
        
        return options