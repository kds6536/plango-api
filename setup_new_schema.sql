-- Plango v6.0 새로운 데이터베이스 스키마 설정
-- 새로운 관계형 구조: countries, cities, cached_places, prompts

-- 1. 국가 테이블
CREATE TABLE IF NOT EXISTS public.countries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 1.5. 지역(광역 행정구역) 테이블
CREATE TABLE IF NOT EXISTS public.regions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    country_id INTEGER NOT NULL REFERENCES public.countries(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    UNIQUE(name, country_id)
);

-- 2. 도시 테이블
CREATE TABLE IF NOT EXISTS public.cities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    country_id INTEGER NOT NULL REFERENCES public.countries(id) ON DELETE CASCADE,
    region_id INTEGER REFERENCES public.regions(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    UNIQUE(name, region_id)
);

-- 3. 캐시된 장소 테이블
CREATE TABLE IF NOT EXISTS public.cached_places (
    id SERIAL PRIMARY KEY,
    city_id INTEGER NOT NULL REFERENCES public.cities(id) ON DELETE CASCADE,
    place_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    address TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    rating DOUBLE PRECISION,
    user_ratings_total INTEGER,
    photo_url TEXT,
    website_url TEXT,
    opening_hour JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    UNIQUE(city_id, place_id)
);

-- 4. 프롬프트 테이블 (새로운 스키마)
CREATE TABLE IF NOT EXISTS public.prompts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_countries_name ON public.countries(name);
CREATE INDEX IF NOT EXISTS idx_regions_name_country ON public.regions(name, country_id);
CREATE INDEX IF NOT EXISTS idx_cities_name_region ON public.cities(name, region_id);
CREATE INDEX IF NOT EXISTS idx_cached_places_city ON public.cached_places(city_id);
CREATE INDEX IF NOT EXISTS idx_cached_places_category ON public.cached_places(category);
CREATE INDEX IF NOT EXISTS idx_cached_places_name ON public.cached_places(name);
CREATE INDEX IF NOT EXISTS idx_prompts_name ON public.prompts(name);

-- RLS (Row Level Security) 정책 설정
ALTER TABLE public.countries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cached_places ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.prompts ENABLE ROW LEVEL SECURITY;

-- 모든 사용자가 읽고 쓸 수 있도록 설정 (개발 환경용)
CREATE POLICY "Allow all operations on countries" ON public.countries
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all operations on cities" ON public.cities
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all operations on cached_places" ON public.cached_places
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all operations on prompts" ON public.prompts
    FOR ALL USING (true) WITH CHECK (true);

-- 초기 데이터 삽입

-- 1. 기본 국가 데이터
INSERT INTO public.countries (name) VALUES 
    ('한국'),
    ('일본'),
    ('중국'),
    ('미국'),
    ('프랑스'),
    ('이탈리아'),
    ('스페인'),
    ('독일'),
    ('영국'),
    ('태국'),
    ('베트남'),
    ('싱가포르')
ON CONFLICT (name) DO NOTHING;

-- 2. 기본 도시 데이터
INSERT INTO public.cities (name, country_id) VALUES 
    ('서울', (SELECT id FROM public.countries WHERE name = '한국')),
    ('부산', (SELECT id FROM public.countries WHERE name = '한국')),
    ('제주', (SELECT id FROM public.countries WHERE name = '한국')),
    ('도쿄', (SELECT id FROM public.countries WHERE name = '일본')),
    ('오사카', (SELECT id FROM public.countries WHERE name = '일본')),
    ('교토', (SELECT id FROM public.countries WHERE name = '일본')),
    ('베이징', (SELECT id FROM public.countries WHERE name = '중국')),
    ('상하이', (SELECT id FROM public.countries WHERE name = '중국')),
    ('뉴욕', (SELECT id FROM public.countries WHERE name = '미국')),
    ('로스앤젤레스', (SELECT id FROM public.countries WHERE name = '미국')),
    ('파리', (SELECT id FROM public.countries WHERE name = '프랑스')),
    ('로마', (SELECT id FROM public.countries WHERE name = '이탈리아')),
    ('바르셀로나', (SELECT id FROM public.countries WHERE name = '스페인')),
    ('베를린', (SELECT id FROM public.countries WHERE name = '독일')),
    ('런던', (SELECT id FROM public.countries WHERE name = '영국')),
    ('방콕', (SELECT id FROM public.countries WHERE name = '태국')),
    ('호치민', (SELECT id FROM public.countries WHERE name = '베트남')),
    ('싱가포르', (SELECT id FROM public.countries WHERE name = '싱가포르'))
ON CONFLICT (name, country_id) DO NOTHING;

