import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Union

from batch_predict import EnzRankService

app = FastAPI()

predictor: EnzRankService = None


@app.on_event("startup")
def load_model():
    """
    Execute when FastAPI starts.
    Load the model into memory to avoid loading it with every request.
    """
    global predictor
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(base_dir, 'CNN_model_final', 'Final_model.model')
        csv_path = os.path.join(base_dir, 'CNN_data_kegg', 'kegg_compound.csv')

        predictor = EnzRankService(model_path=model_path, csv_path=csv_path)
    except Exception as e:
        print(f"CRITICAL: Failed to load EnzRank model: {e}")
        predictor = None


class RequestData(BaseModel):
    data: Union[List[Dict[str, Any]], Dict[str, Any]]


@app.post("/rank")
def run_prediction(req: RequestData):
    global predictor
    if predictor is None:
        raise HTTPException(status_code=500, detail="Model not initialized. Check server logs.")

    input_data = req.data
    if isinstance(input_data, dict):
        input_data = list(input_data.values())

    try:
        results = predictor.predict_batch(input_data)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


if __name__ == "__main__":
    print("Starting EnzRank Server (Fast Mode)...")
    uvicorn.run(app, host="0.0.0.0", port=8003)