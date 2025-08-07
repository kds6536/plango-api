-- Plango v6.0 새로운 데이터베이스 스키마 설정
-- 새로운 관계형 구조: countries, cities, cached_places, prompts

-- 1. 국가 테이블
CREATE TABLE IF NOT EXISTS public.countries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 2. 도시 테이블
CREATE TABLE IF NOT EXISTS public.cities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    country_id INTEGER NOT NULL REFERENCES public.countries(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    UNIQUE(name, country_id)
);

-- 3. 캐시된 장소 테이블
CREATE TABLE IF NOT EXISTS public.cached_places (
    id SERIAL PRIMARY KEY,
    city_id INTEGER NOT NULL REFERENCES public.cities(id) ON DELETE CASCADE,
    place_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    address TEXT,
    coordinates JSONB,
    rating DECIMAL(3,2),
    total_ratings INTEGER DEFAULT 0,
    phone VARCHAR(50),
    website TEXT,
    photos JSONB,
    opening_hours JSONB,
    price_level INTEGER,
    raw_data JSONB,
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
CREATE INDEX IF NOT EXISTS idx_cities_name_country ON public.cities(name, country_id);
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
    '당신은 전문 여행 큐레이터입니다. 다음 정보를 바탕으로 {city}, {country}에서 방문할 만한 장소들을 추천해주세요.

여행 정보:
- 도시: {city}
- 국가: {country}
- 총 여행 기간: {total_duration}일
- 여행자 수: {travelers_count}명
- 예산: {budget_range}
- 여행 스타일: {travel_style}
- 특별 요청: {special_requests}

{previously_recommended_places}

다음 카테고리별로 10개씩 새로운 장소를 추천해주세요:
1. **볼거리** (관광지, 명소, 박물관, 역사적 장소)
2. **먹거리** (현지 음식점, 맛집, 카페)
3. **즐길거리** (체험, 엔터테인먼트, 액티비티)
4. **숙소** (호텔, 게스트하우스, 리조트)

각 장소는 실제 존재하는 곳이어야 하며, 구글에서 검색 가능한 정확한 이름이어야 합니다.
여행자의 예산과 스타일을 고려하여 적절한 장소를 선별해주세요.

JSON 형식으로 다음과 같이 응답해주세요:
{
  "main_theme": "이번 여행의 주요 테마나 컨셉",
  "볼거리": ["장소명1", "장소명2", "장소명3", "장소명4", "장소명5", "장소명6", "장소명7", "장소명8", "장소명9", "장소명10"],
  "먹거리": ["음식점1", "음식점2", "음식점3", "음식점4", "음식점5", "음식점6", "음식점7", "음식점8", "음식점9", "음식점10"],
  "즐길거리": ["액티비티1", "액티비티2", "액티비티3", "액티비티4", "액티비티5", "액티비티6", "액티비티7", "액티비티8", "액티비티9", "액티비티10"],
  "숙소": ["숙소1", "숙소2", "숙소3", "숙소4", "숙소5", "숙소6", "숙소7", "숙소8", "숙소9", "숙소10"]
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