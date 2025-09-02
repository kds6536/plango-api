# ===============================================================
# 멀티스테이지 빌드로 메모리 사용량 최적화
# ===============================================================

# ---- 1단계: 빌드 스테이지 ----
FROM python:3.11-alpine as builder

# 빌드에 필요한 최소한의 패키지만 설치
RUN apk add --no-cache gcc musl-dev libffi-dev

WORKDIR /app

# pip 업그레이드 및 설정
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# requirements 복사 및 설치 (재시도 옵션 추가)
COPY requirements.txt .
RUN pip install --no-cache-dir --retries 5 --timeout 300 -r requirements.txt

# ---- 2단계: 실행 스테이지 ----
FROM python:3.11-alpine

# 실행에 필요한 최소한의 패키지만 설치 (curl 제거)
RUN addgroup -g 1001 -S appuser && \
    adduser -S appuser -G appuser

# 빌드 스테이지에서 설치된 패키지 복사
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /code

# 애플리케이션 코드 및 헬스체크 스크립트 복사
COPY --chown=appuser:appuser ./app /code/app
COPY --chown=appuser:appuser ./healthcheck.py /code/healthcheck.py

# 로그 디렉토리 생성
RUN mkdir -p /code/logs && chown appuser:appuser /code/logs

USER appuser

# 포트 노출
EXPOSE 8000

# Python 기반 헬스체크 (curl 의존성 제거)
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python /code/healthcheck.py

# Railway 포트 동적 할당 대응
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 