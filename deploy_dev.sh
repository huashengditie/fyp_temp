#!/bin/bash

# ================= Configuration =================
BASE_DIR=$HOME/pathway_agent
IMG_DIR=$BASE_DIR/images
LOG_DIR=$BASE_DIR/logs
CODE_DIR=$BASE_DIR/services
DATA_DIR=$BASE_DIR/data/agent_memory

mkdir -p $LOG_DIR
mkdir -p $DATA_DIR 

echo "[1/3] Cleaning up old services..."
pkill -f uvicorn
pkill -f streamlit

apptainer instance stop --all > /dev/null 2>&1
sleep 2

export APPTAINERENV_PYTHONNOUSERSITE=1 
export APPTAINERENV_PYTHONUNBUFFERED=1

echo "[2/3] Starting Backend Tool Services..."

# 1. dGPredictor (Port 8002)
echo "   -> dGPredictor (8002)..."
nohup apptainer exec \
  --bind $CODE_DIR/dGPredictor:/app \
  $IMG_DIR/dg.sif \
  bash -c "cd /app && uvicorn server:app --host 0.0.0.0 --port 8002" > $LOG_DIR/dg.log 2>&1 &

# 2. EnzRank (Port 8003)
echo "   -> EnzRank (8003)..."
nohup apptainer exec --nv \
  --bind $CODE_DIR/EnzRank:/app \
  $IMG_DIR/enz.sif \
  bash -c "cd /app && uvicorn server:app --host 0.0.0.0 --port 8003" > $LOG_DIR/enz.log 2>&1 &

# 3. SearchMEResource (Port 8004)
echo "   -> SearchMEResource (8004)..."
nohup apptainer exec \
  --bind $CODE_DIR/SearchMEResource:/app \
  $IMG_DIR/search_me.sif \
  bash -c "cd /app && uvicorn main:app --host 0.0.0.0 --port 8004" > $LOG_DIR/search_me.log 2>&1 &

# 4. eQuilibrator (Port 8005)
echo "   -> eQuilibrator (8005)... (Warning: DB loading takes 1-2 mins)"
nohup apptainer exec \
  --bind $CODE_DIR/eQuilibrator:/app \
  $IMG_DIR/equilibrator.sif \
  bash -c "cd /app && uvicorn main:app --host 0.0.0.0 --port 8005" > $LOG_DIR/equilibrator.log 2>&1 &

sleep 3

echo "[3/3] Starting Agent Core & Frontend..."

# 5. Agent Core (Port 8081)
export APPTAINERENV_OLLAMA_HOST=http://127.0.0.1:11434
export APPTAINERENV_DG_PREDICTOR_URL=http://127.0.0.1:8002/predict
export APPTAINERENV_ENZRANK_URL=http://127.0.0.1:8003/rank
export APPTAINERENV_MERESOURCE_URL=http://127.0.0.1:8004
export APPTAINERENV_EQUILIBRATOR_URL=http://127.0.0.1:8005/calculate
export APPTAINERENV_AGENT_MEMORY_PATH=/persistence/agent_memory.sqlite

echo "   -> Agent Core (8081)..."
nohup apptainer exec \
  --bind $CODE_DIR/agent-core:/app \
  --bind $DATA_DIR:/persistence \
  $IMG_DIR/agent.sif \
  bash -c "cd /app && uvicorn main:app --host 0.0.0.0 --port 8081" > $LOG_DIR/agent.log 2>&1 &

# 6. Frontend (Port 8501)
echo "   -> Frontend (8501)..."
nohup apptainer exec \
  --bind $CODE_DIR/frontend:/app \
  --env AGENT_URL="http://127.0.0.1:8081/chat" \
  $IMG_DIR/frontend.sif \
  bash -c "cd /app && streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true" > $LOG_DIR/frontend.log 2>&1 &

echo "Deployment completed!"
echo "-------------------------------------------------------"
echo "Frontend URL:    http://<SERVER_IP>:8501"
echo "Agent Core API:  http://<SERVER_IP>:8081"
echo "Memory DB:       $DATA_DIR/agent_memory.sqlite"
echo "Logs Directory:  $LOG_DIR"
echo "-------------------------------------------------------"
echo "Note: eQuilibrator is loading its 1.5GB DB cache in the background."
echo "You can check its progress with: tail -f $LOG_DIR/equilibrator.log"