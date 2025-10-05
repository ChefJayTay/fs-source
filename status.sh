#!/bin/bash
# Project Status Summary

echo "================================"
echo "FS Source - Project Status"
echo "================================"
echo ""

# Check virtual environment
if [ -d "venv" ]; then
    echo "✅ Virtual environment: Ready"
else
    echo "❌ Virtual environment: Missing"
fi

# Check config
if [ -f "config/obs_config.json" ]; then
    echo "✅ Configuration file: Exists"
else
    echo "⚠️  Configuration file: Not configured (run setup.py)"
fi

# Check Python files
echo ""
echo "Python Scripts:"
echo "  ✅ fs_source.py - Remote mode (OBS WebSocket)"
echo "  ✅ fs_source_daemon.py - Daemon mode (always-on)"
echo "  ✅ fs_source_native.py - Native mode (local camera)"
echo "  ✅ setup.py - Configuration wizard"
echo "  ✅ test_obs_connection.py - OBS connection tester"
echo "  ✅ test_local_camera.py - Local camera finder"

# Check documentation
echo ""
echo "Documentation:"
echo "  ✅ README.md - User guide"
echo "  ✅ QUICKSTART.md - Quick start guide"
echo "  ✅ OVERVIEW.md - Technical overview"

# Check dependencies
echo ""
echo "Checking dependencies..."
source venv/bin/activate 2>/dev/null
if python -c "import cv2, mediapipe, obswebsocket" 2>/dev/null; then
    echo "✅ All dependencies installed"
else
    echo "⚠️  Some dependencies missing"
fi

echo ""
echo "================================"
echo "Next Steps:"
echo "================================"
echo "1. Configure: python setup.py"
echo "2. Test connection: python test_obs_connection.py"
echo "3. Choose mode:"
echo "   Remote:  ./run.sh            (OBS WebSocket, network)"
echo "   Daemon:  ./run_daemon.sh     (always-on, smart standby)"
echo "   Native:  ./run_native.sh     (local camera, no NDI)"
echo "   Service: ./install_service.sh (auto-start at boot)"
echo ""
echo "For Native mode: python test_local_camera.py (find cameras)"
echo ""

# Check if service is installed
if systemctl is-enabled fs-source.service &>/dev/null; then
    echo "📌 Service Status:"
    systemctl is-active fs-source.service &>/dev/null && echo "   ✅ Running" || echo "   ⏸️  Stopped"
fi
