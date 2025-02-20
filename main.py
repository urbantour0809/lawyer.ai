import os
import requests
import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# ✅ 환경 변수 로드
load_dotenv()

# ✅ 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("server.log"),
        logging.StreamHandler()
    ]
)

# ✅ FastAPI 인스턴스 생성
app = FastAPI()

# ✅ CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ 로컬 서버에서 사용할 `download/` 폴더 설정
DOWNLOAD_DIR = os.path.abspath("download")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ✅ 로컬 GPU 서버 (ngrok URL) 가져오기
LOCAL_GPU_SERVER = os.getenv("LOCAL_GPU_SERVER", "").strip()

if not LOCAL_GPU_SERVER:
    logging.error("❌ LOCAL_GPU_SERVER 환경 변수가 설정되지 않음!")

if LOCAL_GPU_SERVER and not LOCAL_GPU_SERVER.startswith(("http://", "https://")):
    LOCAL_GPU_SERVER = "http://" + LOCAL_GPU_SERVER
    logging.warning(f"⚠️ LOCAL_GPU_SERVER에 스키마가 없어서 자동 추가됨: {LOCAL_GPU_SERVER}")

# ✅ `LOCAL_GPU_SERVER` 값을 제공하는 엔드포인트 추가
@app.get("/get-local-gpu-server")
async def get_local_gpu_server():
    """✅ `LOCAL_GPU_SERVER` 값을 반환하는 엔드포인트"""
    return {"LOCAL_GPU_SERVER": LOCAL_GPU_SERVER}

# ✅ 요청 받을 데이터 모델 정의
class QueryRequest(BaseModel):
    question: str

class ContractRequest(BaseModel):
    contract_type: str
    party_a: str
    party_b: str
    contract_date: str
    additional_info: str = ""

# ✅ 서버 상태 확인 엔드포인트
@app.get("/healthz")
@app.get("/health")
def health_check():
    logging.info("✅ Health Check 요청 받음")
    return {"status": "OK", "message": "FastAPI 로컬 서버가 정상적으로 실행 중입니다."}

# ✅ 질문을 받아 로컬 GPU 서버로 요청을 전달하는 엔드포인트
@app.post("/ask")
async def ask_question(request: QueryRequest):
    user_query = request.question.strip()
    logging.info(f"📝 질문 받음: {user_query}")

    if not user_query:
        logging.warning("⚠️ 빈 질문 입력됨")
        return {"error": "질문을 입력하세요."}

    if not LOCAL_GPU_SERVER:
        logging.error("❌ LOCAL_GPU_SERVER 환경 변수가 설정되지 않음")
        return {"error": "서버 설정 오류: LOCAL_GPU_SERVER 환경 변수가 없습니다."}

    target_url = f"{LOCAL_GPU_SERVER}/gpu_ask"
    logging.info(f"🔄 로컬 GPU 서버로 요청 전송: {target_url}")

    try:
        response = requests.post(target_url, json={"question": user_query}, timeout=180)

        if response.status_code == 200:
            logging.info(f"✅ 로컬 GPU 서버 응답 성공")
            return response.json()
        else:
            logging.error(f"❌ 로컬 GPU 서버 응답 실패 - 상태 코드: {response.status_code}")
            return {"error": f"로컬 GPU 서버 오류: {response.status_code}", "details": response.text}

    except requests.exceptions.RequestException as e:
        logging.exception("❌ 로컬 GPU 서버 요청 실패")
        return {"error": f"로컬 GPU 서버 요청 실패: {e}"}

# ✅ 문서 생성 요청을 로컬 GPU 서버에서 처리
@app.post("/generate-document")
async def generate_document(request: ContractRequest):
    """✅ Cloudtype이 로컬 GPU 서버로 문서 생성 요청을 보냄"""
    logging.info(f"📄 문서 생성 요청 받음: {request}")

    if not LOCAL_GPU_SERVER:
        return {"error": "서버 설정 오류: LOCAL_GPU_SERVER 환경 변수가 없습니다."}

    target_url = f"{LOCAL_GPU_SERVER}/generate-document"
    
    # ✅ 요청 데이터에 main.py의 URL 추가
    request_data = request.model_dump()
    request_data["server_url"] = os.getenv("SERVER_URL", "http://localhost:8000")  # Cloudtype 서버 URL
    
    logging.info(f"🔄 로컬 GPU 서버로 문서 생성 요청 전송: {target_url}")

    try:
        response = requests.post(target_url, json=request_data, timeout=600)

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"문서 생성 오류: {response.status_code}", "details": response.text}

    except requests.exceptions.RequestException as e:
        return {"error": f"문서 생성 요청 실패: {e}"}

# ✅ 서버 시작시 LOCAL_GPU_SERVER 값을 로컬 GPU 서버에 전달
@app.on_event("startup")
async def startup_event():
    """서버 시작시 LOCAL_GPU_SERVER 값을 로컬 GPU 서버에 전달"""
    if LOCAL_GPU_SERVER:
        try:
            setup_url = f"{LOCAL_GPU_SERVER}/set-server-url"
            response = requests.post(setup_url, json=LOCAL_GPU_SERVER)
            if response.status_code == 200:
                logging.info("✅ LOCAL_GPU_SERVER 값을 로컬 서버에 성공적으로 전달했습니다.")
            else:
                logging.error(f"❌ LOCAL_GPU_SERVER 값 전달 실패: {response.status_code}")
        except Exception as e:
            logging.error(f"❌ LOCAL_GPU_SERVER 값 전달 중 오류 발생: {str(e)}")

if __name__ == "__main__":
    logging.info("🚀 FastAPI 서버 시작됨 (로컬에서 실행 중)")
    uvicorn.run(app, host="0.0.0.0", port=8001)
