#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plango API Test Script
Tests all main API endpoints
"""

import requests
import json

def test_api():
    print("🔍 Plango API Test Started")
    print()
    
    base_url = "http://127.0.0.1:8005"
    
    # 1. Server basic status
    try:
        response = requests.get(f"{base_url}/")
        print(f"✅ Server Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()
    except Exception as e:
        print(f"❌ Server connection failed: {e}")
        print()
        return False
    
    # 2. Health API
    try:
        response = requests.get(f"{base_url}/api/v1/health")
        print(f"✅ Health API: {response.status_code}")
        print(f"Response: {response.json()}")
        print()
    except Exception as e:
        print(f"❌ Health API failed: {e}")
        print()
    
    # 3. Places API health check
    try:
        response = requests.get(f"{base_url}/api/v1/places/health")
        print(f"✅ Places API Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Google Places API: {data.get('google_places_api', 'unknown')}")
            print(f"Message: {data.get('message', '')}")
            print()
        else:
            print(f"Response: {response.text}")
            print()
    except Exception as e:
        print(f"❌ Places API test failed: {e}")
        print()
    
    # 4. OpenAPI schema check
    try:
        response = requests.get(f"{base_url}/openapi.json")
        if response.status_code == 200:
            openapi_data = response.json()
            paths = openapi_data.get('paths', {})
            
            print(f"📚 Total API endpoints: {len(paths)}")
            places_endpoints = [path for path in paths.keys() if 'places' in path]
            print(f"📍 Places endpoints: {len(places_endpoints)}")
            
            if places_endpoints:
                print("Places endpoints found:")
                for endpoint in places_endpoints:
                    print(f"  - {endpoint}")
            print()
        else:
            print(f"❌ OpenAPI schema failed: {response.status_code}")
            print()
    except Exception as e:
        print(f"❌ OpenAPI schema check failed: {e}")
        print()
    
    print("🎉 API test completed!")
    return True

if __name__ == "__main__":
    test_api() 