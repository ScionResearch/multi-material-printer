# Scion Research Multi-Material 3D Printer Controller

![Scion and Massey University Logos](./gui_mafdl/Picture1.png) ![Massey University Logo](./gui_mafdl/Picture2.png)

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

*   **Network Flexibility:** The control unit can operate in two modes:
    *   **Access Point (AP) Mode:** Creates its own Wi-Fi network, allowing direct connection to the printer without an existing network.
    *   **Wi-Fi Client Mode:** Connects to an existing Wi-Fi network.
*   **Full Printer Control:** The GUI provides standard printer controls, including listing files, starting a print, pausing, resuming, and stopping.
*   **Manual Hardware Control:** Manually operate individual MMU pumps to prime, purge, or test materials.
*   **Automated Multi-Material Printing:**
    *   Define a "recipe" of which material to use at specific layer numbers.
    *   Initiate a multi-material print process that automatically polls the printer's status.
    *   Pauses the print at the designated layer, runs the pumps to swap materials, and resumes printing seamlessly.
*   **Live Feedback:** A terminal-like output window in the GUI shows real-time status updates and command logs from the printer and control scripts.

---

## Project Structure

*   `/`: Contains shell scripts for managing network modes (`startAP.sh`, `stopAP.sh`).
*   `gui_mafdl/`: Source code for the main C++/Qt GUI application.
*   `build-untitled6-LinuxKit-Release/`: The default build output directory for the compiled GUI application.
*   `scripts/`: Contains all the core Python scripts for printer communication (`newmonox.py`, `pollphoton.py`) and hardware control (`photonmmu_pump.py`).
*   `gui/`: Contains experimental/alternative GUI files (GTK, Tkinter).

---

## Getting Started

### Prerequisites

*   A configured Raspberry Pi (or similar Linux SBC).
*   Python 3 and required libraries (`RPi.GPIO`, `adafruit-circuitpython-motorkit`).
*   Qt 5 development libraries.
*   The custom-built MMU hardware connected to the Raspberry Pi's GPIO pins.

### Build Instructions

1.  Navigate to the release build directory:
    ```bash
    cd build-untitled6-LinuxKit-Release/
    ```
2.  Run qmake to generate the Makefile from the project file:
    ```bash
    qmake ../gui_mafdl/untitled6.pro
    ```
3.  Compile the project:
    ```bash
    make
    ```
4.  The executable `untitled6` will be created in the current directory.

# Scion Multi-Material Unit Controller

A sophisticated control system for multi-material 3D printing, enabling automated material changes during print jobs. This system coordinates between a 3D printer and a multi-material unit (MMU) to seamlessly switch between different resins or materials at specified layer heights.

## 🎯 Vision: Simplified User Experience

**Before:** Users had to manually coordinate multiple interfaces, edit configuration files, and run shell scripts.

**After:** A single, intuitive GUI application that handles everything from network setup to print management.

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

## 📁 Project Structure

```
scionresearch-multi-material-printer/
├── README.md                    # This file
├── TODO.md                      # Development roadmap and known issues
├── .gitignore                   # Git ignore rules
│
├── build/                       # Compiled applications and build artifacts
│   └── ScionMMUController       # Main GUI executable (after build)
│
├── config/                      # Configuration files
│   ├── network_settings.ini.template  # Network configuration template
│   ├── network_settings.ini     # User network settings (created from template)
│   ├── pump_profiles.json       # Pump calibration and profiles
│   └── wpa_supplicant.conf      # WiFi configuration (legacy)
│
├── src/                         # Source code
│   ├── gui/                     # Qt C++ GUI application
│   │   ├── main.cpp             # Application entry point
│   │   ├── dialog.cpp/.h        # Main dialog window
│   │   ├── dialog.ui            # UI layout file
│   │   ├── ScionMMUController.pro # Qt project file
│   │   ├── assets.qrc           # Qt resource file
│   │   └── assets/              # Images and UI resources
│   │       ├── Picture1.png
│   │       └── Picture2.png
│   │
│   └── controller/              # Python control modules
│       ├── __init__.py          # Python package initialization
│       ├── print_manager.py     # Main print orchestration (was pollphoton.py)
│       ├── mmu_control.py       # Pump control logic (was photonmmu_pump.py)
│       ├── printer_comms.py     # Printer communication (was newmonox.py)
│       └── guitest.py           # Legacy GUI testing utilities
│
└── tools/                       # Utilities and setup scripts
    ├── install_dependencies.sh  # System setup script
    ├── startAP.sh               # Enable WiFi access point mode
    └── stopAP.sh                # Disable access point, return to client mode
```

## 🎮 User Workflow (Simplified)

### The Old Way (Complex)
1. SSH into Raspberry Pi
2. Run shell scripts to configure network
3. Edit configuration files manually
4. Start GUI application
5. Type cryptic recipe strings
6. Start print job on printer physically
7. Navigate file dialogs to select scripts
8. Hope everything works together

### The New Way (Simple)
1. **Launch Application:** Open ScionMMUController
2. **Connect:** Application auto-discovers printer on network
3. **Select Print File:** Choose from files available on printer
4. **Define Recipe:** Use visual table to set material changes by layer
5. **Start Print:** Single button starts everything automatically
6. **Monitor:** Real-time progress updates and status

## 🛠️ Configuration

### Network Setup
Edit `config/network_settings.ini`:

```ini
[wifi]
ssid = "YourWiFiNetwork"
password = "YourPassword"
enabled = true

[access_point]
ssid = "ScionMMU"
password = "scionmmu123"
enabled = false

[printer]
ip_address = ""  # Leave empty for auto-discovery
port = 80
timeout = 10
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

### Immediate Goals (v1.1)
- [ ] Integrated network manager in GUI
- [ ] Visual recipe editor (table-based)
- [ ] Auto-discovery of printers
- [ ] Real-time status display

### Future Goals (v2.0)
- [ ] Multi-printer support
- [ ] Web-based remote interface
- [ ] Advanced material profiles
- [ ] Predictive maintenance alerts

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow Qt coding standards for C++ code
- Use PEP 8 for Python code
- Update documentation for new features
- Add tests for critical functionality

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Authors

- **Scion Research** - Initial work and ongoing development

## 🙏 Acknowledgments

- Anycubic community for printer communication protocols
- Qt community for excellent GUI framework
- Raspberry Pi Foundation for affordable computing platform

