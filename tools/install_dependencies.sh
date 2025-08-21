#!/bin/bash

# Scion Multi-Material Unit Controller Installation Script
# This script sets up all dependencies and configures the system for MMU operation

set -e  # Exit on any error

echo "=========================================="
echo "Scion MMU Controller Installation Script"
echo "=========================================="

# Check if running as root (needed for some system operations)
if [[ $EUID -eq 0 ]]; then
   echo "Warning: Running as root. Some operations may need sudo."
fi

# Update system packages
echo "Updating system packages..."
sudo apt update

# Install Qt development libraries
echo "Installing Qt5 development libraries..."
sudo apt install -y qt5-default qtbase5-dev qttools5-dev qttools5-dev-tools

# Install Python dependencies
echo "Installing Python dependencies..."
sudo apt install -y python3 python3-pip python3-venv

# Install networking tools for AP mode
echo "Installing networking tools..."
sudo apt install -y hostapd dnsmasq

# Install GPIO libraries (for Raspberry Pi)
echo "Installing GPIO libraries..."
pip3 install RPi.GPIO gpiozero

# Install other Python packages
echo "Installing Python packages..."
pip3 install requests configparser

# Create Python virtual environment (optional but recommended)
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt 2>/dev/null || echo "requirements.txt not found, skipping..."

# Set up configuration files
echo "Setting up configuration files..."
cd "$(dirname "$0")/.."

# Copy template configuration if it doesn't exist
if [ ! -f "config/network_settings.ini" ]; then
    cp config/network_settings.ini.template config/network_settings.ini
    echo "Created network_settings.ini from template"
fi

# Set up proper permissions for shell scripts
echo "Setting up script permissions..."
chmod +x tools/startAP.sh
chmod +x tools/stopAP.sh
chmod +x tools/install_dependencies.sh

# Build the Qt application
echo "Building Qt application..."
cd src/gui
qmake ScionMMUController.pro
make

echo "=========================================="
echo "Installation completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit config/network_settings.ini for your network setup"
echo "2. Edit config/pump_profiles.json for your pump configuration"
echo "3. Run the application: ./build/ScionMMUController"
echo ""
echo "For AP mode setup, run: sudo ./tools/startAP.sh"
echo "For WiFi mode setup, run: sudo ./tools/stopAP.sh"
echo "=========================================="