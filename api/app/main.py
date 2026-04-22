from fastapi import FastAPI

app = FastAPI()

@app.get("/runtime/health")
def health():
    return {"status": "ok"}
