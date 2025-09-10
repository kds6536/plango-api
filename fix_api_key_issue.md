# Google API 키 문제 해결 방안

## 문제 상황
현재 Google API 키에 리퍼러 제한이 설정되어 있어서 서버에서 직접 Geocoding API를 호출할 수 없습니다.

## 해결 방법

### 1. Google Cloud Console에서 API 키 설정 변경

1. **Google Cloud Console** 접속
   - https://console.cloud.google.com/

2. **API 및 서비스 > 사용자 인증 정보** 이동

3. **현재 API 키 편집** 또는 **새 API 키 생성**

4. **애플리케이션 제한사항** 설정:
   ```
   옵션 1: 제한 없음 (개발/테스트용)
   옵션 2: IP 주소 (서버 IP 추가)
   - Railway 서버 IP 주소 추가
   - 로컬 개발 IP 추가 (필요시)
   ```

5. **API 제한사항** 설정:
   ```
   필수 API들:
   - Geocoding API
   - Places API (New)
   - Maps JavaScript API (프론트엔드용)
   - Directions API
   ```

### 2. 환경 변수 업데이트

Railway에서 환경 변수 업데이트:
```
MAPS_PLATFORM_API_KEY_BACKEND=새로운_서버용_API_키
GOOGLE_MAPS_API_KEY=기존_프론트엔드용_API_키 (그대로 유지)
```

### 3. 테스트 방법

API 키 업데이트 후:
```bash
# 로컬 테스트
python test_endpoints.py

# 또는 Railway 배포 후 엔드포인트 테스트
POST /api/v1/place-recommendations/test-ambiguous-location
POST /api/v1/place-recommendations/test-geocoding-failure
```

## 현재 상태

✅ **폴백 시스템**: 정상 작동
✅ **에러 처리**: 정상 작동  
❌ **Geocoding API**: API 키 제한으로 실패
❌ **동명 지역 처리**: Geocoding 의존으로 현재 불가

## 임시 해결책

API 키 문제 해결 전까지는 모든 요청이 폴백 시스템으로 처리됩니다:
- 사용자가 "광주"를 입력해도 동명 지역 선택지가 나타나지 않음
- 대신 기본 서울 추천 장소가 반환됨
- 시스템은 정상 작동하지만 정확한 지역 구분은 불가