# 🚨 긴급: Google API 키 문제 해결 방안

## 현재 상황
- **모든 Google 백엔드 API 실패**: 리퍼러 제한으로 인한 `REQUEST_DENIED`
- **폴백 시스템 작동 중**: 기본 기능은 유지되지만 정확성 떨어짐
- **사용자 경험 저하**: 동명 지역 구분, 실시간 장소 검색 불가

## 해결 방안 (우선순위별)

### 🥇 방안 1: 새로운 서버용 API 키 생성 (권장)
```
1. Google Cloud Console 접속
2. 새 API 키 생성
3. 애플리케이션 제한사항: "없음" 또는 "IP 주소"
4. API 제한사항: 필요한 API들만 선택
   - Geocoding API
   - Places API (New)
   - Directions API
   - Maps JavaScript API (프론트엔드용)
```

**Railway 환경 변수 추가:**
```
GOOGLE_MAPS_UNRESTRICTED_KEY=새로운_서버용_키
```

### 🥈 방안 2: 기존 키 제한 해제 (임시)
```
1. Google Cloud Console에서 기존 키 편집
2. 애플리케이션 제한사항을 "없음"으로 변경
3. 테스트 후 다시 적절한 제한 설정
```

### 🥉 방안 3: 프록시 서버 구축 (복잡)
```
프론트엔드에서 API 호출 → 백엔드로 전달하는 방식
(구현 복잡도가 높아 권장하지 않음)
```

## 테스트 방법

API 키 업데이트 후:
```bash
# 1. 로컬 테스트
python test_all_google_apis.py

# 2. 서비스 영향도 재확인
python test_service_impact.py

# 3. Railway 배포 후 엔드포인트 테스트
POST /api/v1/place-recommendations/test-ambiguous-location
POST /api/v1/place-recommendations/test-geocoding-failure
```

## 예상 복구 시간
- **방안 1**: 10-15분 (키 생성 + 배포)
- **방안 2**: 5분 (설정 변경 + 배포)
- **방안 3**: 2-3시간 (개발 + 테스트)

## 현재 폴백으로 작동하는 기능
✅ 장소 추천 (기본 데이터)
✅ 일정 생성 (AI 기반)
❌ 동명 지역 구분
❌ 실시간 장소 검색
❌ 정확한 이동 시간 계산

## 권장 조치
**즉시 방안 1 또는 2를 실행하여 전체 기능을 복구하는 것을 강력히 권장합니다.**