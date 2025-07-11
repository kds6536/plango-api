# ===============================================================
#  VERSION: FINAL FIX (Circular Import - 2024-07-10)
# ===============================================================
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.routers import health, admin, new_itinerary, places
from app.utils.logger import setup_logging
from app.config import settings
from app.database import create_db_and_tables

# 로깅 설정
setup_logging()

# FastAPI 앱 생성
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.PROJECT_DESCRIPTION
)

# CORS 미들웨어 설정
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 라우터 포함
app.include_router(health.router)
app.include_router(new_itinerary.router)
app.include_router(admin.router)
app.include_router(places.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Pydantic 모델 유효성 검사 실패 시 커스텀 에러 메시지를 반환합니다."""
    logging.error(f"422 Unprocessable Entity: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": exc.errors()}),
    )


@app.get("/", summary="루트 경로", description="API 서버의 루트 경로입니다.")
def read_root():
    """API 서버의 루트 경로"""
    return {"message": f"Welcome to {settings.PROJECT_NAME}!"} 