import os
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai

app = FastAPI(title="Be Na AI Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

client = genai.Client(api_key=API_KEY) if API_KEY else None

SYSTEM_PROMPT = """
Bạn là Bé Na, một trợ lý AI thân thiện.
Bạn giao tiếp bằng tiếng Việt, trả lời tự nhiên,
ngắn gọn, dễ hiểu và hữu ích.
"""

class ChatRequest(BaseModel):
    text: str

@app.get("/")
def home():
    return {"message": "Be Na AI Server is running!"}

@app.get("/health")
def health():
    return {"status": "ok"}

def ask_gemini(text: str):
    if not client:
        return "Máy chủ chưa được cài đặt Gemini API Key."

    response = client.models.generate_content(
        model=MODEL,
        contents=SYSTEM_PROMPT + "\n\nNgười dùng: " + text
    )

    return response.text or "Bé Na chưa có câu trả lời."

@app.post("/chat")
def chat(request: ChatRequest):
    return {"reply": ask_gemini(request.text)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            message = await websocket.receive_text()

            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "action": "none",
                    "text": "Tin nhắn không đúng định dạng."
                })
                continue

            if data.get("type") == "chat":
                user_text = str(data.get("text", "")).strip()

                if not user_text:
                    reply = "Bạn chưa nhập nội dung."
                else:
                    try:
                        reply = ask_gemini(user_text)
                    except Exception:
                        reply = "Bé Na đang gặp lỗi kết nối AI."

                await websocket.send_json({
                    "action": "none",
                    "text": reply
                })

    except WebSocketDisconnect:
        print("Client disconnected")
