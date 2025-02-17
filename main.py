import os
import requests
import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
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

# ✅ FastAPI 인스턴스 생성 (root_path 설정 추가)
app = FastAPI(root_path="/")

# ✅ CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Cloudtype의 `download/` 폴더 설정
DOWNLOAD_DIR = os.path.abspath("download")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

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

# ✅ 서버 상태 확인 엔드포인트 (Cloudtype에서 `/healthz`를 찾을 수 있도록 추가)
@app.get("/healthz")
@app.get("/health")
def health_check():
    logging.info("✅ Health Check 요청 받음")
    return {"status": "OK", "message": "Cloudtype FastAPI Server is running"}

# ✅ 문서 생성 요청을 로컬 GPU 서버로 전달하는 엔드포인트
@app.post("/generate-document")
async def generate_document(request: ContractRequest):
    """✅ Cloudtype이 로컬 GPU 서버로 문서 생성 요청을 보냄"""
    logging.info(f"📄 문서 생성 요청 받음: {request}")

    if not LOCAL_GPU_SERVER:
        return {"error": "서버 설정 오류: LOCAL_GPU_SERVER 환경 변수가 없습니다."}

    target_url = f"{LOCAL_GPU_SERVER}/generate-document"
    logging.info(f"🔄 로컬 GPU 서버로 문서 생성 요청 전송: {target_url}")

    try:
        response = requests.post(target_url, json=request.dict(), timeout=300)

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"문서 생성 오류: {response.status_code}", "details": response.text}

    except requests.exceptions.RequestException as e:
        return {"error": f"문서 생성 요청 실패: {e}"}

# ✅ Cloudtype에서 `/download/{file_name}` 엔드포인트 추가
@app.get("/download/{file_name}")
async def download_file(file_name: str):
    """✅ Cloudtype에서 직접 PDF 다운로드 제공"""
    file_path = os.path.join(DOWNLOAD_DIR, file_name)

    if not os.path.exists(file_path):
        logging.error(f"❌ 다운로드 요청한 파일이 존재하지 않음: {file_name}")
        return JSONResponse(content={"error": "파일이 존재하지 않습니다."}, status_code=404)

    logging.info(f"✅ Cloudtype에서 PDF 다운로드 요청: {file_name}")
    return FileResponse(file_path, media_type="application/pdf", filename=file_name)

if __name__ == "__main__":
    logging.info("🚀 FastAPI 서버 시작됨 (Cloudtype 환경에서 실행 중)")

    # ✅ Cloudtype에서 `download/` 폴더 생성 (최초 실행 시)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=300)
