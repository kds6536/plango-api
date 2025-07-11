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

# FastAPI 앱 생성
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.PROJECT_VERSION
)

# CORS 미들웨어 설정
if getattr(settings, "BACKEND_CORS_ORIGINS", None):
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
    """
    애플리케이션 시작 시 실행되는 비동기 이벤트입니다.
    느린 초기화 작업(예: DB 연결)을 여기서 수행합니다.
    """
    logger = logging.getLogger(__name__)
    try:
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_API_KEY")
        
        if not url or not key:
            raise ValueError("Supabase URL 또는 API 키가 설정되지 않았습니다.")
            
        # admin 라우터의 supabase 변수에 클라이언트 인스턴스 주입
        admin.supabase = create_client(url, key)
        logger.info("✅ Supabase 클라이언트가 성공적으로 초기화 및 주입되었습니다.")
    except Exception as e:
        logger.error(f"💥 Supabase 클라이언트 초기화 실패: {e}")
        admin.supabase = None


# 라우터 포함
app.include_router(health.router)
app.include_router(new_itinerary.router)
app.include_router(admin.router)
app.include_router(places.router)

# create_db_and_tables()


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