# Quick Reference Card
# Scion Multi-Material Printer Control System

## System Status

```bash
# Check service status
sudo systemctl status scion-mmu-web.service
sudo systemctl status scion-mmu-print-manager.service

# View logs
sudo journalctl -u scion-mmu-web.service -f
sudo journalctl -u scion-mmu-print-manager.service -f

# Restart services
sudo systemctl restart scion-mmu-web.service
sudo systemctl restart scion-mmu-print-manager.service
```

## Network Configuration

| Device           | IP Address     | Port | Notes                    |
|------------------|----------------|------|--------------------------|
| ESP32 Gateway    | 192.168.4.1    | -    | WiFi access point        |
| Raspberry Pi     | 192.168.4.2    | 5000 | Static IP required       |
| Anycubic Printer | 192.168.4.3    | 6000 | Static IP required       |

**WiFi Network:**
- SSID: `PumpedMMP`
- Password: `00000000`

## Web Interface

Access at: `http://192.168.4.2:5000`

**Pages:**
- `/` - Dashboard (status and quick actions)
- `/recipe` - Recipe builder
- `/manual` - Manual pump and printer controls
- `/config` - System configuration

**API Endpoints:**
- `/api/health` - Service health check
- `/api/status` - Current system status
- `/api/recipe` - Recipe management
- `/api/printer/*` - Printer control
- `/api/pump` - Manual pump control
- `/api/multi-material/*` - Multi-material control

## Common Commands

### Printer Communication

```bash
cd ~/multi-material-printer/src/controller
source ../../venv/bin/activate

# Test connection
python printer_comms.py --auto-connect

# Get status
python printer_comms.py -i 192.168.4.3 -c getstatus

# Get file list
python printer_comms.py -i 192.168.4.3 -c getfile

# Pause print
python printer_comms.py -i 192.168.4.3 -c gopause

# Resume print
python printer_comms.py -i 192.168.4.3 -c goresume
```

### Pump Control

```bash
cd ~/multi-material-printer/src/controller
source ../../venv/bin/activate

# Run pump (Motor ID: A/B/C/D, Direction: F/R, Duration: seconds)
python mmu_control.py A F 30  # Pump A forward 30 seconds
python mmu_control.py D R 15  # Drain pump reverse 15 seconds
```

### Recipe Format

File: `config/recipe.txt`

Format: `Material,Layer:Material,Layer:...`

Example:
```
A,50:B,120:C,200:D,300
```

This means:
- Start with Material A
- Change to B at layer 50
- Change to C at layer 120  
- Change to D at layer 200
- Continue with D until layer 300

## Pump Configuration

File: `config/pump_profiles.json`

```json
{
  "pumps": {
    "pump_a": {
      "name": "Pump A",
      "gpio_pin": 18,
      "flow_rate_ml_per_second": 2.5,
      "max_volume_ml": 500
    },
    ...
  },
  "material_change": {
    "drain_volume_ml": 50,
    "fill_volume_ml": 45,
    "mixing_time_seconds": 10,
    "settle_time_seconds": 5
  }
}
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u scion-mmu-print-manager.service -n 50

# Check dependencies
source ~/multi-material-printer/venv/bin/activate
python -c "import flask_socketio; print('OK')"
```

### Cannot Connect to Printer

```bash
# Test network
ping 192.168.4.3

# Check WiFi connection
iwconfig wlan0

# Verify static IP
ip addr show wlan0
```

### Print Manager Not Connecting

```bash
# Check web service
sudo systemctl status scion-mmu-web.service
curl http://localhost:5000/api/health

# Restart in correct order
sudo systemctl restart scion-mmu-web.service
sleep 5
sudo systemctl restart scion-mmu-print-manager.service
```

### Pumps Not Responding

```bash
# Check I2C
sudo i2cdetect -y 1

# Check GPIO permissions
groups | grep gpio

# Test motor controller
python -c "from adafruit_motorkit import MotorKit; print(MotorKit())"
```

## Architecture Overview

```
Browser → Web Interface → Print Manager → Hardware
         (Flask/SocketIO)   (Controller)   (Printer/Pumps)
         Port 5000          WebSocket      I2C/GPIO/WiFi
```

**Key Principles:**
- Web interface = UI only (no hardware access)
- Print manager = single hardware authority
- WebSocket = real-time communication
- Services = persistent, auto-restart

## File Locations

```
~/multi-material-printer/
├── config/
│   ├── network_settings.ini     # Network config
│   ├── pump_profiles.json       # Pump calibration
│   └── recipe.txt               # Current recipe
├── src/controller/
│   ├── print_manager.py         # Hardware controller
│   ├── printer_comms.py         # Printer communication
│   ├── mmu_control.py           # Pump control
│   └── websocket_ipc.py         # WebSocket IPC
└── web-app/
    ├── app.py                   # Flask web server
    ├── templates/               # HTML templates
    └── static/                  # CSS/JS assets
```

## Emergency Stop

**Web Interface:** Click red "Emergency Stop" button on any page

**Command Line:**
```bash
# Stop all services
sudo systemctl stop scion-mmu-print-manager.service
sudo systemctl stop scion-mmu-web.service

# Or kill processes
pkill -f print_manager.py
pkill -f "app.py"
```

## Maintenance

### Update System

```bash
cd ~/multi-material-printer
git pull
sudo systemctl restart scion-mmu-web.service
sudo systemctl restart scion-mmu-print-manager.service
```

### View Active Connections

```bash
# Network connections
sudo netstat -tulpn | grep :5000

# WebSocket clients
curl http://localhost:5000/api/health | jq
```

### Backup Configuration

```bash
tar -czf mmu-backup-$(date +%Y%m%d).tar.gz \
  ~/multi-material-printer/config/*.ini \
  ~/multi-material-printer/config/*.json \
  ~/multi-material-printer/config/*.txt
```

## Safety Notes

⚠️ **IMPORTANT:**
- Always test pumps individually before starting print
- Verify material levels before long prints
- Monitor first few material changes closely
- Keep vat drain accessible during operation
- Have emergency stop procedures ready

## Support Resources

- Installation Guide: `INSTALLATION.md`
- Fix Summary: `CRITICAL_FIXES_SUMMARY.md`
- Architecture: `PRD.md`, `CLAUDE.md`
- GitHub: https://github.com/ScionResearch/multi-material-printer

---

**Version:** 1.0 | **Updated:** October 3, 2025
