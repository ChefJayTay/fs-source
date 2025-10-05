#!/bin/bash
# Uninstall FS Source Daemon systemd service

SYSTEM_SERVICE="/etc/systemd/system/fs-source.service"

echo "================================"
echo "FS Source Daemon - Uninstall Service"
echo "================================"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo "⚠️  Don't run this script as root or with sudo"
    echo "The script will ask for sudo password when needed"
    exit 1
fi

# Check if service is installed
if [ ! -f "$SYSTEM_SERVICE" ]; then
    echo "ℹ️  Service is not installed"
    exit 0
fi

read -p "Remove FS Source Daemon service from startup? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstallation cancelled"
    exit 0
fi

# Stop service if running
echo "Stopping service..."
sudo systemctl stop fs-source.service

# Disable service
echo "Disabling service..."
sudo systemctl disable fs-source.service

# Remove service file
echo "Removing service file..."
sudo rm "$SYSTEM_SERVICE"

# Reload systemd
echo "Reloading systemd..."
sudo systemctl daemon-reload
sudo systemctl reset-failed

echo ""
echo "✅ Service uninstalled successfully"
echo ""
echo "The application files are still in: $(pwd)"
echo "You can still run manually with: ./run.sh or ./run_daemon.sh"
echo ""
