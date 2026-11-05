
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Be Na server is ready!"}

@app.get("/healthz")
async def health():
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        await websocket.send_json({
            "type": "status",
            "message": "Be Na da ket noi!"
        })

        while True:
            message = await websocket.receive_text()

            await websocket.send_json({
                "type": "echo",
                "message": message
            })

    except WebSocketDisconnect:
        print("Robot da ngat ket noi")
