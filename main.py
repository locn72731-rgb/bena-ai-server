import os
import time
import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO)

app = FastAPI()

API_KEY = os.getenv("OPENAI_API_KEY")
ROBOT_TOKEN = os.getenv("ROBOT_TOKEN")
MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")

client = AsyncOpenAI(api_key=API_KEY) if API_KEY else None

histories = {}
last_request = {}

INSTRUCTIONS = """
Bạn là Bé Na, một robot AI có tính cách nữ dịu dàng,
thân thiện và vui vẻ. Bạn nói tiếng Việt tự nhiên,
dễ hiểu, câu trả lời ngắn gọn.
Bạn đang trò chuyện với người dùng tuổi học sinh.
Luôn giữ nội dung phù hợp lứa tuổi.
Không yêu cầu người dùng tiết lộ mật khẩu,
địa chỉ nhà, số điện thoại hoặc thông tin riêng tư.
Nếu gặp tình huống nguy hiểm, hãy khuyên người dùng
tìm sự giúp đỡ từ người lớn đáng tin cậy.
"""


def check_token(token):
    if not ROBOT_TOKEN or token != ROBOT_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


async def ask_be_na(session_id, message):
    if not client:
        raise RuntimeError("Thieu OPENAI_API_KEY")

    if not message or len(message) > 600:
        return "Bạn hãy gửi câu ngắn hơn nhé!"

    now = time.time()

    if now - last_request.get(session_id, 0) < 2:
        return "Bạn chờ Bé Na một chút nhé!"

    last_request[session_id] = now

    moderation = await client.moderations.create(
        model="omni-moderation-latest",
        input=message
    )

    if moderation.results[0].flagged:
        return "Mình thử chuyển sang chủ đề an toàn hơn nhé!"

    history = histories.setdefault(session_id, [])

    response = await client.responses.create(
        model=MODEL,
        instructions=INSTRUCTIONS,
        input=history + [
            {"role": "user", "content": message}
        ],
        max_output_tokens=180
    )

    answer = response.output_text or "Bé Na chưa nghĩ ra câu trả lời."

    output_check = await client.moderations.create(
        model="omni-moderation-latest",
        input=answer
    )

    if output_check.results[0].flagged:
        answer = "Bé Na chưa thể trả lời câu này. Mình nói chuyện chủ đề khác nhé!"

    history.extend([
        {"role": "user", "content": message},
        {"role": "assistant", "content": answer}
    ])

    histories[session_id] = history[-12:]

    return answer


@app.get("/")
async def root():
    return {"message": "Be Na AI server is ready!"}


@app.get("/healthz")
async def health():
    return {"status": "ok"}


class ChatRequest(BaseModel):
    session_id: str
    message: str
    token: str


@app.post("/chat")
async def chat(data: ChatRequest):
    check_token(data.token)

    try:
        answer = await ask_be_na(
            data.session_id,
            data.message
        )

        return {
            "type": "reply",
            "message": answer
        }

    except Exception:
        logging.exception("LOI KHI GOI AI")
        return JSONResponse(
            status_code=500,
            content={"error": "AI server error"}
        )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token", "")

    if not ROBOT_TOKEN or token != ROBOT_TOKEN:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    session_id = str(id(websocket))

    try:
        await websocket.send_json({
            "type": "status",
            "message": "Be Na da ket noi!"
        })

        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
                message = data.get("message", "")
            except Exception:
                message = raw

            try:
                answer = await ask_be_na(session_id, message)

                await websocket.send_json({
                    "type": "reply",
                    "message": answer
                })

            except Exception:
                logging.exception("LOI AI WEBSOCKET")
                await websocket.send_json({
                    "type": "error",
                    "message": "Be Na dang gap loi ket noi AI."
                })

    except WebSocketDisconnect:
        logging.info("Robot da ngat ket noi")
