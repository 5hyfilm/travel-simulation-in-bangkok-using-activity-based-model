#!/bin/bash

echo "=========================================="
echo "   Bangkok MATSim One-Click Runner"
echo "=========================================="

# Define the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Activate Python Virtual Environment
echo ">>> Activating virtual environment..."
if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
    echo "Virtual environment activated successfully."
else
    echo "Warning: Virtual environment not found at $PROJECT_ROOT/venv."
    echo "Attempting to run with default system Python..."
fi

# 2. Run the main pipeline (which now handles both preprocessing and MATSim)
echo ">>> Starting the simulation pipeline..."
cd "$PROJECT_ROOT/preprocess" || exit
python main.py

echo "=========================================="
echo "   Run Completed"
echo "=========================================="
