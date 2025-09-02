# ===============================================================
#  VERSION: FINAL FIX (Circular Import - 2024-07-10)
# ===============================================================
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from supabase import create_client

from app.routers import health, admin, new_itinerary, places, setup, place_recommendations, setup_v6
from app.config import settings
# from app.database import create_db_and_tables
from app.utils.logger import get_logger

# FastAPI 애플리케이션 생성
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.PROJECT_VERSION
)

# 로거 초기화 (CORS 설정보다 먼저 해야 함)
logger = get_logger("api")

# CORS 미들웨어 추가
# 환경 변수에서 추가 origins를 가져와서 병합
additional_origins = os.getenv("ADDITIONAL_CORS_ORIGINS", "").split(",")
additional_origins = [origin.strip() for origin in additional_origins if origin.strip()]

all_origins = list(settings.BACKEND_CORS_ORIGINS)
all_origins.extend(additional_origins)

# 중복 제거
all_origins = list(set(all_origins))

logger.info(f"CORS Origins 설정: {all_origins}")

if all_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=all_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# --- 메모리 효율적인 시작 이벤트 핸들러 ---
@app.on_event("startup")
async def startup_event():
    """메모리 사용량을 최소화한 초기화"""
    try:
        url = settings.SUPABASE_URL
        key = settings.SUPABASE_KEY
        if url and key:
            # 지연 로딩으로 메모리 사용량 최적화
            supabase_client = create_client(url, key)
            logger.info("Supabase 클라이언트 초기화 성공")
            
            # 라우터에 클라이언트 주입 (전역 변수 사용 최소화)
            admin.supabase = supabase_client
            new_itinerary.supabase = supabase_client
        else:
            logger.warning("Supabase 설정 누락 - 관련 기능 제한됨")
            admin.supabase = None
            new_itinerary.supabase = None
            
    except Exception as e:
        logger.error(f"Supabase 초기화 실패: {e}")
        admin.supabase = None
        new_itinerary.supabase = None

@app.on_event("shutdown")
async def shutdown_event():
    """메모리 정리"""
    logger.info("애플리케이션 종료 - 메모리 정리 중")

# 라우터 포함
app.include_router(health.router)
app.include_router(admin.router)
app.include_router(new_itinerary.router)
app.include_router(places.router)
app.include_router(setup.router)
app.include_router(place_recommendations.router)  # 새로운 장소 추천 라우터 (v6.0)
app.include_router(setup_v6.router)  # v6.0 설정 및 테스트 라우터

# 진단 라우터 추가
from app.routers import diagnosis
app.include_router(diagnosis.router)

# 관리자 대시보드 라우터 추가
from app.routers import admin_dashboard
app.include_router(admin_dashboard.router)

# # 데이터베이스 및 테이블 생성
# @app.on_event("startup")
# def on_startup():
#     create_db_and_tables()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Pydantic 모델 유효성 검사 실패 시 커스텀 에러 메시지를 반환합니다."""
    logging.error(f"422 Unprocessable Entity: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors()}),
    )


@app.get("/", tags=["기본"])
async def read_root():
    """루트 엔드포인트 - 헬스체크 겸용"""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}!",
        "status": "healthy",
        "version": settings.PROJECT_VERSION
    } 


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 