# Plango API

AI 기반 여행 일정 생성 서비스의 백엔드 API 서버입니다.

## 🌟 주요 기능

- **AI 여행 일정 생성**: OpenAI GPT를 활용하여 사용자 맞춤형 여행 일정 생성
- **Plan A/B 제공**: 두 가지 다른 스타일의 여행 일정 옵션 제공
- **여행지 관리**: 여행지 정보 조회 및 관리
- **RESTful API**: 표준 REST API 인터페이스 제공

## 🛠️ 기술 스택

- **Framework**: FastAPI
- **Language**: Python 3.11+
- **Database**: PostgreSQL
- **Cache**: Redis
- **AI**: OpenAI GPT
- **Deployment**: Railway
- **Testing**: Pytest

## 🚀 빠른 시작

### 1. 저장소 클론

```bash
git clone <repository-url>
cd plango-api
```

### 2. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 환경변수 설정

```bash
cp .env.example .env
# .env 파일을 편집하여 실제 값으로 변경
```

### 5. 서버 실행

```bash
# 개발 모드
python main.py

# 또는 uvicorn 직접 실행
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 6. API 문서 확인

브라우저에서 다음 주소로 접속:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📁 프로젝트 구조

```
plango-api/
├── app/
│   ├── __init__.py
│   ├── config.py              # 설정 관리
│   │   ├── __init__.py
│   │   ├── itinerary.py
│   │   └── destination.py
│   ├── routers/               # API 라우터
│   │   ├── __init__.py
│   │   ├── health.py
│   │   ├── itinerary.py
│   │   └── destinations.py
│   ├── services/              # 비즈니스 로직
│   │   ├── __init__.py
│   │   ├── ai_service.py
│   │   └── itinerary_service.py
│   ├── utils/                 # 유틸리티
│   │   ├── __init__.py
│   │   └── logger.py
│   └── schemas/               # Pydantic 스키마
│       ├── __init__.py
│       ├── itinerary.py
│       └── destination.py
├── tests/                     # 테스트 코드
├── logs/                      # 로그 파일
├── main.py                    # 애플리케이션 엔트리포인트
├── requirements.txt           # Python 의존성
├── .env.example              # 환경변수 예시
├── .gitignore                # Git 무시 파일
├── railway.toml              # Railway 배포 설정
└── README.md                 # 프로젝트 문서
```

## 🔧 개발 가이드

### 코드 포맷팅

```bash
# Black 포맷터 실행
black .

# Import 정렬
isort .

# 린터 실행
flake8 .
```

### 테스트 실행

```bash
# 모든 테스트 실행
pytest

# 커버리지와 함께 실행
pytest --cov=app
```

## 🌐 API 엔드포인트

### Health Check
- `GET /api/v1/health` - 서버 상태 확인

### 여행 일정
- `POST /api/v1/itinerary/generate` - 여행 일정 생성
- `GET /api/v1/itinerary/{id}` - 여행 일정 조회

### 여행지
- `GET /api/v1/destinations` - 여행지 목록 조회
- `GET /api/v1/destinations/{id}` - 특정 여행지 조회

## 🚀 배포

### Railway 배포

1. Railway 계정 연결
2. 환경변수 설정
3. 자동 배포 확인

```bash
railway login
railway link
railway up
```

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🤝 기여하기

1. 이 저장소를 포크합니다
2. 새로운 기능 브랜치를 생성합니다 (`git checkout -b feature/AmazingFeature`)
3. 변경사항을 커밋합니다 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/AmazingFeature`)
5. Pull Request를 생성합니다

## 📞 문의

프로젝트 관련 문의사항이 있으시면 이슈를 생성해주세요. 