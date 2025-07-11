from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from contextlib import asynccontextmanager
import uvicorn
import os
import json
import logging
from dotenv import load_dotenv

from app.routers import destinations, health, places, new_itinerary, admin
from app.config import settings

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 애플리케이션 시작 시 실행되는 코드
    print("��� Plango API 서버가 시작됩니다...")
    print("��� 새로운 4단계 프로세스 엔드포인트 활성화:")
    print("   - /api/v1/itinerary/generate (1안/2안 생성)")
    print("   - /api/v1/itinerary/optimize (경로 최적화)")
    print("��� 관리자 AI 설정 엔드포인트 활성화:")
    print("   - GET/PUT /api/v1/admin/ai-settings (AI 제공자 관리)")
    yield
    # 애플리케이션 종료 시 실행되는 코드
    print("��� Plango API 서버가 종료됩니다...")

# FastAPI 애플리케이션 인스턴스 생성
app = FastAPI(
    title="Plango API - Advanced Edition with Dynamic AI",
    description="AI 기반 4단계 프로세스 여행 일정 생성 서비스 (동적 AI 제공자 지원)",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용
    allow_credentials=False,  # credentials는 False로 설정
    allow_methods=["*"],
    allow_headers=["*"],
)

# 422 에러 상세 로그 핸들러 추가
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """422 에러 발생 시 상세 에러 내용을 로그에 출력"""
    error_details = json.dumps(exc.errors(), indent=2, ensure_ascii=False)
    logging.error("=== Pydantic Validation Error ===")
    logging.error(f"Request URL: {request.url}")
    logging.error(f"Request Method: {request.method}")
    logging.error(f"Request Headers: {dict(request.headers)}")
    logging.error(f"Error Details:\n{error_details}")
    logging.error("===============================")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors()}),
    )

# 라우터 등록 - 새로운 4단계 프로세스 우선 적용
app.include_router(admin.router)
app.include_router(destinations.router)
app.include_router(health.router)
# app.include_router(itinerary.router)  # 기존 라우터 비활성화 - 새로운 4단계 프로세스로 대체
app.include_router(new_itinerary.router)  # 새로운 4단계 프로세스 라우터 활성화
app.include_router(places.router)

@app.get("/")
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "Plango API - Advanced Edition with Dynamic AI에 오신 것을 환영합니다! ������",
        "version": "2.1.0",
        "docs": "/docs",
        "features": {
            "4_step_process": {
                "endpoint": "/api/v1/itinerary/generate",
                "description": "AI 브레인스토밍 → 구글 플레이스 강화 → AI 큐레이션 → JSON 조립"
            },
            "route_optimization": {
                "endpoint": "/api/v1/itinerary/optimize", 
                "description": "구글 다이렉션 API로 최적 동선 계산"
            },
            "dynamic_ai": {
                "endpoint": "/api/v1/admin/ai-settings",
                "description": "관리자가 OpenAI ↔ Gemini 동적 전환 가능"
            }
        }
    }

if __name__ == "__main__":
    # Railway 환경에서는 PORT 환경변수 사용, 로컬에서는 8005 사용
    port = int(os.getenv("PORT", 8005))
    host = "0.0.0.0" if os.getenv("RAILWAY_ENVIRONMENT") else "127.0.0.1"
    
    print("��� Plango API 서버를 시작합니다...")
    print(f"��� 서버 주소: http://{host}:{port}")
    print(f"��� API 문서: http://{host}:{port}/docs")
    print("��� 주요 엔드포인트:")
    print("   - POST /api/v1/itinerary/generate (4단계 일정 생성)")
    print("   - POST /api/v1/itinerary/optimize (경로 최적화)")
    print("   - GET/PUT /api/v1/admin/ai-settings (AI 제공자 관리)")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True if os.getenv("ENVIRONMENT") == "development" else False
    )
