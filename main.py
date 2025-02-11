import os
import requests
import logging
from dotenv import load_dotenv
from fastapi import FastAPI
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

# ✅ CORS 설정 추가 (모든 출처 허용 → 필요 시 특정 도메인만 허용 가능)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

# ✅ 요청 받을 데이터 모델 정의
class QueryRequest(BaseModel):
    question: str

# ✅ 환경 변수에서 로컬 GPU 서버 주소 가져오기
LOCAL_GPU_SERVER = os.getenv("LOCAL_GPU_SERVER")

if not LOCAL_GPU_SERVER:
    logging.error("❌ LOCAL_GPU_SERVER 환경 변수가 설정되지 않음!")
else:
    if not LOCAL_GPU_SERVER.startswith(("http://", "https://")):
        LOCAL_GPU_SERVER = "http://" + LOCAL_GPU_SERVER
        logging.warning(f"⚠️ LOCAL_GPU_SERVER에 스키마가 없어서 자동 추가됨: {LOCAL_GPU_SERVER}")

# ✅ 서버 상태 확인용 엔드포인트 (Cloudtype 헬스체크 대응)
@app.get("/health")
@app.get("/healthz")
def health_check():
    logging.info("✅ Health Check 요청 받음")
    return {"status": "OK", "message": "Cloudtype FastAPI Server is running"}

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

    # ✅ 요청을 보내기 전에 URL 로그 출력
    target_url = f"{LOCAL_GPU_SERVER}/gpu_ask"
    logging.info(f"🔄 로컬 GPU 서버로 요청 전송: {target_url}")

    try:
        response = requests.post(target_url, json={"question": user_query}, timeout=60)

        if response.status_code == 200:
            logging.info(f"✅ 로컬 GPU 서버 응답 성공")
            return response.json()
        else:
            logging.error(f"❌ 로컬 GPU 서버 응답 실패 - 상태 코드: {response.status_code}")
            return {"error": f"로컬 GPU 서버 오류: {response.status_code}", "details": response.text}

    except requests.exceptions.ConnectionError:
        logging.exception("❌ 로컬 GPU 서버에 연결할 수 없음")
        return {"error": "로컬 GPU 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요."}

    except requests.exceptions.Timeout:
        logging.exception("❌ 로컬 GPU 서버 응답 시간 초과")
        return {"error": "로컬 GPU 서버 응답 시간이 초과되었습니다."}

    except requests.exceptions.RequestException as e:
        logging.exception("❌ 로컬 GPU 서버 요청 실패")
        return {"error": f"로컬 GPU 서버 요청 실패: {e}"}

# ✅ Cloudtype에서 실행
if __name__ == "__main__":
    logging.info("🚀 FastAPI 서버 시작됨 (Cloudtype 환경에서 실행 중)")
    uvicorn.run(app, host="0.0.0.0", port=8000)
