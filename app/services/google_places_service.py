"""
Google Places API 서비스
실제 장소 정보를 Google Places API에서 가져오는 서비스
"""

import os
import logging
from typing import List, Dict, Any, Optional
import googlemaps
import httpx
from app.config import settings
import asyncio
import traceback

logger = logging.getLogger(__name__)


class GooglePlacesService:
    def __init__(self):
        self.api_key = settings.MAPS_PLATFORM_API_KEY
        self.gmaps = None
        if self.api_key:
            try:
                self.gmaps = googlemaps.Client(key=self.api_key)
                self.session = httpx.AsyncClient()
                logger.info("✅ Google Maps 클라이언트 초기화 성공")
            except Exception as e:
                logger.error(f"💥 Google Maps 클라이언트 초기화 실패: {e}")
        else:
            logger.warning("⚠️ MAPS_PLATFORM_API_KEY가 설정되지 않았습니다.")

    async def enrich_places_data(self, place_names: List[str], city: str) -> List[Dict[str, Any]]:
        """
        장소 이름 목록을 실제 데이터로 강화 (2단계용) - find_place 사용
        """
        if not self.gmaps:
            logger.error("Google Places API 클라이언트가 초기화되지 않았습니다.")
            return []

        enriched_places = []
        for place_name in place_names:
            try:
                result = await asyncio.to_thread(
                    self.gmaps.find_place,
                    query=f"{place_name} {city}",
                    language='ko',
                    fields=['place_id', 'name', 'formatted_address', 'rating', 'user_ratings_total', 'photos', 'geometry']
                )

                if result and result.get('candidates'):
                    place = result['candidates'][0]
                    location = place.get('geometry', {}).get('location', {})
                    place_data = {
                        "place_id": place.get("place_id"),
                        "name": place.get("name"),
                        "address": place.get("formatted_address"),
                        "rating": place.get("rating"),
                        "user_ratings_total": place.get("user_ratings_total"),
                        "latitude": location.get("lat"),
                        "longitude": location.get("lng"),
                    }
                    enriched_places.append(place_data)
                    logger.info(f"📍 [GOOGLE_SUCCESS] 장소 데이터 강화 완료: {place_name} -> {place.get('name')}")
                else:
                    logger.warning(f"⚠️ [GOOGLE_EMPTY] 장소를 찾을 수 없습니다: {place_name} in {city}")
            except Exception as e:
                logger.error("=" * 80)
                logger.error(f"❌ [GOOGLE_ERROR] Google Places API 호출 중 오류 발생")
                logger.error(f"🔎 [PLACE_NAME] {place_name}")
                logger.error(f"🏙️ [CITY] {city}")
                logger.error(f"🚨 [ERROR_TYPE] {type(e).__name__}")
                logger.error(f"📝 [ERROR_MESSAGE] {str(e)}")
                logger.error(f"🔗 [TRACEBACK] {traceback.format_exc()}")
                logger.error("=" * 80)
                continue
        
        return enriched_places

    async def get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        장소 ID로 상세 정보 가져오기
        """
        if not self.gmaps:
            logger.error("Google Places API 클라이언트가 초기화되지 않았습니다.")
            return None
        
        try:
            result = self.gmaps.place(
                place_id=place_id,
                fields=["name", "formatted_address", "rating", "user_ratings_total", "geometry", "photos", "reviews", "website", "opening_hours", "international_phone_number"],
                language="ko",
            )
            return result.get('result')
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ [GOOGLE_ERROR] Google Place Details API 호출 실패")
            logger.error(f"🔎 [PLACE_ID] {place_id}")
            logger.error(f"🚨 [ERROR_TYPE] {type(e).__name__}")
            logger.error(f"📝 [ERROR_MESSAGE] {str(e)}")
            logger.error(f"🔗 [TRACEBACK] {traceback.format_exc()}")
            logger.error("=" * 80)
            return None

    async def get_optimized_route(self, waypoints: List[str]) -> Dict:
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
                mode="driving",
                language="ko",
            )
            return directions_result[0] if directions_result else {}
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ [GOOGLE_ERROR] Google Directions API 호출 실패")
            logger.error(f"🗺️ [WAYPOINTS] {waypoints}")
            logger.error(f"🚨 [ERROR_TYPE] {type(e).__name__}")
            logger.error(f"📝 [ERROR_MESSAGE] {str(e)}")
            logger.error(f"🔗 [TRACEBACK] {traceback.format_exc()}")
            logger.error("=" * 80)
            return {}

google_places_service = GooglePlacesService() 