import os
import requests
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
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

# ✅ 로컬 GPU 서버 (ngrok URL) 가져오기
LOCAL_GPU_SERVER = os.getenv("LOCAL_GPU_SERVER", "").strip()

if not LOCAL_GPU_SERVER:
    logging.error("❌ LOCAL_GPU_SERVER 환경 변수가 설정되지 않음!")

if LOCAL_GPU_SERVER and not LOCAL_GPU_SERVER.startswith(("http://", "https://")):
    LOCAL_GPU_SERVER = "http://" + LOCAL_GPU_SERVER
    logging.warning(f"⚠️ LOCAL_GPU_SERVER에 스키마가 없어서 자동 추가됨: {LOCAL_GPU_SERVER}")

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

# ✅ SSE를 이용한 문서 생성 상태 스트리밍
@app.post("/generate-document")
async def generate_document(request: ContractRequest):
    """✅ SSE(Server-Sent Events) 방식으로 문서 생성 상태 업데이트"""

    async def event_stream():
        try:
            yield "data: 문서 생성 요청을 처리 중입니다...\n\n"
            
            target_url = f"{LOCAL_GPU_SERVER}/generate-document"
            logging.info(f"🔄 로컬 GPU 서버로 문서 생성 요청 전송: {target_url}")

            with requests.post(target_url, json=request.model_dump(), stream=True, timeout=600) as response:
                if response.status_code == 200:
                    for line in response.iter_lines():
                        if line:
                            yield f"data: {line.decode('utf-8')}\n\n"

                else:
                    logging.error(f"❌ 문서 생성 실패 - 상태 코드: {response.status_code}")
                    yield f"data: 오류 발생 - 상태 코드: {response.status_code}\n\n"

        except requests.exceptions.RequestException as e:
            logging.exception("❌ 문서 생성 요청 실패")
            yield f"data: 문서 생성 중 오류 발생: {str(e)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    logging.info("🚀 FastAPI 서버 시작됨 (로컬에서 실행 중)")
    uvicorn.run(app, host="0.0.0.0", port=8001)
