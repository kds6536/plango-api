from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
from dotenv import load_dotenv

from app.routers import itinerary, destinations, health, places, new_itinerary
from app.config import settings

# 환경변수 로드
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 애플리케이션 시작 시 실행되는 코드
    print("🚀 Plango API 서버가 시작됩니다...")
    print("📍 새로운 4단계 프로세스 엔드포인트 활성화:")
    print("   - /api/v1/itinerary/generate (1안/2안 생성)")
    print("   - /api/v1/itinerary/optimize (경로 최적화)")
    yield
    # 애플리케이션 종료 시 실행되는 코드
    print("👋 Plango API 서버가 종료됩니다...")

# FastAPI 애플리케이션 인스턴스 생성
app = FastAPI(
    title="Plango API - Advanced Edition",
    description="AI 기반 4단계 프로세스 여행 일정 생성 서비스",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록 (새로운 엔드포인트를 먼저 등록)
app.include_router(new_itinerary.router, tags=["새로운 여행 일정 API"])
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(itinerary.router, prefix="/api/v1", tags=["기존 Itinerary"])
app.include_router(destinations.router, prefix="/api/v1", tags=["Destinations"])
app.include_router(places.router, prefix="/api/v1", tags=["Places"])

@app.get("/")
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "Plango API - Advanced Edition에 오신 것을 환영합니다! 🌍",
        "version": "2.0.0",
        "docs": "/docs",
        "new_features": {
            "4_step_process": {
                "endpoint": "/api/v1/itinerary/generate",
                "description": "AI 브레인스토밍 → 구글 플레이스 강화 → AI 큐레이션 → JSON 조립"
            },
            "route_optimization": {
                "endpoint": "/api/v1/itinerary/optimize", 
                "description": "구글 다이렉션 API로 최적 동선 계산"
            }
        }
    }

if __name__ == "__main__":
    print("🚀 Plango API 서버를 시작합니다...")
    print("📍 서버 주소: http://127.0.0.1:8005")
    print("📚 API 문서: http://127.0.0.1:8005/docs")
    print("🆕 새로운 엔드포인트:")
    print("   - POST /api/v1/itinerary/generate (4단계 일정 생성)")
    print("   - POST /api/v1/itinerary/optimize (경로 최적화)")
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8005,
        reload=True if os.getenv("ENVIRONMENT") == "development" else False
    ) 