from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="AI Travel Advisor API")


@app.get("/")
def home():
    return {"message": "Welcome to AI Travel Advisor API"}


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
def chat(request: ChatRequest):
    return {
        "reply": f"You said: {request.message}"
    }