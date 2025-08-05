-- Plango v2.0 Supabase 스키마 설정
-- AI 설정 및 마스터 프롬프트 관리를 위한 테이블 생성

-- 1. AI 설정 테이블
CREATE TABLE IF NOT EXISTS public.ai_settings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    provider VARCHAR(20) NOT NULL DEFAULT 'openai',
    openai_model VARCHAR(50) NOT NULL DEFAULT 'gpt-4',
    gemini_model VARCHAR(50) NOT NULL DEFAULT 'gemini-1.5-flash',
    temperature DECIMAL(3,2) NOT NULL DEFAULT 0.7,
    max_tokens INTEGER NOT NULL DEFAULT 2000,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 2. 마스터 프롬프트 테이블
CREATE TABLE IF NOT EXISTS public.master_prompts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    prompt_type VARCHAR(50) NOT NULL,
    prompt_content TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 3. 기존 settings 테이블 (호환성 유지)
CREATE TABLE IF NOT EXISTS public.settings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    key VARCHAR(100) NOT NULL UNIQUE,
    value TEXT NOT NULL,
    is_encrypted BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 4. 기존 prompts 테이블 (호환성 유지)
CREATE TABLE IF NOT EXISTS public.prompts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    key VARCHAR(100) NOT NULL UNIQUE,
    value TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_ai_settings_active ON public.ai_settings(is_active);
CREATE INDEX IF NOT EXISTS idx_master_prompts_type_active ON public.master_prompts(prompt_type, is_active);
CREATE INDEX IF NOT EXISTS idx_settings_key ON public.settings(key);
CREATE INDEX IF NOT EXISTS idx_prompts_key ON public.prompts(key);

-- RLS (Row Level Security) 정책 설정
ALTER TABLE public.ai_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.master_prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.prompts ENABLE ROW LEVEL SECURITY;

-- 모든 사용자가 읽고 쓸 수 있도록 설정 (개발 환경용)
CREATE POLICY "Allow all operations on ai_settings" ON public.ai_settings
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all operations on master_prompts" ON public.master_prompts
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all operations on settings" ON public.settings
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow all operations on prompts" ON public.prompts
    FOR ALL USING (true) WITH CHECK (true);

-- 초기 데이터 삽입

-- 1. AI 설정 초기값
INSERT INTO public.ai_settings (provider, openai_model, gemini_model, temperature, max_tokens, is_active)
VALUES ('openai', 'gpt-4', 'gemini-1.5-flash', 0.7, 2000, true)
ON CONFLICT DO NOTHING;

-- 2. 마스터 프롬프트 초기값
INSERT INTO public.master_prompts (prompt_type, prompt_content, is_active)
VALUES 
(
    'itinerary_generation',
    '너는 10년 경력의 전문 여행 큐레이터 "플랜고 플래너"야. 너의 전문 분야는 사용자가 선택한 장소들을 바탕으로, 가장 효율적인 동선과 감성적인 스토리를 담아 최고의 여행 일정을 기획하는 것이야. 너는 단순한 챗봇이 아니라, 프로페셔널 여행 기획 전문가야.

너의 임무는 사용자가 선택한 장소 목록, 여행 기간, 그리고 사전 그룹핑된 정보를 받아, 완벽하게 최적화된 여행 일정을 생성하는 것이다.

**//-- 절대 규칙 --//**

1. **엄격한 JSON 출력:** 너의 답변은 반드시 유효한 JSON 객체여야만 한다. JSON 블록 앞뒤로 어떠한 설명, 인사말, markdown 문법(`json` 등)도 포함해서는 안 된다. 너의 전체 답변은 순수한 JSON 내용 그 자체여야 한다.
2. **논리적인 동선 구성:** 제공된 `사전_그룹` 정보를 중요한 힌트로 사용하되, 가장 효율적이고 논리적인 일일 경로를 만드는 것이 너의 최우선 목표다. 같은 날에는 지리적으로 가까운 장소들을 묶어 이동 시간을 최소화해야 한다.
3. **현실적인 시간 배분:** 각 활동에 필요한 `소요시간_분`을 합리적으로 할당하고, 활동들 사이의 `이동시간_분`을 반드시 포함하여 현실적인 시간표를 만들어야 한다.
4. **모든 장소 포함:** `사용자_선택_장소` 목록에 있는 모든 장소를 반드시 일정 안에 포함시켜야 한다. 단 하나도 누락해서는 안 된다.
5. **감성적인 콘텐츠 제작:** 각 날짜의 `일일_테마`와 각 활동의 `설명` 부분에는 전문 여행 작가처럼 짧고 매력적인 문구를 작성해야 한다. 각 활동(activity)에는 내용과 어울리는 이모지를 하나씩 추가해야 한다.

**//-- 입력 데이터 (이 부분은 백엔드에서 동적으로 채워집니다) --//**

{input_data}

**//-- 필수 JSON 출력 형식 --//**

{
  "여행_제목": "나만의 맞춤 여행",
  "일정": [
    {
      "일차": 1,
      "날짜": "YYYY-MM-DD",
      "일일_테마": "여행의 시작: 새로운 발견의 시간",
      "숙소": {
        "이름": "숙소명"
      },
      "시간표": [
        {
          "시작시간": "09:00",
          "종료시간": "10:00",
          "활동": "활동명 🎯",
          "장소명": "장소명",
          "설명": "활동에 대한 감성적인 설명",
          "소요시간_분": 60,
          "이동시간_분": 0
        }
      ],
      "일일_요약_팁": "하루 여행에 대한 유용한 팁"
    }
  ]
}',
    true
),
(
    'place_recommendation',
    '당신은 전문 여행 가이드입니다. 사용자의 여행 선호도에 맞는 장소를 추천해주세요.',
    true
),
(
    'optimization',
    '여행 동선을 최적화하여 이동 시간을 최소화하고 효율적인 일정을 만들어주세요.',
    true
)
ON CONFLICT DO NOTHING;

-- 3. 호환성을 위한 기존 테이블 데이터
INSERT INTO public.settings (key, value, is_encrypted)
VALUES 
    ('default_provider', 'openai', false),
    ('openai_model_name', 'gpt-4', false),
    ('gemini_model_name', 'gemini-1.5-flash', false)
ON CONFLICT (key) DO UPDATE SET 
    value = EXCLUDED.value,
    updated_at = TIMEZONE('utc'::text, NOW());

INSERT INTO public.prompts (key, value)
VALUES 
    ('stage1_destinations_prompt', '당신은 Plango AI입니다. 여행 목적지 분석 전문가로서 작업해주세요.'),
    ('stage3_detailed_itinerary_prompt', '당신은 Plango AI입니다. 여행 일정 최적화 전문가로서 작업해주세요.')
ON CONFLICT (key) DO UPDATE SET 
    value = EXCLUDED.value,
    updated_at = TIMEZONE('utc'::text, NOW());

-- 완료 메시지
SELECT 'Plango v2.0 데이터베이스 스키마 설정 완료!' as message;