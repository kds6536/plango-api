# Plango API v6.0 변경사항

## 📋 개요
Plango API v6.0에서는 새로운 관계형 데이터베이스 구조를 도입하여 확장 가능하고 효율적인 여행 일정 생성 시스템을 완성했습니다.

## 🗄️ 새로운 데이터베이스 스키마

### 핵심 테이블
1. **`countries`** - 국가 정보 (id, name)
2. **`cities`** - 도시 정보 (id, name, country_id)
3. **`cached_places`** - 장소 정보 (id, city_id, place_id, name, category, etc.)
4. **`prompts`** - 프롬프트 템플릿 (id, name, value, description)

### 관계형 구조
- `cities.country_id` → `countries.id` (Foreign Key)
- `cached_places.city_id` → `cities.id` (Foreign Key)

## 🔧 주요 변경사항

### 1. Supabase Service 리팩토링 (`app/services/supabase_service.py`)
- **신규 함수**:
  - `get_or_create_country()` - 국가 조회 또는 생성
  - `get_or_create_city()` - 도시 조회 또는 생성  
  - `get_existing_place_names()` - 기존 추천 장소 이름 목록 조회
  - `save_cached_places()` - 새로운 장소 정보 저장

- **수정된 함수**:
  - `get_master_prompt()` - name 컬럼으로 조회, 예외 발생 방식 변경
  
- **제거된 함수**:
  - `update_master_prompt()` - 일반 API에서 프롬프트 쓰기 제거
  - `get_prompt_history()`, `delete_prompt()` - 불필요한 쓰기 함수 제거
  - 로컬 파일 관련 fallback 함수들 대부분 제거

### 2. 새로운 장소 추천 시스템 (`app/services/place_recommendation_service.py`)
- **중복 추천 방지**: 기존 추천 장소 제외
- **프롬프트 동적 생성**: 기존 장소 목록을 포함한 맞춤형 프롬프트
- **AI + Google Places API 연동**: 검증된 장소 정보 제공
- **캐싱 시스템**: cached_places 테이블에 결과 저장

### 3. 새로운 API 엔드포인트 (`app/routers/place_recommendations.py`)
- `POST /api/v1/place-recommendations/generate` - 장소 추천 생성
- `GET /api/v1/place-recommendations/health` - 서비스 상태 확인
- `GET /api/v1/place-recommendations/stats/{city_id}` - 도시별 추천 통계
- `POST /api/v1/place-recommendations/test-prompt-generation` - 프롬프트 테스트

### 4. 새로운 스키마 정의 (`app/schemas/place.py`)
- `Country`, `City`, `CachedPlace`, `Prompt` 모델
- `PlaceRecommendationRequest`, `PlaceRecommendationResponse` 요청/응답 모델

### 5. 설정 및 테스트 도구 (`app/routers/setup_v6.py`)
- `POST /api/v1/setup-v6/test-country-city` - 국가/도시 생성 테스트
- `POST /api/v1/setup-v6/test-place-recommendation` - 장소 추천 테스트
- `GET /api/v1/setup-v6/check-prompts` - 프롬프트 확인
- `GET /api/v1/setup-v6/health-v6` - v6.0 시스템 상태 확인

## 🔄 기존 코드 호환성

### Enhanced AI Service 수정
- `get_master_prompt()` - 기존 프롬프트 타입을 새로운 스키마 이름으로 매핑
- `update_master_prompt()` - NotImplementedError 발생 (관리자 전용으로 제한)

### Advanced Itinerary Service 수정  
- 프롬프트 조회 방식을 새로운 스키마에 맞게 변경
- `load_prompts_from_db()` 함수 호출 제거

## 📂 새로운 파일 구조

```
plango-api/
├── app/
│   ├── schemas/
│   │   └── place.py                        # 새로운 스키마 정의
│   ├── services/
│   │   ├── supabase_service.py              # 대폭 리팩토링
│   │   └── place_recommendation_service.py  # 신규 서비스
│   └── routers/
│       ├── place_recommendations.py         # 신규 라우터
│       └── setup_v6.py                      # 신규 설정 라우터
├── setup_new_schema.sql                     # 새로운 DB 스키마 SQL
└── CHANGELOG_v6.md                          # 이 파일
```

## 🚀 사용 방법

### 1. 데이터베이스 스키마 설정
```sql
-- setup_new_schema.sql 실행
```

### 2. 새로운 장소 추천 API 사용
```bash
curl -X POST "http://localhost:8000/api/v1/place-recommendations/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "country": "한국",
    "city": "서울", 
    "total_duration": 3,
    "travelers_count": 2,
    "budget_range": "중간",
    "travel_style": "문화탐방",
    "special_requests": "한국 전통 문화 체험"
  }'
```

### 3. 시스템 상태 확인
```bash
curl "http://localhost:8000/api/v1/setup-v6/health-v6"
```

## 📈 성능 개선

1. **중복 추천 방지**: 기존 추천 장소를 제외하여 더 다양한 추천 제공
2. **캐시 시스템**: cached_places 테이블로 반복 검색 최소화
3. **관계형 구조**: Foreign Key로 데이터 무결성 보장
4. **프롬프트 동적 생성**: 도시별 맞춤형 프롬프트로 추천 품질 향상

## 🔒 보안 강화

1. **쓰기 권한 제한**: 일반 API에서 프롬프트 수정 불가
2. **예외 처리 강화**: ValueError로 명확한 오류 메시지 제공
3. **RLS 정책**: Row Level Security로 데이터 접근 제어

## 🎯 다음 단계

v6.0 완성 후 다음 기능들을 순차적으로 개발 예정:
1. 사용자별 추천 히스토리 관리
2. 추천 알고리즘 개선 (머신러닝 기반)
3. 실시간 장소 정보 업데이트
4. 다국어 지원 확장