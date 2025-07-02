// Node.js로 만든 간단한 API 서버 (FastAPI 대신 테스트용)
const http = require('http');
const url = require('url');

const server = http.createServer((req, res) => {
    const parsedUrl = url.parse(req.url, true);
    const path = parsedUrl.pathname;
    
    // CORS 헤더 설정
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Content-Type', 'application/json');
    
    if (path === '/') {
        res.writeHead(200);
        res.end(JSON.stringify({
            message: "안녕하세요! Plango API (Node.js 테스트 버전)가 작동중입니다! 🚀",
            version: "1.0.0-test",
            docs: "/docs"
        }));
    } 
    else if (path === '/api/v1/health') {
        res.writeHead(200);
        res.end(JSON.stringify({
            status: "healthy",
            timestamp: new Date().toISOString(),
            version: "1.0.0-test",
            environment: "development",
            message: "Node.js 테스트 서버가 정상 작동중입니다"
        }));
    }
    else if (path === '/api/v1/itinerary/generate' && req.method === 'POST') {
        res.writeHead(200);
        res.end(JSON.stringify({
            message: "여행 일정 생성 테스트",
            plan_a: {
                title: "도쿄 문화 탐방",
                description: "전통과 현대가 만나는 도쿄 여행"
            },
            plan_b: {
                title: "도쿄 모험 여행", 
                description: "액티비티와 체험 중심의 도쿄 여행"
            }
        }));
    }
    else {
        res.writeHead(404);
        res.end(JSON.stringify({
            error: "페이지를 찾을 수 없습니다",
            path: path
        }));
    }
});

const PORT = 8000;
server.listen(PORT, () => {
    console.log(`🚀 Plango API 테스트 서버가 http://localhost:${PORT} 에서 실행중입니다!`);
    console.log(`📋 테스트 가능한 엔드포인트:`);
    console.log(`   - GET  http://localhost:${PORT}/`);
    console.log(`   - GET  http://localhost:${PORT}/api/v1/health`);
    console.log(`   - POST http://localhost:${PORT}/api/v1/itinerary/generate`);
    console.log(`\n✨ 브라우저에서 위 주소들을 테스트해보세요!`);
}); 