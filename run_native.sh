#!/bin/bash
# FS Source Native Launcher
# Runs the native version (local camera, no NDI needed)

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

echo "Starting FS Source (Native Mode)..."
echo "Using local camera directly (no NDI)"
echo "Press Ctrl+C to stop"
echo ""

# Run the native application
python fs_source_native.py
