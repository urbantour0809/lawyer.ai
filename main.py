import os
import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

# ✅ .env 파일 로드
load_dotenv()

app = FastAPI()

# ✅ 요청 받을 데이터 모델 정의
class QueryRequest(BaseModel):
    question: str

# ✅ 환경 변수에서 로컬 GPU 서버 주소 가져오기
LOCAL_GPU_SERVER = os.getenv("LOCAL_GPU_SERVER")

@app.post("/ask")
def ask_question(request: QueryRequest):
    user_query = request.question.strip()

    # ✅ 내 로컬 GPU 서버로 요청 보내기
    try:
        response = requests.post(f"{LOCAL_GPU_SERVER}/gpu_ask", json={"question": user_query})
        return response.json()  # 로컬 서버에서 받은 응답을 그대로 반환
    except requests.exceptions.RequestException as e:
        return {"error": f"로컬 GPU 서버 요청 실패: {e}"}

# ✅ Cloudtype에서 실행
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)  # Cloudtype에서 실행
