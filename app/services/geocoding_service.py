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
        from app.services.api_key_manager import api_key_manager
        
        # API 키 매니저를 통해 최적의 키 선택
        if api_key:
            self.api_key = api_key
            key_source = "provided"
        else:
            self.api_key = api_key_manager.get_best_key_for_service("geocoding")
            key_source = "api_key_manager"
        
        # 🚨 디버깅: 실제 사용되는 키 로깅
        if self.api_key:
            logger.info(f"🔑 [GEOCODING_API_KEY_SOURCE] 사용 중인 키 소스: {key_source}")
            logger.info(f"🔑 [GEOCODING_API_KEY_PREFIX] 키 앞 20자: {self.api_key[:20]}...")
        else:
            logger.error("❌ [GEOCODING_NO_API_KEY] 사용 가능한 API 키가 없습니다")
        
        self.gmaps = None
        self.api_key_manager = api_key_manager
        
        if self.api_key:
            try:
                self.gmaps = googlemaps.Client(key=self.api_key)
                logger.info("✅ Google Geocoding 클라이언트 초기화 성공")
            except Exception as e:
                logger.error(f"💥 Google Geocoding 클라이언트 초기화 실패: {e}")
        else:
            logger.warning("⚠️ 사용 가능한 API 키가 없습니다.")

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

    def remove_duplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        지오코딩 결과에서 중복된 결과를 제거합니다.
        """
        if len(results) <= 1:
            return results
        
        logger.info(f"🔧 [DUPLICATE_REMOVAL] 총 {len(results)}개 결과에서 중복 제거 시작...")
        
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
        
        # 중복 제거: 동일한 지역의 중복 결과 필터링
        unique_results = []
        seen_locations = set()
        
        for result in administrative_results:
            # 좌표 기반으로 중복 확인 (소수점 2자리까지만 비교하여 근접한 위치는 동일하게 처리)
            lat = result.get("lat")
            lng = result.get("lng")
            
            if lat is not None and lng is not None:
                # 좌표를 소수점 2자리로 반올림하여 근접한 위치를 동일하게 처리
                location_key = (round(lat, 2), round(lng, 2))
                
                if location_key not in seen_locations:
                    seen_locations.add(location_key)
                    unique_results.append(result)
                    logger.info(f"  ✅ [UNIQUE_LOCATION] 고유 위치 추가: {result.get('formatted_address')} ({lat:.2f}, {lng:.2f})")
                else:
                    logger.info(f"  🔄 [DUPLICATE_LOCATION] 중복 위치 제거: {result.get('formatted_address')} ({lat:.2f}, {lng:.2f})")
            else:
                # 좌표가 없는 경우 formatted_address로 중복 확인
                address = result.get("formatted_address", "")
                if address not in seen_locations:
                    seen_locations.add(address)
                    unique_results.append(result)
                    logger.info(f"  ✅ [UNIQUE_ADDRESS] 고유 주소 추가: {address}")
                else:
                    logger.info(f"  🔄 [DUPLICATE_ADDRESS] 중복 주소 제거: {address}")
        
        logger.info(f"🔧 [DUPLICATE_REMOVAL] 중복 제거 완료: {len(results)}개 → {len(unique_results)}개")
        return unique_results

    def is_ambiguous_location(self, results: List[Dict[str, Any]]) -> bool:
        """
        지오코딩 결과가 동명 지역인지 판단합니다.
        중복된 결과는 제거하고 실제 서로 다른 지역만 동명 지역으로 판단합니다.
        """
        if len(results) <= 1:
            logger.info(f"🔍 [AMBIGUOUS_CHECK] 결과 {len(results)}개 - 동명 지역 아님")
            return False
        
        logger.info(f"🔍 [AMBIGUOUS_CHECK] 총 {len(results)}개 결과에서 동명 지역 여부 확인 중...")
        
        # 중복 제거된 결과로 동명 지역 여부 판단
        unique_results = self.remove_duplicate_results(results)
        
        is_ambiguous = len(unique_results) >= 2
        
        if is_ambiguous:
            logger.warning(f"⚠️ [AMBIGUOUS_DETECTED] 실제 동명 지역 감지! 고유 결과 {len(unique_results)}개")
            for i, result in enumerate(unique_results):
                logger.warning(f"  🏛️ [OPTION_{i+1}] {result.get('formatted_address')}")
        else:
            logger.info(f"✅ [NOT_AMBIGUOUS] 동명 지역 아님 (중복 제거 후 고유 결과 {len(unique_results)}개)")
        
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