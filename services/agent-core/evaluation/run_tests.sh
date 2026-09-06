#!/bin/bash

# =======================================================
# Automation Script for Agent Evaluation
# =======================================================

# 1. Determine the directory where this script is located
#    This ensures the script works no matter where you call it from.
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 2. Determine the Project Root (services/agent-core)
#    We assume 'evaluation' is inside 'agent-core', so we go up one level.
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 3. Configure PYTHONPATH
#    This is the most critical step. It tells Python where to look for 'app'.
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"

echo "=========================================="
echo "      Agent Evaluation Pipeline"
echo "=========================================="
echo "Script Dir  : $SCRIPT_DIR"
echo "Project Root: $PROJECT_ROOT"
echo "PYTHONPATH  : Configured"
echo "=========================================="
echo ""

# 4. Step 1: Generate/Refresh Dataset

#echo ">>> [Step 1/2] Generating Test Dataset..."
#python3 "${SCRIPT_DIR}/generate_dataset.py"

#if [ $? -ne 0 ]; then
#echo "? Error: Failed to generate dataset."
#exit 1
#fi
#echo "? Dataset generated successfully."
#echo ""

# 5. Step 2: Run Evaluation
echo ">>> [Step 2/2] Running Evaluation..."
python3 "${SCRIPT_DIR}/run_eval.py"

# Check if the previous command failed
if [ $? -ne 0 ]; then
    echo "? Error: Evaluation script failed."
    exit 1
fi

echo ""
echo "? All steps completed successfully."