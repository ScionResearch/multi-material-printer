# Installation and Setup Guide
# Scion Multi-Material Printer Control System

## Quick Start - Critical Fixes Applied

This document provides installation instructions for the updated system with critical bug fixes and architectural improvements.

## System Requirements

- Raspberry Pi 4 (or compatible)
- Python 3.8 or higher
- Anycubic Mono X (or compatible) resin printer
- ESP32 WiFi Gateway (optional, for network isolation)
- Stepper motor pump controllers (Adafruit MotorKit or compatible)

## Network Configuration

### ESP32 Gateway Setup (Recommended)

The ESP32 creates an isolated WiFi network:

- **ESP32 Gateway**: 192.168.4.1
- **Raspberry Pi**: 192.168.4.3 (static IP required)
- **Anycubic Printer**: 192.168.4.2
- **WiFi SSID**: PumpedMMP
- **Password**: 00000000

#### Configure Raspberry Pi Static IP

Edit `/etc/dhcpcd.conf`:

```bash
sudo nano /etc/dhcpcd.conf
```

Add at the end:

```
interface wlan0
static ip_address=192.168.4.3/24
static routers=192.168.4.1
static domain_name_servers=192.168.4.1 8.8.8.8
```

Reboot:

```bash
sudo reboot
```

#### Configure Printer Static IP

Use your printer's network settings menu to configure:
- IP Address: 192.168.4.2
- Subnet Mask: 255.255.255.0
- Gateway: 192.168.4.1

## Software Installation

### 1. Clone Repository

```bash
cd ~
git clone https://github.com/ScionResearch/multi-material-printer.git
cd multi-material-printer
```

### 2. Install Python Dependencies

```bash
# Install system packages
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv i2c-tools python3-smbus

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Hardware Access

Enable I2C and GPIO:

```bash
sudo raspi-config
# Navigate to: Interfacing Options > I2C > Enable
# Navigate to: Interfacing Options > GPIO > Enable
```

Add user to required groups:

```bash
sudo usermod -a -G i2c,gpio,dialout pi
```

### 4. Configure Network Settings

Copy template and edit:

```bash
cp config/network_settings.ini.template config/network_settings.ini
nano config/network_settings.ini
```

Verify the printer IP matches your configuration (should be 192.168.4.3 by default).

### 5. Install Systemd Services

Install the two system services:

```bash
# Copy service files
sudo cp config/scion-mmu-web.service /etc/systemd/system/
sudo cp config/scion-mmu-print-manager.service /etc/systemd/system/

# Update paths if you installed to a different location
sudo nano /etc/systemd/system/scion-mmu-web.service
sudo nano /etc/systemd/system/scion-mmu-print-manager.service

# Reload systemd
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable scion-mmu-web.service
sudo systemctl enable scion-mmu-print-manager.service

# Start services
sudo systemctl start scion-mmu-web.service
sudo systemctl start scion-mmu-print-manager.service
```

### 6. Verify Installation

Check service status:

```bash
# Check web interface
sudo systemctl status scion-mmu-web.service

# Check print manager
sudo systemctl status scion-mmu-print-manager.service

# View logs
sudo journalctl -u scion-mmu-web.service -f
sudo journalctl -u scion-mmu-print-manager.service -f
```

Access web interface at: http://192.168.4.2:5000 (or http://localhost:5000 on the Pi)

## Architecture Overview

The system consists of two persistent services:

### 1. Web Interface Service (`scion-mmu-web.service`)
- Flask web server with SocketIO
- User interface for recipe creation and monitoring
- RESTful API endpoints
- WebSocket server for real-time communication

### 2. Print Manager Service (`scion-mmu-print-manager.service`)
- Persistent hardware controller
- Single authority for all printer and pump operations
- Connects to web interface via WebSocket client
- Monitors print progress and executes material changes

### Key Improvements

1. **Eliminated Race Conditions**: Single authority (print manager) for hardware control
2. **Real-time Communication**: WebSocket-based IPC replaces file-based system
3. **Persistent State**: Print manager runs continuously, maintains state across requests
4. **Bug Fixes**: Corrected printer connection check, network configuration
5. **Clean Architecture**: Clear separation of concerns between UI and hardware

## Testing

### Test Printer Connection

```bash
# From Raspberry Pi
cd ~/multi-material-printer
source venv/bin/activate
cd src/controller
python printer_comms.py --auto-connect
```

### Test Pump Motors

Access web interface and navigate to Manual Controls page to test individual pumps.

### Test Material Change Sequence

1. Navigate to Recipe page
2. Create a test recipe (e.g., A,10:B,20)
3. Save recipe
4. Return to Dashboard
5. Click "Test Pumps" to verify pump operation
6. Start a print on the printer
7. Click "Start Multi-Material" to begin automated material changes

## Troubleshooting

### Service Won't Start

```bash
# Check logs for errors
sudo journalctl -u scion-mmu-print-manager.service -n 50 --no-pager

# Check Python path and dependencies
source ~/multi-material-printer/venv/bin/activate
python -c "import websocket_ipc; print('OK')"
```

### Cannot Connect to Printer

```bash
# Verify network connectivity
ping 192.168.4.2

# Test printer communication directly
cd ~/multi-material-printer/src/controller
python printer_comms.py -i 192.168.4.2 -c getstatus
```

### Print Manager Not Connecting to Web App

```bash
# Check if web interface is running
sudo systemctl status scion-mmu-web.service

# Check if port 5000 is accessible
curl http://localhost:5000/api/health

# Restart both services in correct order
sudo systemctl restart scion-mmu-web.service
sudo systemctl restart scion-mmu-print-manager.service
```

### Pump Motors Not Responding

```bash
# Check I2C devices
sudo i2cdetect -y 1

# Check GPIO permissions
groups | grep gpio

# Check motor controller connection
python -c "from adafruit_motorkit import MotorKit; print(MotorKit())"
```

## Manual Operation (Without Systemd)

For development and testing:

```bash
# Terminal 1: Start web interface
cd ~/multi-material-printer/web-app
source ../venv/bin/activate
python app.py

# Terminal 2: Start print manager
cd ~/multi-material-printer/src/controller
source ../../venv/bin/activate
python print_manager.py
```

## Updating the System

```bash
cd ~/multi-material-printer
git pull

# Stop services
sudo systemctl stop scion-mmu-print-manager.service
sudo systemctl stop scion-mmu-web.service

# Update dependencies
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Restart services
sudo systemctl start scion-mmu-web.service
sudo systemctl start scion-mmu-print-manager.service
```

## Configuration Files

- `config/network_settings.ini` - Network and printer configuration
- `config/pump_profiles.json` - Pump calibration and timing
- `config/recipe.txt` - Current material change recipe

## Support

For issues and questions:
- GitHub Issues: https://github.com/ScionResearch/multi-material-printer/issues
- Documentation: See README.md and PRD.md

## Security Notes

- The web interface binds to 0.0.0.0:5000 (accessible on local network)
- No authentication is implemented - use on trusted networks only
- Services run as 'pi' user with hardware access permissions
- Consider adding firewall rules for production deployments
