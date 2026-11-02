from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Bé Na Cloud AI đã sẵn sàng!"}
