import os
import requests
import logging
from dotenv import load_dotenv
from fastapi import FastAPI
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

# ✅ 요청 받을 데이터 모델 정의
class QueryRequest(BaseModel):
    question: str

# ✅ 환경 변수에서 로컬 GPU 서버 주소 가져오기
LOCAL_GPU_SERVER = os.getenv("LOCAL_GPU_SERVER")

# ✅ 서버 상태 확인용 GET 엔드포인트 추가
@app.get("/health")
def health_check():
    logging.info("✅ Health Check 요청 받음")
    return {"status": "OK", "message": "Server is running"}

# ✅ 질문을 받아 로컬 GPU 서버로 요청을 전달하는 POST 엔드포인트
@app.post("/ask")
def ask_question(request: QueryRequest):
    user_query = request.question.strip()
    
    logging.info(f"📝 질문 받음: {user_query}")

    if not user_query:
        logging.warning("⚠️ 질문이 비어 있음")
        return {"error": "질문을 입력하세요."}

    if not LOCAL_GPU_SERVER:
        logging.error("❌ LOCAL_GPU_SERVER 환경 변수가 설정되지 않음")
        return {"error": "서버 설정 오류: LOCAL_GPU_SERVER 환경 변수가 없습니다."}

    try:
        logging.info(f"🔄 로컬 GPU 서버로 요청 전송: {LOCAL_GPU_SERVER}/gpu_ask")
        response = requests.post(f"{LOCAL_GPU_SERVER}/gpu_ask", json={"question": user_query})

        if response.status_code == 200:
            logging.info("✅ 로컬 GPU 서버 응답 성공")
            return response.json()
        else:
            logging.error(f"❌ 로컬 GPU 서버 응답 실패 - 상태 코드: {response.status_code}")
            return {"error": f"로컬 GPU 서버 오류: {response.status_code}", "details": response.text}

    except requests.exceptions.RequestException as e:
        logging.exception("❌ 로컬 GPU 서버 요청 실패")
        return {"error": f"로컬 GPU 서버 요청 실패: {e}"}

# ✅ Cloudtype에서 실행
if __name__ == "__main__":
    logging.info("🚀 FastAPI 서버 시작됨")
    uvicorn.run(app, host="0.0.0.0", port=8000)  # Cloudtype에서 실행
