# Scion Research Multi-Material 3D Printer Controller

This project is a hardware and software solution designed to enable multi-material resin 3D printing on an Anycubic Photon Mono X 6k printer. It was developed as a collaborative project between [Scion](https://www.scionresearch.com/) and the [Massey AgriFood Digital Lab](https://www.massey.ac.nz/about-massey/our-structure/college-of-sciences/school-of-food-and-advanced-technology/agrifood-digital-lab/).

The system uses a single-board computer (like a Raspberry Pi) to act as an intermediary between the printer and a custom-built multi-material unit (MMU) consisting of stepper motor-driven pumps. It allows a user to define a print plan where different materials (resins) are automatically swapped at specific layer heights.

---

## Core Components

> NOTE: The legacy Qt/C++ desktop GUI is now deprecated. The project has transitioned to a web-first architecture using Flask + Socket.IO. The Qt code remains temporarily for reference and will be removed in a future cleanup release.

1. **Control Unit:** Raspberry Pi (or similar SBC) running the Flask web server and the persistent `print_manager` service.
2. **Web UI (`web-app/`):** Browser-based interface (Flask + Socket.IO + Bootstrap) for recipes, monitoring, diagnostics, manual pump & printer control.
3. **Print Manager Service:** Long-running Python process (`src/controller/print_manager.py`) – single authority for hardware and printer orchestration; receives commands exclusively via WebSocket events.
4. **MMU Hardware:** Stepper-driven pumps (drain + material channels) for automated resin exchange sequences.
5. **Controller Modules:** Python modules for printer communication (`printer_comms.py`), pump/MMU control (`mmu_control.py`), IPC (`websocket_ipc.py`).
6. **Diagnostics & Calibration:** Web-exposed commands for GPIO/I2C tests and pump calibration flows.

---

## Capabilities

### System Features
- **Network Management:** Switch between Access Point mode (creates own WiFi) and client mode (connects to existing WiFi)
- **File Management:** List and select printable files stored on the printer's internal memory
- **Standard Print Operations:** Start, pause, resume, and stop prints directly from the interface
- **Multi-Material Recipe System:** Define sequences of material changes based on specific layer numbers
- **Automated Print Execution:** The system automatically executes multi-material recipes by:
  1. Continuously polling the printer for its current layer number
  2. Pausing the print job when a target layer is reached
  3. Activating the correct pumps to perform the material swap
  4. Resuming the print job automatically
- **Manual Pump Control:** Run any pump forwards or backwards for specified durations (maintenance and setup)
- **Live Operation Logging:** Real-time feedback on commands sent, printer status, and script actions
- **Configuration Management:** External configuration files for network settings and pump profiles

---

## 🚀 Quick Start

### Prerequisites
- Raspberry Pi 4 or similar Linux computer
- Multi-material unit hardware with controllable pumps
- Compatible resin 3D printer (tested with Anycubic Photon series)
- Network connectivity (WiFi or Ethernet)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ScionResearch/multi-material-printer.git
   cd multi-material-printer
   ```

2. **Enable Hardware Interfaces (First-Time Raspberry Pi Setup):**
   ```bash
   sudo raspi-config
   ```
   - Go to: `3 Interface Options` → `I5 I2C`
   - Select `<Yes>` to enable the I2C interface
   - Reboot when prompted: `sudo reboot`
   
   **⚠️ Critical:** The Adafruit motor controllers will fail if the I2C interface is not enabled.

3. **Run the installation script:**
   ```bash
   chmod +x tools/install_dependencies.sh
   sudo ./tools/install_dependencies.sh
   ```

4. **Configure your setup:**
   - Edit `config/network_settings.ini` for your network
   - Edit `config/pump_profiles.json` for your hardware setup

5. **Build and run:**
   ```bash
   cd src/gui
   qmake ScionMMUController.pro
   make
   ../../build/ScionMMUController
   ```

## 📖 Usage Guide

### Network Setup Options

**Current Setup (ESP32 Gateway + Access Point Mode)**
*Note: This configuration is specific to the current hardware setup*

Network topology:
- **192.168.4.1** - ESP32 WiFi gateway/router 
- **192.168.4.2** - Raspberry Pi (control unit)
- **192.168.4.3** - 3D Printer (communication endpoint)

1. The ESP32 creates the WiFi network and acts as gateway
2. Configure printer IP in your setup:
   ```bash
   cp config/network_settings.ini.template config/network_settings.ini
   nano config/network_settings.ini
   ```
   Update the `[printer]` section:
   ```ini
   [printer]
   ip_address = "192.168.4.3"
   port = 6000
   ```

**Alternative: Standard WiFi Client Mode**  
1. Switch to client mode: `sudo ./tools/stopAP.sh`
2. Both Pi and printer connect to existing WiFi (requires IP discovery)

### Using the GUI

1. **Launch the Application:**
   ```bash
   ./build/ScionMMUController
   ```

2. **Check Connection:**
   - Click **"Check Status"** button
   - Status should show "Connected..." if printer is reachable

3. **Setup Multi-Material Print:**
   - Define material recipe in format: `MATERIAL,LAYER:MATERIAL,LAYER`
   - Example: `A,50:B,120:C,200` (switch to A at layer 50, B at 120, C at 200)
   - Click **"Set"** to save recipe

4. **Start Multi-Material Print:**
   - Start print job on printer (or use "Get Files" to select from GUI)
   - Click **"Begin MM"** to start automated material swapping
   - System monitors layers and performs swaps automatically

### Manual Controls

- **Motor Control:** Test pumps with format `PUMP,DIRECTION,TIME` (e.g., `A,F,30`)
  - `PUMP`: A, B, C, or D
  - `DIRECTION`: F (Forward) or R (Reverse)  
  - `TIME`: Duration in seconds
- **Printer Controls:** Direct pause/resume/stop commands to printer
- **Stop MM:** Halt automated material swapping (printer continues)

## 📁 Project Structure

```
multi-material-printer/
├── README.md                    # This file
├── TODO.md                      # Development roadmap and tasks
├── .gitignore                   # Git ignore rules
├── requirements.txt             # Python dependencies
│
├── archive/                     # Archived legacy files
├── build/                       # Compiled applications and build artifacts
│   └── ScionMMUController       # Main GUI executable (after build)
│
├── config/                      # Configuration files
│   ├── network_settings.ini.template  # Network configuration template
│   ├── network_settings.ini     # User network settings (create from template)
│   ├── pump_profiles.json       # Pump calibration and profiles
│   └── wpa_supplicant.conf      # WiFi configuration (legacy)
│
├── src/                         # Source code
│   ├── gui/                     # Qt C++ GUI application
│   │   ├── main.cpp             # Application entry point
│   │   ├── dialog.cpp/.h        # Main dialog window
│   │   ├── configmanager.cpp/.h # Configuration management
│   │   ├── dialog.ui            # UI layout file
│   │   ├── ScionMMUController.pro # Qt project file
│   │   ├── assets.qrc           # Qt resource file
│   │   └── assets/              # Images and UI resources
│   │
│   └── controller/              # Python control modules
│       ├── __init__.py          # Python package initialization
│       ├── print_manager.py     # Print orchestration wrapper
│       ├── mmu_control.py       # Pump control wrapper
│       ├── printer_comms.py     # Printer communication wrapper
│       ├── pollphoton.py        # Original polling script
│       ├── newmonox.py          # Original printer communication
│       └── photonmmu_pump.py    # Original pump control
│
└── tools/                       # Utilities and setup scripts
    ├── install_dependencies.sh  # System setup script
    ├── startAP.sh               # Enable WiFi access point mode
    └── stopAP.sh                # Switch to WiFi client mode
```
## 🛠️ Configuration

### Network Configuration

**For Current ESP32 Setup:**
Create and edit `config/network_settings.ini`:
```bash
cp config/network_settings.ini.template config/network_settings.ini
```

Key settings for current hardware:
```ini
[printer]
ip_address = "192.168.4.3"  # Printer endpoint  
port = 6000                 # Anycubic communication port
timeout = 10
```

**For Standard WiFi Networks:**
```ini
[wifi]
ssid = "YourWiFiNetwork"
password = "YourPassword"
enabled = true

[printer]
ip_address = ""  # Auto-discovery
port = 6000
```

### Pump Configuration
Edit `config/pump_profiles.json`:

```json
{
  "pumps": {
    "pump_a": {
      "name": "Pump A",
      "gpio_pin": 18,
      "flow_rate_ml_per_second": 2.5,
      "calibration": {
        "steps_per_ml": 100
      }
    }
  },
  "material_change": {
    "drain_volume_ml": 50,
    "fill_volume_ml": 45,
    "mixing_time_seconds": 10
  }
}
```

## 🔧 Development

### Building from Source

**Prerequisites:**
- Qt5 development libraries
- Python 3.7+
- CMake or qmake

**Build Steps:**
```bash
cd src/gui
qmake ScionMMUController.pro
make
```

### Architecture Overview (Current)

```
Browser Client(s)  ── WebSocket + REST ──▶  Flask Web App (app.py)
       ▲                                        │
       │  status_update / command_result        │ emits 'command'
       │                                        ▼
    User UI ◀───────── WebSocket ─────────  Print Manager Service (persistent)
                                                   │
                                                   ▼
                                       Printer (WiFi) + MMU Pumps (GPIO/I2C)
```

Key design principles:
* Single authoritative hardware process (no per-request subprocess spawning).
* All REST endpoints delegate via WebSocket command emission only—no direct hardware calls.
* File-based shared status JSON has been removed (replaced by real-time Socket.IO events).
* 10s quiescent window after a pause prevents race conditions while the printer raises the build plate.

### Legacy Architecture (Deprecated)
Older releases used a Qt GUI spawning the print manager and polling JSON files for status. This model is retired due to fragility and race conditions.

## 🧪 Testing

### Hardware Requirements for Testing
- Raspberry Pi with GPIO access
- Test pumps or pump simulators
- Network-accessible 3D printer
- Test materials or water for pump testing

### Testing Modes
1. **Simulation Mode:** Test without hardware
2. **Pump Test Mode:** Test pumps without printer
3. **Communication Test:** Test printer communication without pumps
4. **Integration Test:** Full system test

## 🐛 Troubleshooting

### Common Issues

**"Printer Not Found"**
- Check network connectivity
- Verify printer IP in config
- Ensure printer is powered on and connected

**"Pump Not Responding"**
- Check GPIO connections
- Verify pump profiles configuration
- Test individual pumps in calibration mode

**"Build Errors"**
- Install Qt5 development packages
- Check compiler version (C++11 support required)
- Verify all dependencies are installed

### Debug Mode
Run with debug output:
```bash
./build/ScionMMUController --debug
```

## 📈 Roadmap

See `TODO.md` for detailed development plans and known issues.


### Development Guidelines
- Follow Qt coding standards for C++ code
- Use PEP 8 for Python code
- Update documentation for new features
- Add tests for critical functionality

## 👥 Authors

- **Massey AgriFood Digital Lab (MAFDL)** - Initial work and design of the system and software
- **Scion Research** - Ongoing development

## 🙏 Acknowledgments
- Jean Henri Odendaal for the lead development of initial phases
- Karl Molving for the modifications and ongoing improvement 


