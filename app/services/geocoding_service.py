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
        self.api_key = (
            api_key or 
            getattr(settings, "MAPS_PLATFORM_API_KEY_BACKEND", None) or 
            getattr(settings, "GOOGLE_MAPS_API_KEY", None) or
            getattr(settings, "MAPS_PLATFORM_API_KEY", None)
        )
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
                logger.error("Google Maps 클라이언트가 초기화되지 않았습니다.")
                return []

            # Geocoding API 호출
            geocode_results = self.gmaps.geocode(location_query, language='ko')
            
            if not geocode_results:
                logger.warning(f"지오코딩 결과가 없습니다: {location_query}")
                return []

            # 결과를 표준화된 형태로 변환
            standardized_results = []
            for result in geocode_results:
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
                
                standardized_results.append(standardized_result)

            logger.info(f"지오코딩 결과 {len(standardized_results)}개 반환: {location_query}")
            return standardized_results

        except Exception as e:
            logger.error(f"지오코딩 API 호출 실패: {e}")
            return []

    def is_ambiguous_location(self, results: List[Dict[str, Any]]) -> bool:
        """
        지오코딩 결과가 동명 지역인지 판단합니다.
        """
        if len(results) <= 1:
            return False
        
        # 행정구역 레벨의 결과만 필터링 (도시, 구, 군 등)
        administrative_results = []
        for result in results:
            types = result.get("types", [])
            if any(t in types for t in ["locality", "administrative_area_level_1", "administrative_area_level_2", "sublocality"]):
                administrative_results.append(result)
        
        # 행정구역 레벨의 결과가 2개 이상이면 동명 지역으로 판단
        return len(administrative_results) >= 2

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