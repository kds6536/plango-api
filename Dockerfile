# Python 3.11 베이스 이미지 사용
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /code

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 파일 복사
COPY requirements.txt .

# Python 패키지 설치
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사 (app 디렉토리만 복사)
COPY ./app /code/app

# 로그 디렉토리 생성
RUN mkdir -p /code/logs

# 비루트 사용자 생성 및 권한 설정
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /code
USER appuser

# 포트 노출
EXPOSE 8000

# 헬스체크 설정
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=5 \
    CMD curl -f -sS http://localhost:8000/api/v1/health || exit 1

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 