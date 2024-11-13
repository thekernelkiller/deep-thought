from fastapi import FastAPI
from pydantic import BaseModel
from gemini_app import chat_companion
import asyncio

app = FastAPI()

class Question(BaseModel):
    text: str
    history: list = []

@app.post("/chat")
async def chat(question: Question):
    response = await chat_companion(question.text, question.history)
    return {"response": response}