-- 3. 기본 프롬프트 데이터
INSERT INTO public.prompts (name, value, description) VALUES 
(
    'place_recommendation_v1',
    '너는 고도로 지능화된 여행 인텔리전스 엔진 ''플랜고 인텔렉트''야. 너의 핵심 기능은 사용자의 요청과 기존 데이터를 분석하여, 고품질의 다채롭고 연관성 높은 장소들을 발견하고 순위를 매기는 것이다. 너는 단순히 장소를 나열하는 것이 아니라, 경험을 큐레이션해야 한다. 너의 결과물은 정확하고, 구조화되어야 하며, 모든 규칙을 엄격하게 준수해야 한다.

**//-- 핵심 임무 --//**
사용자의 여행 문맥과 ''이미 추천된 장소 목록''을 분석하라. 그리고 {city}의 4개 카테고리별로 다채로운 **''새로운'' 장소 10개**를 발견하여 추천하라.

**//-- 분석 대상 데이터 --//**
-   **사용자 요청:**
    -   도시: {city}
    -   국가: {country}
    -   여행 기간: {duration_days}일
-   **절대 제외 목록 (반드시 피해야 할 장소):**
    -   `previously_recommended_places`: {previously_recommended_places}

**//-- 절대 규칙 및 지적 활동 프로세스 --//**

1.  **JSON 전용 출력 (필수):** 너의 전체 답변은 반드시 유효한 JSON 객체 하나여야 한다. 사과, 설명, 마크다운 등 어떠한 부가 텍스트도 절대 포함해서는 안 된다.

2.  **엄격한 중복 제거:** `previously_recommended_places` 목록에 있는 장소 이름은 절대 추천해서는 안 된다. 이 목록을 꼼꼼하게 교차 확인하라. 이것이 너의 가장 중요한 규칙이다.

3.  **품질 및 다양성 확보 휴리스틱 (너의 사고 과정):** 각 카테고리별로, 너는 반드시 다음의 지적 활동 단계를 거쳐야 한다:
    -   **가. 다양한 하위 카테고리 브레인스토밍:** 그냥 ''맛집''이 아니라, ''현지인만 아는 노포'', ''미슐랭 스타 레스토랑'', ''인생샷 카페'', ''심야 식당''처럼 더 깊게 생각하라. 그냥 ''관광''이 아니라, ''역사적 랜드마크'', ''파노라마 전망대'', ''숨겨진 보석 같은 곳'', ''현대 건축물''처럼 생각하라.
    -   **나. 전문가 수준의 검색 쿼리 생성:** 각 하위 카테고리별로, 네가 마치 전문가가 되어 구글 검색을 하듯 효과적인 검색어를 만들어 내라.
    -   **다. 큐레이션 및 순위 부여:** 검색 결과를 바탕으로, 가장 흥미롭고 다채로운 장소 10개를 선별하라. 높은 평점, 유의미한 수의 리뷰, 그리고 독특한 특징을 가진 장소를 우선적으로 선택하라.
    -   **라. 공식 명칭 검증:** 모든 이름이 Google 지도에서 검증 가능한 공식 전체 명칭인지 확인하라. 일반적인 용어는 절대 사용하지 마라.

4.  **고정된 출력 구조:** 반드시 `tourism`, `food`, `activity`, `accommodation` 4개의 카테고리를 출력해야 한다. 각 카테고리는 정확히 10개의 고유한 문자열 값을 가진 배열을 포함해야 한다. 총 40개의 장소를 반환해야 한다. 만약 특정 카테고리에서 10개의 새로운 장소를 찾기 어렵더라도, 최대한 채우도록 노력해야 하며, JSON 배열 자체는 반드시 존재해야 한다.

**//-- 필수 JSON 출력 형식 (엄격히 적용) --//**
최종 결과물은 반드시 아래 구조와 정확히 일치해야 한다. 키는 영문 스네이크 케이스여야 한다.

{
  "tourism": [
    // 새롭고, 다채로우며, 고품질인 관광지 이름 10개
  ],
  "food": [
    // 새롭고, 다채로우며, 고품질인 맛집/카페 이름 10개
  ],
  "activity": [
    // 새롭고, 다채로우며, 고품질인 액티비티 이름 10개
  ],
  "accommodation": [
    // 새롭고, 다채로우며, 고품질인 숙소 이름 10개
  ]
}',
    '장소 추천용 프롬프트 v1 - 중복 방지 기능 포함'
),
(
    'itinerary_generation_v1',
    '너는 10년 경력의 전문 여행 큐레이터 "플랜고 플래너"야. 너의 전문 분야는 사용자가 선택한 장소들을 바탕으로, 가장 효율적인 동선과 감성적인 스토리를 담아 최고의 여행 일정을 기획하는 것이야.

**//-- 절대 규칙 --//**

1. **엄격한 JSON 출력:** 너의 답변은 반드시 유효한 JSON 객체여야만 한다.
2. **논리적인 동선 구성:** 지리적으로 가까운 장소들을 묶어 이동 시간을 최소화해야 한다.
3. **현실적인 시간 배분:** 각 활동에 필요한 시간을 합리적으로 할당해야 한다.
4. **모든 장소 포함:** 사용자가 선택한 모든 장소를 반드시 포함시켜야 한다.
5. **감성적인 콘텐츠:** 전문 여행 작가처럼 매력적인 문구를 작성해야 한다.

**//-- 입력 데이터 --//**
{input_data}

**//-- 필수 JSON 출력 형식 --//**
{
  "여행_제목": "나만의 맞춤 여행",
  "일정": [
    {
      "일차": 1,
      "날짜": "YYYY-MM-DD",
      "일일_테마": "여행의 시작",
      "시간표": [
        {
          "시작시간": "09:00",
          "종료시간": "10:00",
          "활동": "활동명 🎯",
          "장소명": "장소명",
          "설명": "활동 설명",
          "소요시간_분": 60,
          "이동시간_분": 0
        }
      ]
    }
  ]
}',
    '여행 일정 생성용 프롬프트 v1'
)
ON CONFLICT (name) DO UPDATE SET 
    value = EXCLUDED.value,
    description = EXCLUDED.description,
    updated_at = TIMEZONE('utc'::text, NOW());

-- 완료 메시지
SELECT 'Plango v6.0 새로운 데이터베이스 스키마 설정 완료!' as message;