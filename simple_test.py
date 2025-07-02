# 가장 간단한 FastAPI 테스트
try:
    from fastapi import FastAPI
    print("✅ FastAPI 설치됨")
    
    app = FastAPI(title="Plango API Test")
    
    @app.get("/")
    def root():
        return {"message": "안녕하세요! Plango API가 작동중입니다! 🚀"}
    
    @app.get("/health")
    def health():
        return {"status": "ok", "message": "서버가 정상 작동중입니다"}
    
    print("✅ FastAPI 앱 생성 완료")
    print("서버 실행 명령어: py -m uvicorn simple_test:app --reload")
    
except ImportError as e:
    print(f"❌ 라이브러리 없음: {e}")
    print("필요한 라이브러리를 설치해주세요:")
    print("py -m pip install fastapi uvicorn") 