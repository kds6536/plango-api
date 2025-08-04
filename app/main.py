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

from app.routers import health, admin, new_itinerary, places
from app.config import settings
# from app.database import create_db_and_tables
from app.utils.logger import setup_logging

# FastAPI 애플리케이션 생성
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.PROJECT_VERSION
)

# CORS 미들웨어 추가
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# --- 비동기 시작 이벤트 핸들러 ---
@app.on_event("startup")
async def startup_event():
    global supabase_client
    try:
        url = settings.SUPABASE_URL
        key = settings.SUPABASE_KEY
        if url and key:
            supabase_client = create_client(url, key)
            logger.info("Supabase 클라이언트 초기화 성공")
            # 라우터에 Supabase 클라이언트 주입
            admin.supabase = supabase_client
            new_itinerary.supabase = supabase_client
        else:
            logger.warning("Supabase URL 또는 KEY가 설정되지 않았습니다. 관련 기능이 제한될 수 있습니다.")
            admin.supabase = None
            new_itinerary.supabase = None
            
    except Exception as e:
        logger.error(f"💥 Supabase 클라이언트 초기화 실패: {e}")
        admin.supabase = None
        new_itinerary.supabase = None


# 로깅 미_구성
setup_logging()
logger = logging.getLogger("api")

# 라우터 포함
app.include_router(health.router)
app.include_router(admin.router)
app.include_router(new_itinerary.router)
app.include_router(places.router)

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
    """루트 엔드포인트"""
    return {"message": f"Welcome to {settings.PROJECT_NAME}!"} 


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 