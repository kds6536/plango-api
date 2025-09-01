# ===============================================================
# 멀티스테이지 빌드로 메모리 사용량 최적화
# ===============================================================

# ---- 1단계: 빌드 스테이지 ----
FROM python:3.11-alpine as builder

# 빌드에 필요한 최소한의 패키지만 설치
RUN apk add --no-cache gcc musl-dev libffi-dev

WORKDIR /app

# requirements 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- 2단계: 실행 스테이지 ----
FROM python:3.11-alpine

# 실행에 필요한 최소한의 패키지만 설치
RUN apk add --no-cache curl && \
    addgroup -g 1001 -S appuser && \
    adduser -S appuser -G appuser

# 빌드 스테이지에서 설치된 패키지 복사
COPY --from=builder /root/.local /home/appuser/.local

# PATH 설정
ENV PATH=/home/appuser/.local/bin:$PATH

WORKDIR /code

# 애플리케이션 코드만 복사
COPY --chown=appuser:appuser ./app /code/app

# 로그 디렉토리 생성
RUN mkdir -p /code/logs && chown appuser:appuser /code/logs

USER appuser

# 포트 노출
EXPOSE 8000

# 경량화된 헬스체크
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/v1/health || exit 1

# 메모리 효율적인 uvicorn 설정
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--loop", "asyncio"] 