from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import json
import traceback
import time
from app.utils.logger import get_logger

# --- 로거 및 앱 인스턴스 ---
logger = get_logger(__name__)
app = FastAPI()

# --- 로깅 미들웨어 추가 ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # 요청 본문을 읽기 위해 별도의 함수로 처리
    request_body = await request.body()
    
    # 요청 정보 로깅
    log_dict = {
        "method": request.method,
        "url": str(request.url),
        "headers": {k.decode(): v.decode() for k, v in request.headers.raw},
    }
    if request_body:
        try:
            log_dict["body"] = json.loads(request_body)
        except json.JSONDecodeError:
            log_dict["body"] = request_body.decode('utf-8', errors='ignore')

    logger.info(f"--- Request --- \n{json.dumps(log_dict, indent=2, ensure_ascii=False)}")
    
    # 응답 생성
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    # 응답 정보 로깅
    response_log_dict = {
        "status_code": response.status_code,
        "process_time_ms": round(process_time * 1000),
    }

    # 응답 본문은 스트리밍될 수 있으므로 안전하게 처리
    try:
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk
        
        if response_body:
             response_log_dict["body"] = json.loads(response_body)
        
        logger.info(f"--- Response --- \n{json.dumps(response_log_dict, indent=2, ensure_ascii=False)}")

        # 한 번 읽은 body_iterator를 다시 사용할 수 없으므로, 새로 response를 만들어 반환
        return Response(content=response_body, status_code=response.status_code, headers=dict(response.headers), media_type=response.media_type)

    except Exception as e:
        logger.error(f"Response logging failed: {e}")
        return response


# --- 기존 예외 핸들러 ---
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