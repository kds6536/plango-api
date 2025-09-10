"""
Google Directions API 서비스
실제 장소 간 이동 시간과 거리를 계산합니다.
"""

import httpx
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
        
        # 🚨 [핵심 수정] googlemaps 라이브러리 대신 직접 HTTP 호출 사용
        logger.info("✅ Google Directions API 서비스 초기화 성공 (HTTP 직접 호출 방식)")

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
        if not self.api_key:
            logger.error("Google Directions API 키가 설정되지 않았습니다.")
            return None
            
        try:
            logger.info(f"🚗 [DIRECTIONS_API] 경로 계산: {origin} → {destination} ({mode})")
            
            # 🚨 [핵심 수정] HTTP 직접 호출로 변경
            url = "https://maps.googleapis.com/maps/api/directions/json"
            params = {
                "origin": origin,
                "destination": destination,
                "mode": mode,
                "language": language,
                "key": self.api_key
            }
            
            if departure_time:
                params["departure_time"] = departure_time
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                directions_result = response.json()
                
                if directions_result.get("status") != "OK":
                    logger.warning(f"⚠️ Directions API 오류: {directions_result.get('status')}")
                    logger.warning(f"📝 오류 메시지: {directions_result.get('error_message', 'N/A')}")
                    return None
                
                routes = directions_result.get("routes", [])
                if not routes:
                    logger.warning(f"⚠️ 경로를 찾을 수 없습니다: {origin} → {destination}")
                    return None
                    
                # 첫 번째 경로의 첫 번째 구간 정보 추출
                route = routes[0]
                legs = route.get("legs", [])
                if not legs:
                    logger.warning("⚠️ 경로 구간 정보가 없습니다")
                    return None
                
                leg = legs[0]
                
                result = {
                    "distance": {
                        "text": leg.get("distance", {}).get("text", "N/A"),
                        "value": leg.get("distance", {}).get("value", 0)  # 미터 단위
                    },
                    "duration": {
                        "text": leg.get("duration", {}).get("text", "N/A"),
                        "value": leg.get("duration", {}).get("value", 0)  # 초 단위
                    },
                    "start_address": leg.get("start_address", ""),
                    "end_address": leg.get("end_address", ""),
                    "steps": len(leg.get("steps", [])),
                    "mode": mode
                }
                
                duration_minutes = round(leg.get("duration", {}).get("value", 0) / 60)
                distance_km = round(leg.get("distance", {}).get("value", 0) / 1000, 1)
                
                logger.info(f"✅ 경로 계산 완료: {distance_km}km, {duration_minutes}분")
                
                return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ [DIRECTIONS_HTTP_ERROR] HTTP 오류: {e.response.status_code}")
            logger.error(f"📝 [ERROR_RESPONSE] 응답 내용: {e.response.text}")
            return None
        except httpx.TimeoutException:
            logger.error("⏰ [DIRECTIONS_TIMEOUT] Directions API 요청 시간 초과")
            return None
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
        if not self.api_key:
            logger.error("Google Distance Matrix API 키가 설정되지 않았습니다.")
            return None
            
        try:
            logger.info(f"🚗 [DISTANCE_MATRIX] 매트릭스 계산: {len(origins)}개 출발지 → {len(destinations)}개 도착지")
            
            # 🚨 [핵심 수정] HTTP 직접 호출로 변경
            url = "https://maps.googleapis.com/maps/api/distancematrix/json"
            params = {
                "origins": "|".join(origins),
                "destinations": "|".join(destinations),
                "mode": mode,
                "language": language,
                "key": self.api_key
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                matrix_result = response.json()
                
                if matrix_result.get('status') != 'OK':
                    logger.warning(f"⚠️ Distance Matrix API 오류: {matrix_result.get('status')}")
                    logger.warning(f"📝 오류 메시지: {matrix_result.get('error_message', 'N/A')}")
                    return None
                    
                logger.info("✅ Distance Matrix 계산 완료")
                return matrix_result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ [MATRIX_HTTP_ERROR] HTTP 오류: {e.response.status_code}")
            logger.error(f"📝 [ERROR_RESPONSE] 응답 내용: {e.response.text}")
            return None
        except httpx.TimeoutException:
            logger.error("⏰ [MATRIX_TIMEOUT] Distance Matrix API 요청 시간 초과")
            return None
        except Exception as e:
            logger.error(f"💥 Distance Matrix API 호출 중 오류 발생: {e}")
            return None

    def calculate_duration_minutes(self, duration_seconds: int) -> int:
        """초 단위 시간을 분 단위로 변환합니다."""
        return max(1, round(duration_seconds / 60))  # 최소 1분

    def calculate_distance_km(self, distance_meters: int) -> float:
        """미터 단위 거리를 킬로미터 단위로 변환합니다."""
        return round(distance_meters / 1000, 1)