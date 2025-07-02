from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Plango API Test", version="1.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Plango API 서버가 정상적으로 실행중입니다! 🚀", "status": "success"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API 서버 상태 양호"}

@app.get("/api/v1/test")
async def test_endpoint():
    return {"message": "테스트 엔드포인트 응답", "data": {"test": True}}

if __name__ == "__main__":
    print("🚀 Plango API 서버를 시작합니다...")
    print("📍 서버 주소: http://127.0.0.1:8001")
    print("📚 API 문서: http://127.0.0.1:8001/docs")
    uvicorn.run(app, host="127.0.0.1", port=8001) 