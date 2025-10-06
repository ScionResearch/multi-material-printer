# Scion Multi-Material 3D Printer Controller

**Automated resin material changing system for Anycubic Photon Mono X 6K**

A collaborative project between [Scion Research](https://www.scionresearch.com/) and the [Massey AgriFood Digital Lab](https://www.massey.ac.nz/about-massey/our-structure/college-of-sciences/school-of-food-and-advanced-technology/agrifood-digital-lab/).

This system enables automated multi-material resin 3D printing by coordinating an Anycubic printer with custom stepper-driven pump hardware via a Raspberry Pi controller. Define a recipe of material changes by layer number, and the system handles the rest—pausing the print, swapping materials, and resuming automatically.

---

## 🎯 Key Features

- ✅ **Automated Material Changes** - Define layer-based recipes for seamless material swapping
- ✅ **Web-Based Interface** - Browser-accessible dashboard, recipe builder, and manual controls
- ✅ **Real-Time Monitoring** - Live printer status, layer progress, and pump operations
- ✅ **Air-Assist Drainage** - GPIO-controlled solenoid valve for efficient resin drainage
- ✅ **Manual Control Mode** - Test pumps, control printer, configure system settings
- ✅ **Production Ready** - Persistent services, automatic restarts, comprehensive logging

---

## 🚀 Quick Start

### Prerequisites

- Raspberry Pi 4 (4GB RAM recommended)
- Anycubic Photon Mono X or compatible resin printer
- Multi-material unit (MMU) with stepper-driven pumps
- I2C motor controllers (Adafruit MotorKit)
- Air solenoid valve for drain assist (optional)

### Installation

```bash
# Clone repository
git clone https://github.com/ScionResearch/multi-material-printer.git
cd multi-material-printer

# Install dependencies
pip3 install -r requirements.txt

# Enable I2C interface (first time only)
sudo raspi-config
# Navigate to: Interface Options → I2C → Enable → Reboot

# Configure system
cp config/network_settings.ini.template config/network_settings.ini
nano config/network_settings.ini  # Set printer IP address

# Start services
chmod +x start_services.sh stop_services.sh
./start_services.sh
```

**Access web interface:** `http://<raspberry-pi-ip>:5000`

### Running a Multi-Material Print

1. **Create Recipe** (Recipe Builder page):
   ```
   A,50:B,120:C,200
   ```
   *(Switch to material A at layer 50, B at layer 120, C at layer 200)*

2. **Start Print** on printer touchscreen or via web UI

3. **Activate Multi-Material Mode** (Dashboard):
   - Click **"Begin MM"** button
   - System monitors layers and executes material changes automatically

4. **Monitor Progress**:
   - Real-time status updates on dashboard
   - Material change sequence logged in detail

---

## 📖 Documentation

Comprehensive documentation is available in the `docs/` folder:

- **[Operating Manual](docs/OPERATING_MANUAL.md)** - User guide for operators and technicians
  - Safety procedures and emergency protocols
  - Daily operations and multi-material printing
  - Troubleshooting and maintenance schedules

- **[Programming Manual](docs/PROGRAMMING_MANUAL.md)** - Technical documentation for developers
  - System architecture and design principles
  - API reference and WebSocket protocol
  - Development workflow and extension guides

---

## 🏗️ System Architecture

```
┌─────────── Browser Client ──────────────┐
│  Dashboard │ Recipe Builder │ Manual   │
└──────────────┬──────────────────────────┘
               │ HTTP REST + WebSocket
               ▼
┌─────────── Flask Web App ───────────────┐
│  • HTTP API endpoints                   │
│  • WebSocket server (Socket.IO)         │
│  • Command router                       │
└──────────────┬──────────────────────────┘
               │ WebSocket IPC
               ▼
┌─────────── Print Manager ───────────────┐
│  • Printer status monitoring (4s poll)  │
│  • Recipe execution                     │
│  • Material change orchestration        │
└──────────────┬──────────────────────────┘
               │ Python modules
               ▼
┌─────────── Hardware Modules ────────────┐
│  printer_comms │ mmu_control            │
│  photonmmu_pump │ solenoid_control      │
└──────────────┬──────────────────────────┘
               │ WiFi / I2C / GPIO
               ▼
┌─────────── Physical Hardware ───────────┐
│  • Anycubic Printer (WiFi)              │
│  • Stepper Pumps A/B/C/D (I2C)         │
│  • Air Solenoid Valve (GPIO 22)         │
└──────────────────────────────────────────┘
```

**Design Principles:**
- Single hardware authority (only print manager touches hardware)
- Event-driven WebSocket communication
- Persistent background services
- Real-time status updates
- Configurable quiescent windows for safe operation

---

## 📁 Project Structure

```
multi-material-printer/
├── web-app/                    # Flask web application
│   ├── app.py                  # Main server, HTTP API, WebSocket
│   ├── static/                 # JavaScript, CSS
│   └── templates/              # HTML pages
│
├── src/controller/             # Hardware control modules
│   ├── print_manager.py        # Main orchestration service
│   ├── printer_comms.py        # Printer WiFi communication
│   ├── mmu_control.py          # Material change sequences
│   ├── photonmmu_pump.py       # Stepper pump control (I2C)
│   ├── solenoid_control.py     # Air valve control (GPIO)
│   └── websocket_ipc.py        # WebSocket client library
│
├── config/                     # Configuration files
│   ├── network_settings.ini    # Printer IP, port, timeouts
│   ├── pump_profiles.json      # Pump parameters, timing
│   └── recipe.txt              # Current material change recipe
│
├── docs/                       # Documentation
│   ├── OPERATING_MANUAL.md     # User guide
│   └── PROGRAMMING_MANUAL.md   # Developer guide
│
├── start_services.sh           # Start both services
├── stop_services.sh            # Stop both services
├── web_app.log                 # Web app logs
└── print_manager.log           # Print manager logs
```

---

## ⚙️ Configuration

### Network Settings (`config/network_settings.ini`)

```ini
[printer]
ip_address = 192.168.4.2
port = 6000
timeout_seconds = 5
polling_interval_seconds = 4
```

### Pump Configuration (`config/pump_profiles.json`)

```json
{
  "pumps": {
    "pump_a": {
      "name": "Pump A",
      "flow_rate_ml_per_second": 5.0,
      "max_volume_ml": 200
    }
  },
  "material_change": {
    "quiescence_seconds": 10,
    "bed_raise_time_seconds": 15,
    "drain_volume_ml": 50,
    "fill_volume_ml": 45,
    "settle_time_seconds": 5
  },
  "solenoid": {
    "enabled": true,
    "gpio_pin": 22,
    "activate_before_drain_delay_seconds": 0.5,
    "deactivate_after_drain_delay_seconds": 1.0
  }
}
```

---

## 🔧 Service Management

### Start Services

```bash
./start_services.sh
```

Starts both web app and print manager in background with logging.

### Stop Services

```bash
./stop_services.sh
```

Gracefully stops both services.

### Check Status

```bash
pgrep -f "app.py"                    # Web app PID
pgrep -f "print_manager.py"          # Print manager PID
tail -f web_app.log print_manager.log  # Monitor logs
```

### Deploy Updates

```bash
# Pull latest code and restart services
ssh pidlp@<raspberry-pi-ip> "cd /home/pidlp/pidlp/multi-material-printer && \
  git stash && \
  git pull origin main && \
  ./stop_services.sh && \
  ./start_services.sh"
```

---

## 🧪 Hardware Testing

### Test Printer Connection

```bash
cd src/controller
python3 -c "import printer_comms; print(printer_comms.get_status('192.168.4.2'))"
```

### Test Individual Pump

```bash
cd src/controller
python3 mmu_control.py A F 5  # Pump A, Forward, 5 seconds
```

### Test Air Solenoid Valve

```bash
cd src/controller
python3 solenoid_control.py 3  # 3-second test cycle
```

### Check I2C Motor Controllers

```bash
i2cdetect -y 1
# Should show devices at 0x60 and 0x61
```

---

## 🐛 Troubleshooting

### Dashboard Shows "Backend: Offline"

**Solution:**
```bash
# Restart services
./stop_services.sh
./start_services.sh

# Check logs
tail -f web_app.log print_manager.log
```

### Printer Not Connecting

**Check:**
- Printer is powered on
- Printer IP correct in `config/network_settings.ini`
- Raspberry Pi can reach printer network: `ping 192.168.4.2`

### Pumps Not Running

**Check:**
- I2C enabled: `sudo raspi-config` → Interface Options → I2C
- Motor controllers detected: `i2cdetect -y 1`
- Power supply connected to motor controllers

### Material Change Not Triggering

**Check:**
- Multi-Material Mode activated (Dashboard shows "Active")
- Recipe saved correctly (Recipe page)
- Current layer detected (Dashboard shows layer number)
- Check logs: `grep "MATERIAL" print_manager.log`

**For detailed troubleshooting, see [Operating Manual](docs/OPERATING_MANUAL.md#troubleshooting)**

---

## 🔌 API Reference

### REST Endpoints

**Printer Control:**
```bash
POST /api/printer/pause
POST /api/printer/resume
POST /api/printer/stop
```

**Pump Control:**
```bash
POST /api/pump
{
  "motor": "A",       # A, B, C, or D
  "direction": "F",   # F = forward, R = reverse
  "duration": 10      # seconds
}
```

**Solenoid Control:**
```bash
POST /api/solenoid/activate
POST /api/solenoid/deactivate
POST /api/solenoid/test
{
  "duration": 2  # seconds (for test action)
}
```

**Multi-Material:**
```bash
POST /api/multi-material/start
POST /api/multi-material/stop
GET  /api/recipe
POST /api/recipe
```

### WebSocket Events

**Server → Client:**
- `status_update` - Real-time printer status, material changes, pump operations

**Client → Server:**
- Handled automatically by UI, see [Programming Manual](docs/PROGRAMMING_MANUAL.md#websocket-protocol) for details

---

## 🛡️ Safety

**⚠️ Important Safety Information:**

- UV resin is a skin and eye irritant - always wear nitrile gloves and safety glasses
- Work in well-ventilated area
- Keep liquids away from electronics
- Do not reach into printer during operation
- Emergency stop button available in Manual Controls page

**For complete safety procedures, see [Operating Manual](docs/OPERATING_MANUAL.md#safety-information)**

---

## 👥 Contributors

**Development:**
- **Massey AgriFood Digital Lab (MAFDL)** - Initial system design and development
- **Scion Research** - Ongoing development and improvements

**Acknowledgments:**
- Jean Henri Odendaal - Lead development of initial phases
- Karl Molving - Modifications and ongoing improvements

---

## 📄 License

This project is proprietary to Scion Research and Massey University.

---

## 🔗 Links

- **Documentation:**
  - [Operating Manual](docs/OPERATING_MANUAL.md)
  - [Programming Manual](docs/PROGRAMMING_MANUAL.md)
- **Repositories:**
  - [GitHub Repository](https://github.com/ScionResearch/multi-material-printer)
- **Organizations:**
  - [Scion Research](https://www.scionresearch.com/)
  - [Massey AgriFood Digital Lab](https://www.massey.ac.nz/about-massey/our-structure/college-of-sciences/school-of-food-and-advanced-technology/agrifood-digital-lab/)

---

**Questions or Issues?**

For technical support, refer to the troubleshooting sections in the documentation or contact the development team.
