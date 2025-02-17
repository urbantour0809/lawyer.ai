import os
import requests
import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

app = FastAPI()

# ✅ CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ 요청 받을 데이터 모델 정의
class ContractRequest(BaseModel):
    contract_type: str
    party_a: str
    party_b: str
    contract_date: str
    additional_info: str = ""

# ✅ 로컬 GPU 서버 주소 가져오기
LOCAL_GPU_SERVER = os.getenv("LOCAL_GPU_SERVER", "").strip()

if not LOCAL_GPU_SERVER:
    logging.error("❌ LOCAL_GPU_SERVER 환경 변수가 설정되지 않음!")

if LOCAL_GPU_SERVER and not LOCAL_GPU_SERVER.startswith(("http://", "https://")):
    LOCAL_GPU_SERVER = "http://" + LOCAL_GPU_SERVER
    logging.warning(f"⚠️ LOCAL_GPU_SERVER에 스키마가 없어서 자동 추가됨: {LOCAL_GPU_SERVER}")

# ✅ 서버 상태 확인 엔드포인트
@app.get("/health")
@app.get("/healthz")
def health_check():
    logging.info("✅ Health Check 요청 받음")
    return {"status": "OK", "message": "Cloudtype FastAPI Server is running"}

# ✅ 문서 생성 요청을 로컬 GPU 서버로 전달하는 엔드포인트
@app.post("/generate-document")
async def generate_document(request: ContractRequest):
    """
    ✅ Cloudtype이 로컬 GPU 서버로 문서 생성 요청을 보냄
    """
    logging.info(f"📄 문서 생성 요청 받음: {request}")

    if not LOCAL_GPU_SERVER:
        return {"error": "서버 설정 오류: LOCAL_GPU_SERVER 환경 변수가 없습니다."}

    target_url = f"{LOCAL_GPU_SERVER}/generate-document"
    logging.info(f"🔄 로컬 GPU 서버로 문서 생성 요청 전송: {target_url}")

    try:
        response = requests.post(target_url, json=request.model_dump(), timeout=240)

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"문서 생성 오류: {response.status_code}", "details": response.text}

    except requests.exceptions.RequestException as e:
        return {"error": f"문서 생성 요청 실패: {e}"}

if __name__ == "__main__":
    logging.info("🚀 FastAPI 서버 시작됨 (Cloudtype 환경에서 실행 중)")
    uvicorn.run(app, host="0.0.0.0", port=8000)
