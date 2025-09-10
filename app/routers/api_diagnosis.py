"""
Railway 서버에서 Google API 진단을 위한 라우터
"""

from fastapi import APIRouter, HTTPException
import logging
import httpx
import json
from typing import Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/diagnosis", tags=["API Diagnosis"])

@router.get("/google-apis")
async def diagnose_google_apis():
    """
    Railway 서버에서 Google API 상태를 진단합니다.
    """
    try:
        backend_key = getattr(settings, "MAPS_PLATFORM_API_KEY_BACKEND", None)
        frontend_key = getattr(settings, "MAPS_PLATFORM_API_KEY", None)
        
        logger.info(f"🔍 [DIAGNOSIS] API 키 상태 확인")
        logger.info(f"  - Backend Key: {'있음' if backend_key else '없음'}")
        logger.info(f"  - Frontend Key: {'있음' if frontend_key else '없음'}")
        
        results = {
            "server_info": {
                "platform": "Railway",
                "backend_key_exists": bool(backend_key),
                "frontend_key_exists": bool(frontend_key),
                "backend_key_prefix": backend_key[:20] + "..." if backend_key else None,
                "frontend_key_prefix": frontend_key[:20] + "..." if frontend_key else None,
                "keys_are_same": backend_key == frontend_key if backend_key and frontend_key else False
            },
            "api_tests": {}
        }
        
        # 1. Geocoding API 테스트
        logger.info("🧪 [TEST] Geocoding API 테스트 시작")
        geocoding_result = await test_geocoding_api(backend_key)
        results["api_tests"]["geocoding"] = geocoding_result
        
        # 2. Places API (New) 테스트
        logger.info("🧪 [TEST] Places API (New) 테스트 시작")
        places_new_result = await test_places_new_api(backend_key)
        results["api_tests"]["places_new"] = places_new_result
        
        # 3. Directions API 테스트
        logger.info("🧪 [TEST] Directions API 테스트 시작")
        directions_result = await test_directions_api(backend_key)
        results["api_tests"]["directions"] = directions_result
        
        # 4. Places Text Search API 테스트
        logger.info("🧪 [TEST] Places Text Search API 테스트 시작")
        places_text_result = await test_places_text_api(backend_key)
        results["api_tests"]["places_text"] = places_text_result
        
        # 결과 분석
        working_apis = []
        failing_apis = []
        
        for api_name, result in results["api_tests"].items():
            if result.get("success", False):
                working_apis.append(api_name)
            else:
                failing_apis.append(api_name)
        
        results["summary"] = {
            "total_apis": len(results["api_tests"]),
            "working_apis": len(working_apis),
            "failing_apis": len(failing_apis),
            "working_list": working_apis,
            "failing_list": failing_apis,
            "overall_status": "healthy" if len(working_apis) > len(failing_apis) else "degraded"
        }
        
        logger.info(f"✅ [DIAGNOSIS_COMPLETE] 진단 완료: {len(working_apis)}/{len(results['api_tests'])} APIs 작동")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ [DIAGNOSIS_ERROR] 진단 중 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"진단 실패: {str(e)}")

async def test_geocoding_api(api_key: str) -> Dict[str, Any]:
    """Geocoding API 테스트"""
    result = {
        "api_name": "Geocoding API",
        "success": False,
        "status_code": None,
        "api_status": None,
        "error_message": None,
        "results_count": 0,
        "test_query": "광주, 대한민국"
    }
    
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": "광주, 대한민국",
            "key": api_key,
            "language": "ko"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            
            result["status_code"] = response.status_code
            
            if response.status_code == 200:
                data = response.json()
                result["api_status"] = data.get("status")
                result["results_count"] = len(data.get("results", []))
                result["error_message"] = data.get("error_message")
                
                if data.get("status") == "OK" and result["results_count"] > 0:
                    result["success"] = True
                    result["sample_result"] = data["results"][0].get("formatted_address")
                
            else:
                result["error_message"] = f"HTTP {response.status_code}"
                
    except Exception as e:
        result["error_message"] = str(e)
    
    return result

