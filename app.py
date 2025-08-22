from fastapi import FastAPI
from pydantic import BaseModel
import random

app = FastAPI()

# Dummy test publisher
class Post(BaseModel):
    title: str
    content: str

@app.get("/")
def root():
    return {"message": "Agent Loop is running 🚀"}

@app.post("/publish")
def publish(post: Post):
    # Instead of real publishing, return dummy confirmation
    return {
        "status": "success",
        "title": post.title,
        "preview": post.content[:50] + "..."
    }
