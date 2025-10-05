#!/bin/bash
# FS Source Standard Launcher
# Runs the standard version (manual start/stop)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Installing dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Activate virtual environment
source venv/bin/activate

echo "Starting FS Source (Standard Mode)..."
echo "This will run until you stop it with Ctrl+C"
echo ""

# Run the application
python fs_source.py
