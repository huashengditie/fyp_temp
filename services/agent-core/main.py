from fastapi import FastAPI
from pydantic import BaseModel
import logging
import uuid
from langchain.globals import set_debug

from app.agents.graph import run_graph, get_history_from_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
set_debug(True) 

app = FastAPI()

class QueryRequest(BaseModel):
    query: str
    thread_id: str = "default-session"

@app.get("/history/{thread_id}")
def fetch_history(thread_id: str):
    history = get_history_from_db(thread_id)
    return {"history": history}

@app.post("/chat")
def chat(request: QueryRequest):
    thread_id = request.thread_id
    
    result, logs = run_graph(request.query, thread_id=thread_id)
    
    return {
        "response": result,
        "logs": logs,
        "thread_id": thread_id
    }