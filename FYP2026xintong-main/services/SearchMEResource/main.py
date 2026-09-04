from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from me_agent_logic import MEResourceAgent
import os

app = FastAPI(title="SearchMEResource API Service")

# Dataset location relative to this file
DATASET_DIR = os.path.join(os.path.dirname(__file__), "Dataset")
agent = MEResourceAgent(DATASET_DIR)

class QueryRequest(BaseModel):
    product: str
    host: str = "iJN1463"
    carbon: str = "D-glucose"

@app.post("/query")
async def handle_query(request: QueryRequest):
    try:
        # Calls the query logic and returns JSON
        result = agent.query_design(request.product, request.host, request.carbon)
        return result
    except Exception as e:
        # Standard error handling
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Listening on port 8004
    uvicorn.run(app, host="0.0.0.0", port=8004)