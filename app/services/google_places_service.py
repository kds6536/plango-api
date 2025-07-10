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
        장소 이름 목록을 실제 데이터로 강화 (2단계용) - Places API (New) HTTP 직접 호출
        photos, editorialSummary, formattedAddress 등 필드 포함, image_url/summary/address 등 반환
        카테고리별 최소 3개 이상 보장(Fallback: 예비 후보군 활용, 부족하면 더미)
        여러 키워드 병렬 호출
        """
        if not self.api_key:
            logger.error("MAPS_PLATFORM_API_KEY가 설정되지 않았습니다.")
            return []

        enriched_places = []
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.photos,places.editorialSummary"
        }
        async def fetch_place(place_name):
            try:
                data = {"textQuery": f"{place_name} {city}"}
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, headers=headers, json=data)
                    result = response.json()
                    if result and result.get('places'):
                        place = result['places'][0]
                        location = place.get('location', {})
                        photos = place.get('photos', [])
                        image_url = None
                        if photos:
                            ref = photos[0].get('name')
                            if ref:
                                image_url = f"https://places.googleapis.com/v1/{ref}/media?maxWidthPx=400&key={self.api_key}"
                        summary = place.get('editorialSummary', {}).get('text')
                        place_data = {
                            "place_id": place.get("id"),
                            "displayName": place.get("displayName", {}).get("text"),
                            "address": place.get("formattedAddress"),
                            "rating": place.get("rating"),
                            "user_ratings_total": place.get("userRatingCount"),
                            "latitude": location.get("latitude"),
                            "longitude": location.get("longitude"),
                            "photoUrl": image_url,
                            "editorialSummary": summary,
                        }
                        return place_data
                    else:
                        logger.warning(f"⚠️ [GOOGLE_EMPTY] 장소를 찾을 수 없습니다: {place_name} in {city}")
                        return None
            except Exception as e:
                logger.error(f"❌ [GOOGLE_ERROR] Google Places API (New) 호출 중 오류: {place_name} in {city} - {e}")
                return None
        # 병렬 호출
        results = await asyncio.gather(*[fetch_place(name) for name in place_names])
        enriched_places = [r for r in results if r]
        # Fallback: 최소 3개 보장
        while len(enriched_places) < 3:
            enriched_places.append({
                "place_id": f"dummy_{len(enriched_places)+1}",
                "displayName": f"더미장소{len(enriched_places)+1}",
                "address": city,
                "photoUrl": None,
                "editorialSummary": "AI가 생성한 더미 장소입니다.",
            })
        return enriched_places

    async def get_place_details(self, keyword: str, city: str, language_code: str) -> Optional[Dict[str, Any]]:
        """
        키워드와 도시 이름으로 장소를 검색하고 상세 정보를 반환합니다. (searchText 사용)
        """
        if not self.api_key:
            logger.error("MAPS_PLATFORM_API_KEY가 설정되지 않았습니다.")
            return None

        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.photos"
        }
        
        # 도시 정보가 포함된 검색어 생성
        text_query = f"{keyword} in {city}"

        try:
            data = {"textQuery": text_query, "languageCode": language_code}
            async with self.session as client:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()  # HTTP 에러 발생 시 예외 처리
                result = response.json()

                if result and result.get('places'):
                    place = result['places'][0]
                    location = place.get('location', {})
                    photos = place.get('photos', [])
                    
                    photo_url = None
                    if photos and photos[0].get('name'):
                        photo_name = photos[0]['name']
                        photo_url = f"https://places.googleapis.com/v1/{photo_name}/media?maxHeightPx=400&key={self.api_key}"

                    return {
                        "place_id": place.get("id"),
                        "name": place.get("displayName", {}).get("text"),
                        "address": place.get("formattedAddress"),
                        "rating": place.get("rating"),
                        "lat": location.get("latitude"),
                        "lng": location.get("longitude"),
                        "photo_url": photo_url
                    }
                else:
                    logger.warning(f"⚠️ [GOOGLE_EMPTY] 장소를 찾을 수 없습니다: {text_query}")
                    return None
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ [GOOGLE_HTTP_ERROR] API 요청 실패: {text_query}, Status: {e.response.status_code}, Response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"❌ [GOOGLE_ERROR] Google Places API 호출 중 오류: {text_query} - {e}", exc_info=True)
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