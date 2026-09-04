import os
import json
import uuid
import subprocess
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "tmp", "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "tmp", "output")

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


class RequestData(BaseModel):
    data: dict  # {"R01": "A+B<=>C"}


def cleanup(paths):
    for p in paths:
        try:
            if os.path.exists(p): os.remove(p)
        except Exception as e:
            print(f"Cleanup error: {e}")


@app.post("/predict")
def run_prediction(req: RequestData, bg_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    input_path = os.path.join(INPUT_DIR, f"{job_id}.json")
    output_path = os.path.join(OUTPUT_DIR, f"{job_id}.json")

    print(f"Received task {job_id}, writing to {input_path}")

    # 1. Write tmp input
    try:
        with open(input_path, 'w') as f:
            json.dump(req.data, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write input: {e}")

    # 2. Envoke script
    cmd = [
        "python", "batch_predict.py",
        "--input_file", input_path,
        "--output_file", output_path
    ]

    try:
        # capture_output=True
        result = subprocess.run(cmd, check=True, cwd=BASE_DIR, capture_output=True, text=True)
        print("Script Output:", result.stdout)
    except subprocess.CalledProcessError as e:
        print("Script Error:", e.stderr)
        return {"error": "Prediction script failed", "details": e.stderr}

    # 3. Read Result
    if os.path.exists(output_path):
        with open(output_path, 'r') as f:
            res = json.load(f)

        # 4. Cleanup
        bg_tasks.add_task(cleanup, [input_path, output_path])
        return res
    else:
        return {"error": "No output file generated"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)