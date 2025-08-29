"""
Google Places API 서비스
실제 장소 정보를 Google Places API에서 가져오는 서비스
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import googlemaps
from app.config import settings
import httpx
import asyncio
import random

logger = logging.getLogger(__name__)

class GooglePlacesService:
    def __init__(self, api_key: Optional[str] = None):
        """
        GooglePlacesService 초기화
        - settings에서 API 키를 가져와 googlemaps.Client를 초기화합니다.
        """
        # Railway 변수명은 'MAPS_PLATFORM_API_KEY' 사용. settings에도 동일 키를 노출하고 있으므로 우선 사용.
        # 하위 호환을 위해 GOOGLE_MAPS_API_KEY가 설정되어 있으면 그것도 사용.
        self.api_key = api_key or getattr(settings, "MAPS_PLATFORM_API_KEY", None) or getattr(settings, "GOOGLE_MAPS_API_KEY", None)
        self.gmaps = None
        if self.api_key:
            try:
                self.gmaps = googlemaps.Client(key=self.api_key)
                logger.info("✅ Google Maps 클라이언트 초기화 성공")
            except Exception as e:
                logger.error(f"💥 Google Maps 클라이언트 초기화 실패: {e}")
        else:
            logger.warning("⚠️ MAPS_PLATFORM_API_KEY가 설정되지 않았습니다.")

    def _extract_photo_url(self, place: Dict[str, Any], max_height_px: int = 400) -> str:
        """Places API(New) 사진 리소스 이름으로 미디어 URL을 생성"""
        try:
            place_name = place.get("displayName", {}).get("text", "Unknown Place") if isinstance(place.get("displayName"), dict) else place.get("name", "Unknown Place")
            
            if not self.api_key:
                logger.warning(f"⚠️ API 키가 없어 사진 URL을 생성할 수 없습니다 - Place: {place_name}")
                return ""
                
            photos = place.get("photos") or []
            
            if photos and isinstance(photos, list) and len(photos) > 0:
                photo = photos[0]
                name = photo.get("name")
                
                if name and isinstance(name, str) and name.strip():
                    photo_url = f"https://places.googleapis.com/v1/{name}/media?maxHeightPx={max_height_px}&key={self.api_key}"
                    logger.info(f"✅ 사진 URL 생성 성공: {place_name}")
                    return photo_url
                else:
                    logger.debug("⚠️ 사진 이름이 유효하지 않음")
            else:
                logger.debug("⚠️ 사진 데이터가 없음")
        except Exception as e:
            logger.error(f"❌ 사진 URL 생성 실패 - Place: {place_name}: {e}")
            logger.info(f"[검증용 로그] Place: {place_name}, Generated Image URL: None (예외 발생)")
        return ""

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
        # Google Places API(New)는 textQuery에 문자열만 허용. radius/place_type 같은 필드는 body가 아닌 쿼리에 쓸 수 없으므로 생략.
        # languageCode만 함께 전달한다.
        data = {"textQuery": str(text_query), "languageCode": language_code}

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

    async def search_places(
        self,
        query: str,
        location: Optional[str] = None,
        radius: int = 5000,
        place_type: Optional[str] = None,
        language_code: str = "ko",
    ) -> List[Dict[str, Any]]:
        """
        기존 라우터/서비스에서 기대하는 인터페이스의 검색 함수.
        Google Places API(New) Text Search를 사용해 결과를 표준 구조로 반환한다.
        """
        if not self.api_key:
            logger.error("Google Maps API 키가 설정되지 않아 검색을 진행할 수 없습니다.")
            return []

        # 질의문 구성: location이 있으면 함께 붙여 정확도를 높인다
        text_query = f"{query} {location}".strip() if location else query

        fields = [
            "places.id",
            "places.displayName",
            "places.formattedAddress",
            "places.rating",
            "places.userRatingCount",
            "places.priceLevel",
            "places.primaryType",
            "places.primaryTypeDisplayName",
            "places.websiteUri",
            "places.location",
            "places.photos",
        ]

        try:
            result = await self.search_places_text(text_query=text_query, fields=fields, language_code=language_code)
            places = result.get("places", [])
            normalized: List[Dict[str, Any]] = []
            for place in places:
                normalized.append({
                    "place_id": place.get("id"),
                    "name": place.get("displayName", {}).get("text", "Unknown Place"),
                    "address": place.get("formattedAddress"),
                    "rating": place.get("rating", 0.0),
                    "user_ratings_total": place.get("userRatingCount", 0),
                    "price_level": place.get("priceLevel", 0),
                    "type": place.get("primaryType"),
                    "description": place.get("primaryTypeDisplayName", {}).get("text", ""),
                    "website": place.get("websiteUri", ""),
                    "lat": place.get("location", {}).get("latitude"),
                    "lng": place.get("location", {}).get("longitude"),
                    "photo_url": self._extract_photo_url(place),
                })

            # place_type이 주어지면 1차 필터링(응답의 primaryType 기준)
            if place_type:
                normalized = [p for p in normalized if (p.get("type") or "").endswith(place_type) or place_type in (p.get("type") or "")]

            return normalized
        except Exception as e:
            logger.error(f"검색 중 예외 발생: {e}")
            return []

    async def get_place_details(self, place_id: str, language_code: str = "ko") -> Dict[str, Any]:
        """장소 상세 정보 조회 (Places API New)"""
        if not self.api_key:
            logger.error("Google Maps API 키가 설정되지 않아 상세 조회를 진행할 수 없습니다.")
            return {}

        url = f"https://places.googleapis.com/v1/places/{place_id}"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": ",".join([
                "id",
                "displayName",
                "formattedAddress",
                "rating",
                "userRatingCount",
                "priceLevel",
                "websiteUri",
                "location",
                "primaryType",
                "primaryTypeDisplayName",
                "photos",
            ]),
        }
        params = {"languageCode": language_code}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                return {
                    "place_id": data.get("id"),
                    "name": data.get("displayName", {}).get("text"),
                    "address": data.get("formattedAddress"),
                    "rating": data.get("rating"),
                    "user_ratings_total": data.get("userRatingCount"),
                    "price_level": data.get("priceLevel"),
                    "website": data.get("websiteUri"),
                    "lat": data.get("location", {}).get("latitude"),
                    "lng": data.get("location", {}).get("longitude"),
                    "type": data.get("primaryType"),
                    "description": data.get("primaryTypeDisplayName", {}).get("text", ""),
                }
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP 오류 발생(상세): {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"상세 조회 중 예외 발생: {e}")
        return {}

    async def get_nearby_attractions(self, location: str, radius: int = 10000) -> List[Dict[str, Any]]:
        query = f"{location} 관광명소"
        return await self.search_places(query=query, location=location, radius=radius, place_type="tourist_attraction")

    async def get_nearby_restaurants(self, location: str, radius: int = 5000) -> List[Dict[str, Any]]:
        query = f"{location} 맛집"
        return await self.search_places(query=query, location=location, radius=radius, place_type="restaurant")

    async def parallel_search_by_categories(self, search_queries: Dict[str, str], 
                                           target_count_per_category: int = 10,
                                           city: Optional[str] = None,
                                           country: Optional[str] = None,
                                           language_code: str = "ko") -> Dict[str, List[Dict[str, Any]]]:
        """
        AI가 생성한 카테고리별 검색 쿼리를 병렬로 실행하고, 부족한 경우 재시도
        
        Args:
            search_queries: AI가 생성한 카테고리별 검색 쿼리
            target_count_per_category: 카테고리당 목표 장소 개수
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: 카테고리별 장소 목록
        """
        logger.info(f"🚀 [PARALLEL_SEARCH] 병렬 장소 검색 시작")
        logger.info(f"📋 [SEARCH_QUERIES] 검색 쿼리: {search_queries}")
        
        # 1단계: 4개 카테고리 병렬 검색
        initial_tasks = []
        categories = ["tourism", "food", "activity", "accommodation"]
        
        for category in categories:
            base_query = search_queries.get(category, f"{category} places")
            # 도시/국가 접두어 보강 (region까지 포함 가능하도록 city에 region+city가 들어왔다면 그대로 사용)
            location_prefix = " ".join([part for part in [city, country] if part])
            final_query = f"{location_prefix} {base_query}".strip() if location_prefix else base_query
            initial_tasks.append(self._search_category_with_fallback(category, final_query, language_code))
        
        # 병렬 실행
        initial_results = await asyncio.gather(*initial_tasks, return_exceptions=True)
        
        # 결과 정리
        categorized_results = {}
        retry_needed = []
        
        for i, result in enumerate(initial_results):
            category = categories[i]
            if isinstance(result, Exception):
                logger.error(f"❌ [SEARCH_ERROR] {category} 검색 실패: {result}")
                categorized_results[category] = []
                retry_needed.append(category)
            else:
                places_count = len(result)
                categorized_results[category] = result
                logger.info(f"✅ [SEARCH_SUCCESS] {category}: {places_count}개 장소 발견")
                
                # 목표 개수 미달 시 재시도 대상에 추가
                if places_count < target_count_per_category:
                    retry_needed.append(category)
                    logger.info(f"🔄 [RETRY_NEEDED] {category}: {places_count} < {target_count_per_category}, 재시도 필요")
        
        # 2단계: 부족한 카테고리 재시도
        if retry_needed:
            logger.info(f"🔁 [RETRY_START] 재시도 대상 카테고리: {retry_needed}")
            await self._retry_insufficient_categories(categorized_results, retry_needed, 
                                                   search_queries, target_count_per_category)
        
        # 3단계: 전체 중복 제거 후 카테고리별 정규화
        # 먼저 전체 장소에서 place_id 기준으로 중복 제거
        all_unique_places: Dict[str, Dict[str, Any]] = {}
        
        for category, places in categorized_results.items():
            for place in places:
                place_id = place.get("place_id") or place.get("id")
                if place_id and place_id not in all_unique_places:
                    # 카테고리 정보 보존하되, 첫 번째로 발견된 카테고리 우선
                    place["category"] = category
                    all_unique_places[place_id] = place
        
        # 카테고리별로 재분류
        normalized_results: Dict[str, List[Dict[str, Any]]] = {
            "tourism": [],
            "food": [],
            "activity": [],
            "accommodation": []
        }
        
        for place in all_unique_places.values():
            category = place.get("category", "tourism")
            if category in normalized_results:
                normalized_results[category].append(place)
        
        # 각 카테고리별로 평점 기준 정렬 후 상위 N개 선택
        for category in normalized_results:
            places = normalized_results[category]
            places.sort(key=lambda x: (x.get("rating", 0), x.get("user_ratings_total", 0)), reverse=True)
            normalized_results[category] = places[:target_count_per_category]

        # 최종 결과 로깅
        final_counts = {cat: len(places) for cat, places in normalized_results.items()}
        logger.info(f"🎯 [FINAL_RESULTS] 최종 장소 개수(정규화): {final_counts}")

        return normalized_results
    
    async def _search_category_with_fallback(self, category: str, query: str, language_code: str = "ko") -> List[Dict[str, Any]]:
        """단일 카테고리 검색 with 폴백"""
        # Google Places API (New) 공식 필드 마스크 형식
        fields = [
            "places.id",
            "places.displayName",
            "places.formattedAddress", 
            "places.rating",
            "places.userRatingCount",
            "places.priceLevel",
            "places.primaryTypeDisplayName",
            "places.websiteUri",
            "places.location",
            "places.photos",
            "places.editorialSummary",
        ]
        
        try:
            result = await self.search_places_text(query, fields, language_code)
            places = result.get("places", [])
            
            # 데이터 정제 (Google Places API New 응답 구조에 맞게)
            processed_places = []
            for place in places:
                # API 응답 구조: displayName.text, location.latitude 등
                processed_place = {
                    "place_id": place.get("id", f"{category}_{random.randint(1000, 9999)}"),
                    "name": place.get("displayName", {}).get("text", "Unknown Place"),
                    "address": place.get("formattedAddress", "주소 정보 없음"),
                    "rating": place.get("rating", 0.0),
                    "user_ratings_total": place.get("userRatingCount", 0),
                    "price_level": place.get("priceLevel", 2),
                    "category": category,
                    "description": place.get("editorialSummary", {}).get("text") or place.get("primaryTypeDisplayName", {}).get("text", ""),
                    "website": place.get("websiteUri", ""),
                    "lat": place.get("location", {}).get("latitude", 0.0),
                    "lng": place.get("location", {}).get("longitude", 0.0),
                    "photo_url": self._extract_photo_url(place),
                }
                processed_places.append(processed_place)
            
            return processed_places
            
        except Exception as e:
            logger.error(f"❌ [CATEGORY_SEARCH_ERROR] {category} 검색 실패: {e}")
            return []
    
    async def _retry_insufficient_categories(self, categorized_results: Dict[str, List[Dict[str, Any]]], 
                                           retry_categories: List[str], 
                                           original_queries: Dict[str, str],
                                           target_count: int):
        """부족한 카테고리에 대해 대체 검색어로 재시도"""
        
        # 대체 검색어 생성
        alternative_queries = {
            "tourism": ["landmarks", "museums", "cultural sites", "historical places", "attractions"],
            "food": ["restaurants", "cafes", "local cuisine", "dining", "food courts"],
            "activity": ["entertainment", "sports", "recreation", "outdoor activities", "fun"],
            "accommodation": ["hotels", "lodging", "guesthouses", "hostels", "resorts"]
        }
        
        retry_tasks = []
        for category in retry_categories:
            current_count = len(categorized_results[category])
            needed_count = target_count - current_count
            
            if needed_count > 0:
                # 원래 쿼리에서 도시명 추출
                original_query = original_queries.get(category, "")
                city_part = original_query.split()[0] if original_query else "Seoul"
                
                # 대체 검색어 선택
                alternatives = alternative_queries.get(category, [category])
                alt_query = f"{city_part} {random.choice(alternatives)}"
                
                logger.info(f"🔄 [RETRY] {category} 재시도: '{alt_query}' (필요: {needed_count}개)")
                retry_tasks.append(self._search_category_with_fallback(category, alt_query))
            else:
                retry_tasks.append(asyncio.sleep(0))  # 더미 태스크
        
        if retry_tasks:
            retry_results = await asyncio.gather(*retry_tasks, return_exceptions=True)
            
            # 재시도 결과를 기존 결과에 추가
            for i, category in enumerate(retry_categories):
                if i < len(retry_results) and not isinstance(retry_results[i], Exception):
                    additional_places = retry_results[i]
                    if additional_places:
                        # 중복 제거하면서 추가
                        existing_place_ids = {place.get("place_id") for place in categorized_results[category]}
                        for place in additional_places:
                            if place.get("place_id") not in existing_place_ids:
                                categorized_results[category].append(place)
                        
                        new_count = len(categorized_results[category])
                        logger.info(f"✅ [RETRY_SUCCESS] {category}: {new_count}개로 증가")

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
            # Google Places API (New) 공식 필드 마스크 형식
            fields = [
                "places.id",
                "places.displayName", 
                "places.formattedAddress",
                "places.rating",
                "places.userRatingCount",
                "places.priceLevel",
                "places.primaryTypeDisplayName",
                "places.takeout",
                "places.delivery", 
                "places.dineIn",
                "places.websiteUri",
                "places.location"
            ]
            tasks.append(self.search_places_text(query, fields))

        results = await asyncio.gather(*tasks)
        
        enriched_places = []
        for res in results:
            if res and "places" in res:
                for place in res["places"]:
                    # Google Places API (New) 응답 구조에 맞게 정보 추출
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
            # 동기 함수를 비동기로 실행 (이벤트 루프 블로킹 방지)
            import asyncio
            loop = asyncio.get_event_loop()
            directions_result = await loop.run_in_executor(
                None, 
                lambda: self.gmaps.directions(
                    origin=origin,
                    destination=destination,
                    waypoints=waypoints_intermediate,
                    optimize_waypoints=True,
                    mode="driving"
                )
            )
            return directions_result
        except Exception as e:
            logger.error(f"경로 최적화 중 오류 발생: {e}")
            return {}

    async def geocode_location(self, address: str) -> Optional[Dict[str, Any]]:
        """Google Geocoding API로 주소를 표준화된 지명으로 변환"""
        try:
            if not self.gmaps:
                logger.error("Google Maps 클라이언트가 초기화되지 않았습니다.")
                return None
            
            # 동기 함수를 비동기로 실행 (이벤트 루프 블로킹 방지)
            import asyncio
            loop = asyncio.get_event_loop()
            geocode_result = await loop.run_in_executor(None, self.gmaps.geocode, address)
            
            if geocode_result:
                logger.info(f"✅ [GEOCODE_SUCCESS] 주소 '{address}' 표준화 성공")
                return {'results': geocode_result}
            else:
                logger.warning(f"⚠️ [GEOCODE_NO_RESULT] 주소 '{address}' 표준화 결과 없음")
                return None
                
        except Exception as e:
            logger.error(f"❌ [GEOCODE_ERROR] 주소 '{address}' 표준화 실패: {e}")
            return None