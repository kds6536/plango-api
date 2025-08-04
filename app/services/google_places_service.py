"""
Google Places API 서비스
실제 장소 정보를 Google Places API에서 가져오는 서비스
"""

import logging
from typing import List, Dict, Any, Optional
import googlemaps
from app.config import settings
import httpx
import asyncio

logger = logging.getLogger(__name__)

class GooglePlacesService:
    def __init__(self, api_key: Optional[str] = None):
        """
        GooglePlacesService 초기화
        - settings에서 API 키를 가져와 googlemaps.Client를 초기화합니다.
        """
        self.api_key = api_key or settings.MAPS_PLATFORM_API_KEY
        self.gmaps = None
        if self.api_key:
            try:
                self.gmaps = googlemaps.Client(key=self.api_key)
                logger.info("✅ Google Maps 클라이언트 초기화 성공")
            except Exception as e:
                logger.error(f"💥 Google Maps 클라이언트 초기화 실패: {e}")
        else:
            logger.warning("⚠️ MAPS_PLATFORM_API_KEY가 설정되지 않았습니다.")

    async def search_places_text(self, text_query: str, fields: List[str], language_code: str = "ko") -> Dict[str, Any]:
        """
        Google Places API (Text Search)를 사용하여 장소를 검색합니다.
        """
        if not self.api_key:
            logger.error("Google Maps API 키가 설정되지 않아 검색을 진행할 수 없습니다.")
            return {}

        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": ",".join(fields),
        }
        data = {"textQuery": text_query, "languageCode": language_code}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP 오류 발생: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"장소 검색 중 예외 발생: {e}")
        return {}

    async def enrich_places_data(self, place_names: List[str], city: str) -> List[Dict[str, Any]]:
        """
        장소 이름 목록을 받아 Google Places API로 각각의 상세 정보를 조회하고 보강합니다.
        """
        if not self.gmaps:
            logger.error("Google Maps 클라이언트가 초기화되지 않았습니다.")
            return []

        tasks = []
        for place_name in place_names:
            query = f"{place_name} in {city}"
            fields = [
                "id", "displayName", "formattedAddress", "rating", "userRatingCount",
                "priceLevel", "primaryTypeDisplayName", "takeout", "delivery",
                "dineIn", "websiteUri", "location"
            ]
            tasks.append(self.search_places_text(query, fields))

        results = await asyncio.gather(*tasks)
        
        enriched_places = []
        for res in results:
            if res and "places" in res:
                for place in res["places"]:
                    # 필요한 정보만 추출하여 새로운 딕셔너리 생성
                    enriched_place = {
                        "id": place.get("id"),
                        "displayName": place.get("displayName", {}).get("text"),
                        "formattedAddress": place.get("formattedAddress"),
                        "rating": place.get("rating"),
                        "userRatingCount": place.get("userRatingCount"),
                        "priceLevel": place.get("priceLevel"),
                        "primaryTypeDisplayName": place.get("primaryTypeDisplayName", {}).get("text"),
                        "websiteUri": place.get("websiteUri"),
                        "location": place.get("location"),
                        "services": {
                            "takeout": place.get("takeout"),
                            "delivery": place.get("delivery"),
                            "dineIn": place.get("dineIn"),
                        }
                    }
                    enriched_places.append(enriched_place)
        
        return enriched_places


    def get_optimized_route(self, waypoints: List[str]) -> Dict:
        """
        경유지를 포함한 최적화된 경로 반환
        """
        if not self.gmaps or len(waypoints) < 2:
            return {}
        
        origin = waypoints[0]
        destination = waypoints[-1]
        waypoints_intermediate = waypoints[1:-1]
        
        try:
            directions_result = self.gmaps.directions(
                origin=origin,
                destination=destination,
                waypoints=waypoints_intermediate,
                optimize_waypoints=True,
                mode="driving"
            )
            return directions_result
        except Exception as e:
            logger.error(f"경로 최적화 중 오류 발생: {e}")
            return {} 