async def test_places_new_api(api_key: str) -> Dict[str, Any]:
    """Places API (New) 테스트"""
    result = {
        "api_name": "Places API (New)",
        "success": False,
        "status_code": None,
        "error_message": None,
        "results_count": 0,
        "test_query": "서울 맛집"
    }
    
    try:
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating"
        }
        payload = {
            "textQuery": "서울 맛집",
            "languageCode": "ko"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            result["status_code"] = response.status_code
            
            if response.status_code == 200:
                data = response.json()
                result["results_count"] = len(data.get("places", []))
                
                if result["results_count"] > 0:
                    result["success"] = True
                    result["sample_result"] = data["places"][0].get("displayName", {}).get("text")
                    
            else:
                try:
                    error_data = response.json()
                    result["error_message"] = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                    result["error_details"] = error_data.get("error", {}).get("details", [])
                except:
                    result["error_message"] = f"HTTP {response.status_code}"
                
    except Exception as e:
        result["error_message"] = str(e)
    
    return result

async def test_directions_api(api_key: str) -> Dict[str, Any]:
    """Directions API 테스트 (HTTP 직접 호출)"""
    result = {
        "api_name": "Directions API",
        "success": False,
        "status_code": None,
        "api_status": None,
        "error_message": None,
        "routes_count": 0,
        "test_query": "서울역 → 강남역"
    }
    
    try:
        url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            "origin": "서울역",
            "destination": "강남역",
            "key": api_key,
            "language": "ko"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            
            result["status_code"] = response.status_code
            
            if response.status_code == 200:
                data = response.json()
                result["api_status"] = data.get("status")
                result["routes_count"] = len(data.get("routes", []))
                result["error_message"] = data.get("error_message")
                
                if data.get("status") == "OK" and result["routes_count"] > 0:
                    result["success"] = True
                    route = data["routes"][0]
                    leg = route["legs"][0]
                    result["sample_result"] = f"{leg['duration']['text']}, {leg['distance']['text']}"
                elif data.get("status") == "REQUEST_DENIED":
                    result["error_message"] = f"REQUEST_DENIED: {data.get('error_message', 'API 키 제한 또는 권한 문제')}"
                else:
                    result["error_message"] = f"API Status: {data.get('status')}, Message: {data.get('error_message', 'N/A')}"
                
            else:
                result["error_message"] = f"HTTP {response.status_code}: {response.text[:200]}"
                
    except Exception as e:
        result["error_message"] = str(e)
    
    return result

async def test_places_text_api(api_key: str) -> Dict[str, Any]:
    """Places Text Search API 테스트"""
    result = {
        "api_name": "Places Text Search API (Legacy)",
        "success": False,
        "status_code": None,
        "api_status": None,
        "error_message": None,
        "results_count": 0,
        "test_query": "서울 맛집"
    }
    
    try:
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": "서울 맛집",
            "key": api_key,
            "language": "ko"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            
            result["status_code"] = response.status_code
            
            if response.status_code == 200:
                data = response.json()
                result["api_status"] = data.get("status")
                result["results_count"] = len(data.get("results", []))
                result["error_message"] = data.get("error_message")
                
                if data.get("status") == "OK" and result["results_count"] > 0:
                    result["success"] = True
                    result["sample_result"] = data["results"][0].get("name")
                
            else:
                result["error_message"] = f"HTTP {response.status_code}"
                
    except Exception as e:
        result["error_message"] = str(e)
    
    return result

@router.get("/server-info")
async def get_server_info():
    """
    Railway 서버 정보를 반환합니다.
    """
    try:
        import platform
        import os
        
        return {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "server_name": platform.node(),
            "environment_variables": {
                "MAPS_PLATFORM_API_KEY": "있음" if os.getenv("MAPS_PLATFORM_API_KEY") else "없음",
                "MAPS_PLATFORM_API_KEY_BACKEND": "있음" if os.getenv("MAPS_PLATFORM_API_KEY_BACKEND") else "없음",
                "RAILWAY_ENVIRONMENT": os.getenv("RAILWAY_ENVIRONMENT", "unknown"),
                "RAILWAY_SERVICE_NAME": os.getenv("RAILWAY_SERVICE_NAME", "unknown")
            },
            "request_headers_sample": {
                "user_agent": "FastAPI Server",
                "host": "Railway Server"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 정보 조회 실패: {str(e)}")

@router.post("/test-specific-api")
async def test_specific_api(api_name: str, test_data: Dict[str, Any] = None):
    """
    특정 API를 직접 테스트합니다.
    """
    try:
        backend_key = getattr(settings, "MAPS_PLATFORM_API_KEY_BACKEND", None)
        
        if not backend_key:
            raise HTTPException(status_code=500, detail="Backend API 키가 설정되지 않았습니다")
        
        if api_name == "geocoding":
            address = test_data.get("address", "서울") if test_data else "서울"
            result = await test_geocoding_api(backend_key)
            result["custom_query"] = address
            
        elif api_name == "places_new":
            query = test_data.get("query", "서울 맛집") if test_data else "서울 맛집"
            result = await test_places_new_api(backend_key)
            result["custom_query"] = query
            
        elif api_name == "directions":
            origin = test_data.get("origin", "서울역") if test_data else "서울역"
            destination = test_data.get("destination", "강남역") if test_data else "강남역"
            result = await test_directions_api(backend_key)
            result["custom_query"] = f"{origin} → {destination}"
            
        else:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 API: {api_name}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ [SPECIFIC_TEST_ERROR] {api_name} 테스트 실패: {e}")
        raise HTTPException(status_code=500, detail=f"테스트 실패: {str(e)}")