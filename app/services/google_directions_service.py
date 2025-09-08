"""
Google Directions API 서비스
실제 장소 간 이동 시간과 거리를 계산합니다.
"""

import googlemaps
from typing import Dict, Any, Optional, List
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GoogleDirectionsService:
    """Google Directions API를 사용한 경로 및 이동 시간 계산 서비스"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Google Directions API 클라이언트를 초기화합니다.
        
        Args:
            api_key: Google Maps API 키 (선택사항, 없으면 settings에서 가져옴)
        """
        # Backend API Key - Server-side use only, must be kept secret
        # This key should NOT have HTTP Referer restrictions
        backend_key = getattr(settings, "MAPS_PLATFORM_API_KEY_BACKEND", None)
        google_key = getattr(settings, "GOOGLE_MAPS_API_KEY", None)
        
        self.api_key = api_key or backend_key or google_key
        
        # 🚨 디버깅: 실제 사용되는 키 로깅
        if self.api_key:
            key_source = "provided" if api_key else ("BACKEND" if backend_key else "GOOGLE")
            logger.info(f"🔑 [DIRECTIONS_API_KEY_SOURCE] 사용 중인 키 소스: {key_source}")
            logger.info(f"🔑 [DIRECTIONS_API_KEY_PREFIX] 키 앞 20자: {self.api_key[:20]}...")
        else:
            logger.error("❌ [DIRECTIONS_NO_API_KEY] 사용 가능한 API 키가 없습니다")
        self.gmaps = None
        
        if self.api_key:
            try:
                self.gmaps = googlemaps.Client(key=self.api_key)
                logger.info("✅ Google Directions API 클라이언트 초기화 성공")
            except Exception as e:
                logger.error(f"💥 Google Directions API 클라이언트 초기화 실패: {e}")
        else:
            logger.warning("⚠️ MAPS_PLATFORM_API_KEY_BACKEND가 설정되지 않았습니다.")

    async def get_directions(
        self, 
        origin: str, 
        destination: str, 
        mode: str = "driving",
        language: str = "ko",
        departure_time: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        두 지점 간의 경로 정보를 가져옵니다.
        
        Args:
            origin: 출발지 (place_id:ChIJ... 또는 주소)
            destination: 도착지 (place_id:ChIJ... 또는 주소)
            mode: 이동 수단 ("driving", "walking", "transit", "bicycling")
            language: 응답 언어 코드
            departure_time: 출발 시간 (transit 모드에서 사용)
            
        Returns:
            경로 정보 딕셔너리 또는 None (실패 시)
        """
        if not self.gmaps:
            logger.error("Google Directions API 클라이언트가 초기화되지 않았습니다.")
            return None
            
        try:
            logger.info(f"🚗 [DIRECTIONS_API] 경로 계산: {origin} → {destination} ({mode})")
            
            # Google Directions API 호출
            directions_result = self.gmaps.directions(
                origin=origin,
                destination=destination,
                mode=mode,
                language=language,
                departure_time=departure_time
            )
            
            if not directions_result:
                logger.warning(f"⚠️ 경로를 찾을 수 없습니다: {origin} → {destination}")
                return None
                
            # 첫 번째 경로의 첫 번째 구간 정보 추출
            route = directions_result[0]
            leg = route['legs'][0]
            
            result = {
                "distance": {
                    "text": leg['distance']['text'],
                    "value": leg['distance']['value']  # 미터 단위
                },
                "duration": {
                    "text": leg['duration']['text'],
                    "value": leg['duration']['value']  # 초 단위
                },
                "start_address": leg['start_address'],
                "end_address": leg['end_address'],
                "steps": len(leg['steps']),
                "mode": mode
            }
            
            duration_minutes = round(leg['duration']['value'] / 60)
            distance_km = round(leg['distance']['value'] / 1000, 1)
            
            logger.info(f"✅ 경로 계산 완료: {distance_km}km, {duration_minutes}분")
            
            return result
            
        except Exception as e:
            logger.error(f"💥 Directions API 호출 중 오류 발생: {e}")
            return None

    async def get_travel_time_matrix(
        self, 
        origins: List[str], 
        destinations: List[str],
        mode: str = "driving",
        language: str = "ko"
    ) -> Optional[Dict[str, Any]]:
        """
        여러 지점 간의 이동 시간 매트릭스를 가져옵니다.
        
        Args:
            origins: 출발지 리스트
            destinations: 도착지 리스트
            mode: 이동 수단
            language: 응답 언어 코드
            
        Returns:
            거리/시간 매트릭스 또는 None (실패 시)
        """
        if not self.gmaps:
            logger.error("Google Directions API 클라이언트가 초기화되지 않았습니다.")
            return None
            
        try:
            logger.info(f"🚗 [DISTANCE_MATRIX] 매트릭스 계산: {len(origins)}개 출발지 → {len(destinations)}개 도착지")
            
            # Google Distance Matrix API 호출
            matrix_result = self.gmaps.distance_matrix(
                origins=origins,
                destinations=destinations,
                mode=mode,
                language=language
            )
            
            if matrix_result['status'] != 'OK':
                logger.warning(f"⚠️ Distance Matrix API 오류: {matrix_result['status']}")
                return None
                
            logger.info("✅ Distance Matrix 계산 완료")
            return matrix_result
            
        except Exception as e:
            logger.error(f"💥 Distance Matrix API 호출 중 오류 발생: {e}")
            return None

    def calculate_duration_minutes(self, duration_seconds: int) -> int:
        """초 단위 시간을 분 단위로 변환합니다."""
        return max(1, round(duration_seconds / 60))  # 최소 1분

    def calculate_distance_km(self, distance_meters: int) -> float:
        """미터 단위 거리를 킬로미터 단위로 변환합니다."""
        return round(distance_meters / 1000, 1)