import os
import requests
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# ✅ .env 파일 로드
load_dotenv()

# ✅ 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("server.log"),  # 로그를 파일에 저장
        logging.StreamHandler()  # 콘솔에도 출력
    ]
)

app = FastAPI()

# ✅ CORS 설정 추가 (다른 컴퓨터에서 요청 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 🔥 모든 도메인에서 접근 허용 (보안상 필요하면 특정 도메인만 허용)
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용 (OPTIONS 포함)
    allow_headers=["*"],  # 모든 헤더 허용
)

# ✅ 요청 받을 데이터 모델 정의
class QueryRequest(BaseModel):
    question: str

# ✅ 환경 변수에서 로컬 GPU 서버 주소 가져오기
LOCAL_GPU_SERVER = os.getenv("LOCAL_GPU_SERVER")

# ✅ 서버 상태 확인용 GET 엔드포인트 추가 (Cloudtype 호환)
@app.get("/health")
@app.get("/healthz")  # Cloudtype 헬스체크 대응
def health_check():
    logging.info("✅ Health Check 요청 받음")
    return {"status": "OK", "message": "Server is running"}

# ✅ 질문을 받아 로컬 GPU 서버로 요청을 전달하는 POST 엔드포인트
@app.post("/ask")
async def ask_question(request: QueryRequest, client_request: Request):
    user_query = request.question.strip()
    client_ip = client_request.client.host  # 요청한 클라이언트 IP 가져오기
    
    logging.info(f"📝 [{client_ip}] 질문 받음: {user_query}")

    if not user_query:
        logging.warning(f"⚠️ [{client_ip}] 질문이 비어 있음")
        return {"error": "질문을 입력하세요."}

    if not LOCAL_GPU_SERVER:
        logging.error("❌ LOCAL_GPU_SERVER 환경 변수가 설정되지 않음")
        return {
            "error": "서버 설정 오류: LOCAL_GPU_SERVER 환경 변수가 없습니다.",
            "debug_info": os.environ  # 디버깅을 위해 환경 변수 정보 추가
        }

    try:
        target_url = f"{LOCAL_GPU_SERVER}/gpu_ask"
        logging.info(f"🔄 [{client_ip}] 로컬 GPU 서버로 요청 전송: {target_url}")

        response = requests.post(target_url, json={"question": user_query})

        if response.status_code == 200:
            logging.info(f"✅ [{client_ip}] 로컬 GPU 서버 응답 성공")
            return response.json()
        else:
            logging.error(f"❌ [{client_ip}] 로컬 GPU 서버 응답 실패 - 상태 코드: {response.status_code}")
            return {"error": f"로컬 GPU 서버 오류: {response.status_code}", "details": response.text}

    except requests.exceptions.RequestException as e:
        logging.exception(f"❌ [{client_ip}] 로컬 GPU 서버 요청 실패")
        return {"error": f"로컬 GPU 서버 요청 실패: {e}"}

# ✅ Cloudtype에서 실행
if __name__ == "__main__":
    logging.info("🚀 FastAPI 서버 시작됨 (Cloudtype 환경에서 실행 중)")
    logging.info(f"🌐 서버 주소: http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
