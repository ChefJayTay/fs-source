#!/bin/bash
# FS Source Daemon Launcher
# Runs the daemon version (always-on, smart standby)

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

echo "Starting FS Source Daemon..."
echo "This will run continuously and monitor OBS state"
echo "Press Ctrl+C to stop"
echo ""

# Run the daemon
python fs_source_daemon.py
