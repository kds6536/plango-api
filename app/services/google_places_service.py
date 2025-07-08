"""
Google Places API 서비스
실제 장소 정보를 Google Places API에서 가져오는 서비스
"""

import os
import logging
from typing import List, Dict, Optional, Any
import googlemaps
from googlemaps.exceptions import ApiError
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

class GooglePlacesService:
    """Google Places API를 사용하여 장소 정보를 가져오는 서비스"""
    
    def __init__(self):
        # --- Maps Platform API Key만 사용하도록 수정 ---
        self.api_key = settings.MAPS_PLATFORM_API_KEY
        if not self.api_key:
            logger.error("Maps Platform API Key가 설정되지 않았습니다.")
            raise ValueError("API 키가 누락되었습니다.")
        
        self.client = googlemaps.Client(key=self.api_key)
        self.session = httpx.AsyncClient()
    
    async def search_places(
        self, 
        query: str, 
        location: Optional[str] = None,
        radius: int = 5000,
        place_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        장소 검색
        
        Args:
            query: 검색할 장소명
            location: 검색 중심 위치 (위도, 경도 또는 도시명)
            radius: 검색 반경 (미터)
            place_type: 장소 타입 (restaurant, tourist_attraction 등)
            
        Returns:
            장소 정보 리스트
        """
        if not self.client:
            logger.error("Google Places API 클라이언트가 초기화되지 않았습니다.")
            return []
        
        try:
            # 위치 기반 검색
            if location:
                # 위치를 좌표로 변환 (필요한 경우)
                location_coords = await self._get_coordinates(location)
                if location_coords:
                    results = self.client.places_nearby(
                        location=location_coords,
                        radius=radius,
                        keyword=query,
                        type=place_type
                    )
                else:
                    # 텍스트 검색으로 대체
                    results = self.client.places(
                        query=f"{query} in {location}",
                        type=place_type
                    )
            else:
                # 일반 텍스트 검색
                results = self.client.places(
                    query=query,
                    type=place_type
                )
            
            # 결과 정리
            places = []
            if 'results' in results:
                for place in results['results'][:10]:  # 최대 10개 결과
                    place_info = self._format_place_info(place)
                    places.append(place_info)
            
            logger.info(f"장소 검색 완료: '{query}' - {len(places)}개 결과")
            return places
            
        except ApiError as e:
            logger.error(f"Google Places API 오류: {e}")
            return []
        except Exception as e:
            logger.error(f"장소 검색 중 오류 발생: {e}")
            return []
    
    async def get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        장소 상세 정보 조회
        
        Args:
            place_id: Google Places API 장소 ID
            
        Returns:
            장소 상세 정보
        """
        if not self.client:
            logger.error("Google Places API 클라이언트가 초기화되지 않았습니다.")
            return None
        
        try:
            result = self.client.place(
                place_id=place_id,
                fields=[
                    'name', 'formatted_address', 'geometry',
                    'rating', 'user_ratings_total', 'price_level',
                    'opening_hours', 'photos', 'reviews',
                    'international_phone_number', 'website', 'types'
                ]
            )
            
            if 'result' in result:
                return self._format_place_details(result['result'])
            
            logger.warning(f"장소 상세 정보를 찾을 수 없습니다: {place_id}")
            return None
            
        except ApiError as e:
            logger.error(f"Google Places API 오류: {e}")
            return None
        except Exception as e:
            logger.error(f"장소 상세 정보 조회 중 오류 발생: {e}")
            return None
    
    async def get_nearby_attractions(
        self, 
        location: str, 
        radius: int = 10000
    ) -> List[Dict[str, Any]]:
        """
        주변 관광명소 검색
        
        Args:
            location: 중심 위치
            radius: 검색 반경 (미터)
            
        Returns:
            주변 관광명소 리스트
        """
        return await self.search_places(
            query="관광명소",
            location=location,
            radius=radius,
            place_type="tourist_attraction"
        )
    
    async def get_nearby_restaurants(
        self, 
        location: str, 
        radius: int = 5000
    ) -> List[Dict[str, Any]]:
        """
        주변 음식점 검색
        
        Args:
            location: 중심 위치
            radius: 검색 반경 (미터)
            
        Returns:
            주변 음식점 리스트
        """
        return await self.search_places(
            query="맛집",
            location=location,
            radius=radius,
            place_type="restaurant"
        )
    
    async def _get_coordinates(self, location: str) -> Optional[tuple]:
        """
        위치명을 좌표로 변환
        
        Args:
            location: 위치명
            
        Returns:
            (위도, 경도) 튜플
        """
        if not self.client:
            return None
        
        try:
            geocode_result = self.client.geocode(location)
            if geocode_result:
                location_data = geocode_result[0]['geometry']['location']
                return (location_data['lat'], location_data['lng'])
            return None
        except Exception as e:
            logger.error(f"좌표 변환 중 오류 발생: {e}")
            return None
    
    def _format_place_info(self, place: Dict[str, Any]) -> Dict[str, Any]:
        """
        Google Places API 응답을 표준 형식으로 변환
        
        Args:
            place: Google Places API 응답
            
        Returns:
            표준 형식의 장소 정보
        """
        return {
            "place_id": place.get("place_id", ""),
            "name": place.get("name", ""),
            "address": place.get("vicinity", "") or place.get("formatted_address", ""),
            "rating": place.get("rating", 0),
            "rating_count": place.get("user_ratings_total", 0),
            "price_level": place.get("price_level", 0),
            "location": {
                "lat": place.get("geometry", {}).get("location", {}).get("lat", 0),
                "lng": place.get("geometry", {}).get("location", {}).get("lng", 0)
            },
            "types": place.get("types", []),
            "photos": [
                f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo['photo_reference']}&key={self.api_key}"
                for photo in place.get("photos", [])[:3]  # 최대 3개 사진
            ] if self.api_key else []
        }
    
    def _format_place_details(self, place: Dict[str, Any]) -> Dict[str, Any]:
        """
        Google Places API 상세 정보를 표준 형식으로 변환
        
        Args:
            place: Google Places API 상세 응답
            
        Returns:
            표준 형식의 장소 상세 정보
        """
        return {
            "place_id": place.get("place_id", ""),
            "name": place.get("name", ""),
            "address": place.get("formatted_address", ""),
            "rating": place.get("rating", 0),
            "rating_count": place.get("user_ratings_total", 0),
            "price_level": place.get("price_level", 0),
            "location": {
                "lat": place.get("geometry", {}).get("location", {}).get("lat", 0),
                "lng": place.get("geometry", {}).get("location", {}).get("lng", 0)
            },
            "types": place.get("types", []),
            "phone": place.get("international_phone_number", ""),
            "website": place.get("website", ""),
            "opening_hours": place.get("opening_hours", {}).get("weekday_text", []),
            "photos": [
                f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo['photo_reference']}&key={self.api_key}"
                for photo in place.get("photos", [])[:5]  # 최대 5개 사진
            ] if self.api_key else [],
            "reviews": [
                {
                    "author": review.get("author_name", ""),
                    "rating": review.get("rating", 0),
                    "text": review.get("text", ""),
                    "time": review.get("relative_time_description", "")
                }
                for review in place.get("reviews", [])[:3]  # 최대 3개 리뷰
            ]
        }

    async def optimize_route(
        self, 
        places: List[Dict[str, Any]], 
        start_location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        여러 장소들을 최적 순서로 정렬
        
        Args:
            places: 방문할 장소들 (lat, lng 포함)
            start_location: 시작 지점 (선택사항)
            
        Returns:
            최적화된 경로 정보
        """
        if not self.client:
            logger.error("Google Maps API 클라이언트가 초기화되지 않았습니다.")
            return {}
        
        if len(places) < 2:
            logger.warning("최적화할 장소가 부족합니다.")
            return {}
        
        try:
            # 시작점 설정
            if start_location:
                origin = start_location
            else:
                # 첫 번째 장소를 시작점으로 사용
                first_place = places[0]
                origin = f"{first_place['lat']},{first_place['lng']}"
            
            # 마지막 지점 설정 (시작점과 동일하게 설정)
            destination = origin
            
            # 경유지 설정 (첫 번째와 마지막 제외)
            waypoints = []
            for place in places:
                waypoints.append(f"{place['lat']},{place['lng']}")
            
            # 구글 다이렉션 API 호출
            directions_result = self.client.directions(
                origin=origin,
                destination=destination,
                waypoints=waypoints,
                optimize_waypoints=True,  # 경로 최적화 활성화
                mode="walking",  # 도보 기준
                language="ko"
            )
            
            if not directions_result:
                logger.error("경로 최적화 결과를 받지 못했습니다.")
                return {}
            
            route = directions_result[0]
            
            # 최적화된 순서 추출
            optimized_order = []
            if 'waypoint_order' in route:
                waypoint_order = route['waypoint_order']
                for idx in waypoint_order:
                    optimized_order.append(places[idx])
            else:
                # 최적화 정보가 없으면 원래 순서 유지
                optimized_order = places
            
            # 총 거리와 시간 계산
            total_distance = 0
            total_duration = 0
            
            for leg in route['legs']:
                total_distance += leg['distance']['value']
                total_duration += leg['duration']['value']
            
            result = {
                "optimized_places": optimized_order,
                "total_distance": f"{total_distance/1000:.1f}km",
                "total_duration": f"{total_duration//60}분",
                "waypoint_order": route.get('waypoint_order', []),
                "route_details": route
            }
            
            logger.info(f"경로 최적화 완료: {len(places)}개 장소, 총 {result['total_distance']}")
            return result
            
        except ApiError as e:
            logger.error(f"Google Directions API 오류: {e}")
            return {}
        except Exception as e:
            logger.error(f"경로 최적화 중 오류 발생: {e}")
            return {}

    async def search_places_by_category(
        self, 
        city: str, 
        category: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        카테고리별 장소 검색 (브레인스토밍 단계용)
        
        Args:
            city: 도시명
            category: 카테고리 (관광, 맛집, 카페 등)
            limit: 최대 결과 수
            
        Returns:
            장소 정보 리스트
        """
        category_mapping = {
            "관광": "tourist_attraction",
            "맛집": "restaurant", 
            "카페": "cafe",
            "유적지": "museum",
            "문화": "museum",
            "놀거리": "amusement_park",
            "쇼핑": "shopping_mall"
        }
        
        place_type = category_mapping.get(category, "point_of_interest")
        query = f"{category} in {city}"
        
        return await self.search_places(
            query=query,
            location=city,
            place_type=place_type
        )

    async def enrich_places_data(self, place_names: List[str], city: str) -> List[Dict[str, Any]]:
        """
        장소 이름 목록을 실제 데이터로 강화 (2단계용)
        
        Args:
            place_names: 장소 이름 목록
            city: 도시명
            
        Returns:
            상세 정보가 포함된 장소 데이터 목록
        """
        # === Railway 로그: 2단계 시작 ===
        logger.info(f"🌍 [GOOGLE_PLACES_START] 구글 플레이스 API 데이터 강화 시작")
        logger.info(f"🏙️ [TARGET_CITY] {city}")
        logger.info(f"📋 [PLACE_NAMES] {place_names}")
        logger.info(f"🔢 [TOTAL_PLACES] {len(place_names)}개 장소 처리 예정")
        
        enriched_places = []
        
        for i, place_name in enumerate(place_names, 1):
            try:
                logger.info(f"🔍 [SEARCH_{i}/{len(place_names)}] '{place_name}' 검색 시작")
                
                # 장소 검색
                places = await self.search_places(
                    query=f"{place_name} {city}",
                    location=city
                )
                
                if places:
                    # 첫 번째 결과를 선택
                    place = places[0]
                    enriched_places.append(place)
                    logger.info(f"✅ [SEARCH_SUCCESS_{i}] '{place_name}' → '{place.get('name', 'N/A')}'")
                    logger.info(f"📍 [PLACE_DETAILS_{i}] 주소: {place.get('address', 'N/A')}, 평점: {place.get('rating', 'N/A')}")
                else:
                    logger.warning(f"⚠️ [SEARCH_EMPTY_{i}] '{place_name}' 검색 결과 없음")
                    
            except Exception as e:
                logger.error(f"❌ [SEARCH_ERROR_{i}] '{place_name}' 검색 실패: {str(e)}")
                continue
        
        # === Railway 로그: 2단계 완료 ===
        logger.info(f"🎉 [GOOGLE_PLACES_COMPLETE] 구글 플레이스 API 데이터 강화 완료")
        logger.info(f"📊 [SUCCESS_RATE] {len(enriched_places)}/{len(place_names)} 성공 ({len(enriched_places)/len(place_names)*100:.1f}%)")
        logger.info(f"🏛️ [ENRICHED_PLACES] {[place.get('name', 'N/A') for place in enriched_places]}")
        
        return enriched_places

# 싱글톤 인스턴스
google_places_service = GooglePlacesService() 