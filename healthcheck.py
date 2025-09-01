#!/usr/bin/env python3
"""
Railway용 헬스체크 스크립트
curl 의존성 없이 Python으로 직접 HTTP 요청
"""
import os
import sys
import urllib.request
import urllib.error

def main():
    port = os.environ.get('PORT', '8000')
    url = f"http://localhost:{port}/api/v1/health"
    
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            if response.status == 200:
                print("Health check passed")
                sys.exit(0)
            else:
                print(f"Health check failed with status: {response.status}")
                sys.exit(1)
    except Exception as e:
        print(f"Health check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()