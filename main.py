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

# ✅ 요청 받을 데이터 모델 정의
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

# ✅ 문서 생성 요청을 로컬 서버에서 처리
@app.post("/generate-document")
async def generate_document(request: ContractRequest):
    """✅ 로컬에서 PDF 문서를 생성"""
    logging.info(f"📄 문서 생성 요청 받음: {request}")

    # ✅ 서버 내부에서 직접 `/generate-document` 호출
    try:
        response = requests.post("http://127.0.0.1:8000/generate-document", json=request.dict(), timeout=300)

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"문서 생성 오류: {response.status_code}", "details": response.text}

    except requests.exceptions.RequestException as e:
        return {"error": f"문서 생성 요청 실패: {e}"}

if __name__ == "__main__":
    logging.info("🚀 FastAPI 서버 시작됨 (로컬에서 실행 중)")
    uvicorn.run(app, host="0.0.0.0", port=8001)
