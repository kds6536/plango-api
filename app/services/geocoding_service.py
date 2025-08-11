import httpx
import logging
from typing import Dict, Any, Optional, List

from app.config import settings


logger = logging.getLogger(__name__)


class GeocodingService:
    """Google Geocoding API 기반의 위치 표준화 서비스"""

    def __init__(self, api_key: Optional[str] = None) -> None:
        # Railway에서는 MAPS_PLATFORM_API_KEY를 사용
        self.api_key = api_key or getattr(settings, "MAPS_PLATFORM_API_KEY", None) or getattr(settings, "GOOGLE_MAPS_API_KEY", None)
        if not self.api_key:
            logger.warning("⚠️ GeocodingService: API Key가 설정되지 않았습니다.")

    async def _request(self, address: str, language: str = "en") -> Dict[str, Any]:
        if not self.api_key:
            return {"results": []}
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": address,
            "language": language,
            "key": self.api_key,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            return r.json()

    @staticmethod
    def _extract_components(result: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """
        address_components에서 국가/주(광역)/도시를 영문으로 추출
        - country: types=['country']
        - region: types includes 'administrative_area_level_1'
        - city: prefer 'locality', fallback to 'administrative_area_level_2'
        """
        comps: List[Dict[str, Any]] = result.get("address_components", [])
        def get_name(types: List[str]) -> Optional[str]:
            return next((c.get("long_name") for c in comps if set(types).issubset(set(c.get("types", [])))), None)

        country = get_name(["country"]) or None
        region = get_name(["administrative_area_level_1"]) or None
        # 도시: locality 우선, 없으면 administrative_area_level_2로 폴백
        city = get_name(["locality"]) or get_name(["administrative_area_level_2"]) or None
        return {"country": country, "region": region, "city": city}

    async def standardize_location(self, country: str, city: str) -> Dict[str, Any]:
        """사용자 입력(country, city)을 영문 표준명으로 정규화"""
        try:
            query = f"{country} {city}".strip()
            # 요청 직전 로그
            logger.info(f"Geocoding API에 주소 요청: '{query}'")
            data = await self._request(query, language="en")
            # 응답 직후 로그
            try:
                results_len = len(data.get("results", []))
            except Exception:
                results_len = 0
            logger.info(f"Geocoding API 응답 결과 수: {results_len}개")
            logger.debug(f"Geocoding API 전체 응답: {data}")
            results: List[Dict[str, Any]] = data.get("results", [])

            if not results:
                status = "NOT_FOUND"
                logger.info(f"최종 정규화 상태: '{status}'")
                return {"status": status}

            if len(results) == 1:
                comp = self._extract_components(results[0])
                status = "SUCCESS"
                logger.info(f"최종 정규화 상태: '{status}'")
                return {
                    "status": status,
                    "data": {
                        "country": comp.get("country"),
                        "region": comp.get("region"),
                        "city": comp.get("city"),
                    },
                }

            # 여러 개일 경우: formatted_address 제공
            options = [r.get("formatted_address") for r in results if r.get("formatted_address")]
            status = "AMBIGUOUS"
            logger.info(f"최종 정규화 상태: '{status}', 후보 {len(options)}개")
            return {"status": status, "options": options[:10]}
        except Exception as e:
            logger.error(f"Geocoding 표준화 실패: {e}")
            status = "NOT_FOUND"
            logger.info(f"최종 정규화 상태: '{status}' (예외 발생)")
            return {"status": status}


# 전역 인스턴스
geocoding_service = GeocodingService()


