#!/bin/bash
# Install FS Source Daemon as a systemd service
# This will make it start automatically at boot

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/fs-source.service"
SYSTEM_SERVICE="/etc/systemd/system/fs-source.service"

echo "================================"
echo "FS Source Daemon - Install Service"
echo "================================"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "⚠️  Don't run this script as root or with sudo"
    echo "The script will ask for sudo password when needed"
    exit 1
fi

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ Service file not found: $SERVICE_FILE"
    exit 1
fi

echo "This will install FS Source Daemon to run automatically at startup"
echo ""
echo "Service details:"
echo "  - Starts at boot"
echo "  - Runs in standby when OBS is not active"
echo "  - Activates when OBS starts streaming/recording"
echo "  - Auto-restarts on failure"
echo ""

read -p "Continue with installation? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled"
    exit 0
fi

# Generate service file with user-specific paths
echo "Generating service file..."
TEMP_SERVICE="/tmp/fs-source-$USER.service"
sed -e "s|__USER__|$USER|g" \
    -e "s|__INSTALL_DIR__|$SCRIPT_DIR|g" \
    "$SERVICE_FILE" > "$TEMP_SERVICE"

# Copy service file
echo "Installing service file..."
sudo cp "$TEMP_SERVICE" "$SYSTEM_SERVICE"

if [ $? -ne 0 ]; then
    echo "❌ Failed to copy service file"
    rm -f "$TEMP_SERVICE"
    exit 1
fi

# Clean up temp file
rm -f "$TEMP_SERVICE"

# Reload systemd
echo "Reloading systemd..."
sudo systemctl daemon-reload

# Enable service
echo "Enabling service..."
sudo systemctl enable fs-source.service

# Ask if user wants to start now
echo ""
read -p "Start the service now? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting service..."
    sudo systemctl start fs-source.service
    sleep 2
    
    # Show status
    echo ""
    echo "Service status:"
    sudo systemctl status fs-source.service --no-pager -l
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "Useful commands:"
echo "  Start:   sudo systemctl start fs-source"
echo "  Stop:    sudo systemctl stop fs-source"
echo "  Restart: sudo systemctl restart fs-source"
echo "  Status:  sudo systemctl status fs-source"
echo "  Logs:    sudo journalctl -u fs-source -f"
echo "  Disable: sudo systemctl disable fs-source"
echo ""
