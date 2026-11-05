
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

HF_TOKEN = os.getenv("HF_TOKEN")
ROBOT_TOKEN = os.getenv("ROBOT_TOKEN")

MODEL = "openai/gpt-oss-120b:groq"

client = None
if HF_TOKEN:
    client = AsyncOpenAI(
        base_url="https://router.huggingface.co/v1",
        api_key=HF_TOKEN
    )

histories = {}
last_request = {}

INSTRUCTIONS = """
Bạn là Bé Na, robot AI có giọng điệu nữ dịu dàng,
thân thiện và vui vẻ.

Bạn nói tiếng Việt tự nhiên, dễ hiểu, câu trả lời
ngắn gọn và phù hợp với học sinh.

Không yêu cầu người dùng tiết lộ mật khẩu,
địa chỉ nhà, số điện thoại hoặc thông tin riêng tư.

Không hướng dẫn hành vi nguy hiểm.
Nếu người dùng gặp tình huống nguy hiểm,
hãy khuyên tìm sự giúp đỡ từ người lớn đáng tin cậy.
"""


def check_token(token):
    if not ROBOT_TOKEN or token != ROBOT_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )


async def ask_be_na(session_id, message):
    if not client:
        raise RuntimeError("Thieu HF_TOKEN tren Render")

    if not message or len(message) > 600:
        return "Bạn hãy gửi câu ngắn hơn nhé!"

    now = time.time()

    if now - last_request.get(session_id, 0) < 2:
        return "Bạn chờ Bé Na một chút nhé!"

    last_request[session_id] = now

    history = histories.setdefault(session_id, [])

    messages = [
        {
            "role": "system",
            "content": INSTRUCTIONS
        }
    ]

    messages.extend(history)

    messages.append({
        "role": "user",
        "content": message
    })

    response = await client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=180
    )

    answer = response.choices[0].message.content

    if not answer:
        answer = "Bé Na chưa nghĩ ra câu trả lời."

    history.extend([
        {
            "role": "user",
            "content": message
        },
        {
            "role": "assistant",
            "content": answer
        }
    ])

    histories[session_id] = history[-12:]

    return answer


@app.get("/")
async def root():
    return {
        "message": "Be Na Hugging Face server is ready!"
    }


@app.get("/healthz")
async def health():
    return {
        "status": "ok",
        "ai": "configured" if client else "missing HF_TOKEN"
    }


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
        logging.exception("LOI HUGGING FACE AI")

        return JSONResponse(
            status_code=500,
            content={
                "error": "AI server error"
            }
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
                answer = await ask_be_na(
                    session_id,
                    message
                )

                await websocket.send_json({
                    "type": "reply",
                    "message": answer
                })

            except Exception:
                logging.exception("LOI HUGGING FACE WEBSOCKET")

                await websocket.send_json({
                    "type": "error",
                    "message": "Be Na dang gap loi AI."
                })

    except WebSocketDisconnect:
        logging.info("Robot da ngat ket noi")
