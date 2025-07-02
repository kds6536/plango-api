# Makefile for Plango API

.PHONY: help install dev test lint format clean docker-build docker-run

# 기본 타겟
help:
	@echo "사용 가능한 명령어:"
	@echo "  install     - 의존성 설치"
	@echo "  dev         - 개발 서버 실행"
	@echo "  test        - 테스트 실행"
	@echo "  lint        - 코드 검사"
	@echo "  format      - 코드 포맷팅"
	@echo "  clean       - 임시 파일 정리"
	@echo "  docker-build - Docker 이미지 빌드"
	@echo "  docker-run  - Docker 컨테이너 실행"

# 의존성 설치
install:
	pip install --upgrade pip
	pip install -r requirements.txt

# 개발 의존성 설치
install-dev:
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install pytest pytest-asyncio black flake8 isort mypy

# 개발 서버 실행
dev:
	python main.py

# 서버 실행 (uvicorn 직접)
serve:
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 테스트 실행
test:
	pytest tests/ -v

# 테스트 (커버리지)
test-cov:
	pytest tests/ -v --cov=app --cov-report=html

# 코드 검사
lint:
	flake8 app/ tests/
	mypy app/

# 코드 포맷팅
format:
	black app/ tests/
	isort app/ tests/

# 코드 포맷팅 확인
format-check:
	black --check app/ tests/
	isort --check-only app/ tests/

# 임시 파일 정리
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/

# Docker 이미지 빌드
docker-build:
	docker build -t plango-api:latest .

# Docker 컨테이너 실행
docker-run:
	docker run -p 8000:8000 --env-file .env plango-api:latest

# Docker Compose 실행
docker-up:
	docker-compose up -d

# Docker Compose 중지
docker-down:
	docker-compose down

# Docker Compose 로그 확인
docker-logs:
	docker-compose logs -f

# 데이터베이스 마이그레이션 (예시)
migrate:
	alembic upgrade head

# 새 마이그레이션 생성 (예시)
migration:
	alembic revision --autogenerate -m "$(MESSAGE)"

# 환경변수 파일 생성
env:
	cp .env.example .env
	@echo ".env 파일이 생성되었습니다. 필요한 값들을 설정해주세요."

# 전체 체크 (CI/CD에서 사용)
check: format-check lint test

# 프로덕션 빌드
build: clean format lint test docker-build 