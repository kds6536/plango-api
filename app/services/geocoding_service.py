"""
Google Geocoding API 서비스
동명 지역 구분을 위한 지오코딩 서비스
"""

import logging
from typing import List, Dict, Any, Optional
import googlemaps
from app.config import settings

# 커스텀 예외 클래스
class UserInputError(Exception):
    """사용자 입력 오류 (400 에러로 처리)"""
    pass

class SystemError(Exception):
    """시스템 오류 (폴백으로 처리)"""
    pass

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
        
        예외 처리:
        - UserInputError: 사용자 입력 오류 (ZERO_RESULTS)
        - SystemError: 시스템 오류 (API 키, 네트워크 등)
        """
        try:
            if not self.gmaps:
                logger.error("❌ [GEOCODING_CLIENT_ERROR] Google Maps 클라이언트가 초기화되지 않았습니다.")
                raise SystemError("Google Maps 클라이언트 초기화 실패")

            logger.info(f"🌍 [GEOCODING_API_CALL] Geocoding API 호출 시작: '{location_query}'")
            
            # Geocoding API 호출
            geocode_results = self.gmaps.geocode(location_query, language='ko')
            
            logger.info(f"📊 [GEOCODING_RAW_RESULTS] 원본 결과 수: {len(geocode_results)}")
            
            # 🚨 중요: 결과가 없는 경우 사용자 입력 오류로 처리
            if not geocode_results:
                logger.warning(f"⚠️ [GEOCODING_ZERO_RESULTS] 지역을 찾을 수 없습니다: {location_query}")
                raise UserInputError(f"'{location_query}' 지역을 찾을 수 없습니다. 정확한 도시 이름을 입력해주세요.")

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

        except UserInputError:
            # 사용자 입력 오류는 그대로 전파 (400 에러로 처리)
            raise
        except Exception as e:
            logger.error(f"❌ [GEOCODING_SYSTEM_ERROR] 지오코딩 시스템 오류: {e}")
            # 시스템 오류는 SystemError로 변환하여 폴백 처리 유도
            raise SystemError(f"Geocoding 시스템 오류: {str(e)}")

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
        
        # 스마트 중복 제거: 주소 패턴 분석으로 동명 지역 vs 같은 지역 구분
        unique_results = []
        seen_base_cities = set()
        
        for result in administrative_results:
            address = result.get("formatted_address", "")
            base_city = self._extract_base_city_name(address)
            
            logger.info(f"  🔍 [CITY_ANALYSIS] 주소: {address}")
            logger.info(f"  🔍 [CITY_ANALYSIS] 기본 도시명: {base_city}")
            
            if base_city not in seen_base_cities:
                seen_base_cities.add(base_city)
                unique_results.append(result)
                logger.info(f"  ✅ [UNIQUE_CITY] 고유 도시 추가: {base_city}")
            else:
                logger.info(f"  🔄 [DUPLICATE_CITY] 중복 도시 제거: {base_city}")
        
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

    def _extract_city_name(self, formatted_address: str) -> str:
        """
        formatted_address에서 도시명을 추출합니다.
        """
        if not formatted_address:
            return ""
        
        # 한국 주소 패턴: "대한민국 서울특별시" 또는 "대한민국 부산광역시"
        parts = formatted_address.split()
        
        for part in parts:
            if any(suffix in part for suffix in ["특별시", "광역시", "시", "도", "군", "구"]):
                return part
        
        # 패턴이 맞지 않으면 전체 주소 반환
        return formatted_address

    def _extract_base_city_name(self, formatted_address: str) -> str:
        """
        formatted_address에서 기본 도시명을 추출합니다.
        동명 지역 판단을 위한 핵심 로직:
        - "광주광역시" → "광주" 
        - "경기도 광주시" → "광주"
        - "서울특별시" → "서울"
        - "서울특별시 서울특별시" → "서울" (중복 제거)
        """
        if not formatted_address:
            return ""
        
        logger.info(f"    🔍 [BASE_CITY_EXTRACT] 원본 주소: {formatted_address}")
        
        # 한국 주소 패턴 처리
        if "대한민국" in formatted_address:
            return self._extract_korean_base_city(formatted_address)
        
        # 해외 주소 패턴 처리
        return self._extract_international_base_city(formatted_address)

    def _extract_korean_base_city(self, formatted_address: str) -> str:
        """
        한국 주소에서 기본 도시명 추출
        """
        parts = formatted_address.split()
        
        for part in parts:
            # 행정구역 접미사 제거하여 기본 도시명 추출
            if "특별시" in part:
                base_name = part.replace("특별시", "")
                logger.info(f"    🏛️ [KOREAN_CITY] 특별시 감지: {part} → {base_name}")
                return base_name
            elif "광역시" in part:
                base_name = part.replace("광역시", "")
                logger.info(f"    🏛️ [KOREAN_CITY] 광역시 감지: {part} → {base_name}")
                return base_name
            elif part.endswith("시"):
                # "광주시", "수원시" 등
                base_name = part.replace("시", "")
                logger.info(f"    🏛️ [KOREAN_CITY] 시 감지: {part} → {base_name}")
                return base_name
            elif part.endswith("도"):
                # "경기도" 등은 건너뛰고 다음 도시명 찾기
                continue
        
        # 패턴을 찾지 못한 경우 전체 주소 반환
        logger.info(f"    ⚠️ [KOREAN_CITY] 패턴 미발견, 전체 주소 사용: {formatted_address}")
        return formatted_address

    def _extract_international_base_city(self, formatted_address: str) -> str:
        """
        해외 주소에서 기본 도시명 추출
        예: "Paris, France" → "Paris"
        예: "Springfield, IL, USA" → "Springfield"
        """
        # 쉼표로 분리된 첫 번째 부분이 보통 도시명
        parts = formatted_address.split(",")
        if parts:
            base_city = parts[0].strip()
            logger.info(f"    🌍 [INTERNATIONAL_CITY] 해외 도시 감지: {formatted_address} → {base_city}")
            return base_city
        
        # 쉼표가 없는 경우 공백으로 분리된 첫 번째 단어
        words = formatted_address.split()
        if words:
            base_city = words[0]
            logger.info(f"    🌍 [INTERNATIONAL_CITY] 해외 도시 (단어): {formatted_address} → {base_city}")
            return base_city
        
        logger.info(f"    ⚠️ [INTERNATIONAL_CITY] 패턴 미발견: {formatted_address}")
        return formatted_address