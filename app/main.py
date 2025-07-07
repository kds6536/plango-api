from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import json
import traceback

from app.routers import (
    health,
    itinerary,
    new_itinerary,
    places,
    destinations,
    admin
)
from app.utils.logger import get_logger

# --- 기존 FastAPI 앱 인스턴스 생성 및 로거 설정 ---
app = FastAPI()
logger = get_logger(__name__)

# --- 상세 에러 로깅 핸들러 추가 ---

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """FastAPI의 유효성 검사 오류를 더 자세히 로깅합니다."""
    error_details = json.dumps(exc.errors(), indent=2, ensure_ascii=False)
    logging.error(f"422 Unprocessable Entity: \n{error_details}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """처리되지 않은 모든 예외를 잡아 상세한 트레이스백을 로깅합니다."""
    error_traceback = traceback.format_exc()
    logging.error(f"500 Internal Server Error: {exc}\nTraceback:\n{error_traceback}")
    return JSONResponse(
        status_code=500,
        content={"detail": "서버 내부 오류가 발생했습니다. 관리자에게 문의하세요."},
    )

# --- 기존 라우터 포함 로직 ---
@app.get("/")
def read_root():
    return {"message": "Welcome to PlanGo API"}

app.include_router(health.router)
app.include_router(itinerary.router)
app.include_router(new_itinerary.router)
app.include_router(places.router)
app.include_router(destinations.router)
app.include_router(admin.router) 