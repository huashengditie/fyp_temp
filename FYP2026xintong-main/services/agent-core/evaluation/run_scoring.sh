#!/bin/bash

echo "======================================="
echo "   Starting Llama3 Evaluation Scoring  "
echo "======================================="

# Get the directory where this bash script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# 1. Check Python environment
if ! command -v python3 &> /dev/null; then
    echo "[Error] python3 not found. Please install Python first."
    exit 1
fi

# 2. Install dependencies (Using python3 -m pip instead of pip3, and showing logs)
echo "[Info] Checking dependencies (pandas, requests)..."
python3 -m pip install --user pandas requests

# 3. Check if Ollama service is running (Using Python instead of curl)
echo "[Info] Checking Ollama service status..."
if python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:11434/api/tags', timeout=5)" > /dev/null 2>&1; then
    echo "[Success] Ollama service is running normally."
else
    echo "[Error] Cannot connect to local Ollama (http://localhost:11434)."
    echo "Make sure Ollama is running on the host machine."
    exit 1
fi

# 4. Check if the llama3 model is installed (Using Python instead of curl)
echo "[Info] Checking Llama3 model..."
HAS_MODEL=$(python3 -c "import urllib.request, json; data=json.loads(urllib.request.urlopen('http://localhost:11434/api/tags').read().decode('utf-8')); print('True' if any('llama3' in m['name'] for m in data.get('models', [])) else 'False')" 2>/dev/null)

if [ "$HAS_MODEL" != "True" ]; then
    echo "[Warning] llama3 model not detected."
    echo "Attempting to pull model via API (this may take a few minutes)..."
    python3 -c "import urllib.request; req = urllib.request.Request('http://localhost:11434/api/pull', data=b'{\"name\":\"llama3\"}', headers={'Content-Type': 'application/json'}); urllib.request.urlopen(req)"
fi

# 5. Execute the Python script
echo "======================================="
echo "Starting the scoring script..."
python3 "$SCRIPT_DIR/score_eval.py"
echo "======================================="