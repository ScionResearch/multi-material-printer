# Scion Research Multi-Material 3D Printer Controller

This project is a hardware and software solution designed to enable multi-material resin 3D printing on an Anycubic Photon Mono X 6k printer. It was developed as a collaborative project between [Scion](https://www.scionresearch.com/) and the [Massey AgriFood Digital Lab](https://www.massey.ac.nz/about-massey/our-structure/college-of-sciences/school-of-food-and-advanced-technology/agrifood-digital-lab/).

The system uses a single-board computer (like a Raspberry Pi) to act as an intermediary between the printer and a custom-built multi-material unit (MMU) consisting of stepper motor-driven pumps. It allows a user to define a print plan where different materials (resins) are automatically swapped at specific layer heights.

---

## Core Components

1.  **Control Unit:** A Raspberry Pi runs the control software, connects to the printer via Wi-Fi, and interfaces with the MMU hardware via GPIO pins.
2.  **Graphical User Interface (GUI):** A user-friendly desktop application built with C++/Qt. It serves as the central control panel for all printing and hardware operations.
3.  **Multi-Material Unit (MMU):** The physical hardware, composed of stepper motors and pumps, responsible for swapping the resins in the printer's vat.
4.  **Control Scripts:** A collection of Python scripts that handle the low-level logic, including:
    *   Communicating with the printer to get status, send commands (pause, resume, etc.).
    *   Controlling the MMU's stepper motors.
    *   Executing the automated multi-material print cycle.

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

2. **Run the installation script:**
   ```bash
   chmod +x tools/install_dependencies.sh
   sudo ./tools/install_dependencies.sh
   ```

3. **Configure your setup:**
   - Edit `config/network_settings.ini` for your network
   - Edit `config/pump_profiles.json` for your hardware setup

4. **Build and run:**
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

### Architecture Overview

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Qt GUI            │    │  Python Controller  │    │  Hardware           │
│  (ScionMMUController)│◄──►│   (print_manager)   │◄──►│  (Printer + MMU)    │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

The GUI application communicates with Python controller modules via subprocess calls and file-based messaging. The Python modules handle low-level hardware communication.

### Key Components

- **GUI (Qt/C++):** User interface, recipe editing, status display
- **Print Manager (Python):** Orchestrates printing process, monitors printer status
- **MMU Control (Python):** Pump control, material handling
- **Printer Comms (Python):** Network communication with 3D printer

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

- **Jean Henri Odendaal and Massey AgriFood Digital Lab (MAFDL)** - Initial work and design of the system and software
- **Scion Research** - Ongoing development

## 🙏 Acknowledgments
- Jean Henri Odendaal for the lead development of initial phases
- Karl Molving for the modifications and ongoing improvement 


