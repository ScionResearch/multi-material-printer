# Scion Multi-Material 3D Printer Controller - Development Roadmap

*Last Updated: August 2025*

This document outlines the current development status and remaining tasks for the multi-material printer controller. The project has undergone significant restructuring and many foundational tasks are now complete.

## Project Status Overview

✅ **Foundation Complete** - Project restructuring, configuration management, and core architecture are implemented.
✅ **GUI Enhancements Complete** - Advanced user interface with real-time monitoring and streamlined workflows.
🔧 **Active Development** - Critical installation and dependency fixes.
📋 **Future Features** - Network management, hardware control, and safety features.

---

## ✅ COMPLETED WORK (Phases 1 & 2)


### Code Structure, Configuration & GUI Workflow
- ✅ **Clean Architecture:** Well-defined `src/`, `config/`, `tools/`, and `build/` directories.
- ✅ **Externalized Configuration:** All hardcoded paths and settings (IP addresses, pump profiles) have been moved to `.ini` and `.json` files.
- ✅ **Modular Python Code:** Core logic refactored into `printer_comms.py`, `mmu_control.py`, and `print_manager.py`.
- ✅ **Visual Recipe Editor:** A table-based UI allows for intuitive creation and management of material change recipes, eliminating manual entry errors.
- ✅ **Dynamic Status Display:** The GUI provides real-time, color-coded feedback on printer status, progress, and upcoming material changes.
- ✅ **Asynchronous Operations:** A `QThread`-based worker (`ScriptWorker`) ensures the GUI remains responsive by running all communication and hardware tasks in the background.
- ✅ **Robust Error Handling:** The system can detect and gracefully handle connection failures and hardware errors, providing clear feedback to the user.

---

## 🚨 CRITICAL PRIORITY - Installation & Architecture Fixes

**URGENT:** These issues must be resolved before the project can be successfully installed and run on a fresh Raspberry Pi system.

### Missing Dependencies & Installation Issues
- [ ] **1. Integrate the `uart-wifi` Dependency**
    -   ⚠️ **Critical Issue:** The project relies on the `uart-wifi` library for printer communication, but it is not included in the dependencies.
    -   **Action (Refined):** Add the official `uart-wifi` package from PyPI to `requirements.txt`. This is the standard and most reliable method.
        ```
        # In requirements.txt
        uart-wifi>=0.2.1
        ```
    -   **Architectural Goal:** This change solidifies the architecture. Your application will **import** this library, not contain copies of its scripts.

- [ ] **2. Refactor `printer_comms.py` to Use the `uart-wifi` Library**
    -   ⚠️ **Critical Issue:** The current C++ code may still be calling legacy scripts via `subprocess`.
    -   **Action:** Ensure all printer communication is handled by importing and using the `uart-wifi` library classes within your Python modules. This is a fundamental architectural shift from running scripts to using a library.
        ```python
        # Example of the new approach in your printer_comms.py
        from uart_wifi.communication import UartWifi
        from uart_wifi.errors import ConnectionException

        def get_status(printer_ip, port=6000):
            try:
                uart = UartWifi(printer_ip, port)
                responses = uart.send_request("getstatus")
                # ... process and return the response object ...
            except ConnectionException as e:
                # ... handle the error ...
        ```

- [ ] **3. Strengthen Installation Script (`tools/install_dependencies.sh`)**
    -   **Problem:** The script must reliably install all Python dependencies.
    -   **Action:** Simplify the script to use the updated `requirements.txt`.
        ```bash
        # (in install_dependencies.sh)
        echo "Installing all required Python packages..."
        pip3 install --upgrade pip
        pip3 install -r requirements.txt
        echo "Python dependencies installed successfully."
        ```

- [ ] **4. Document Required Hardware Configuration (I2C)**
    -   **Critical:** The Adafruit motor controllers will fail if the I2C interface is not enabled.
    -   **Action:** Add a mandatory setup step to the `README.md` installation guide.
        ```markdown
        ### 1a. Enable Hardware Interfaces (First-Time Raspberry Pi Setup)
        1. Run: `sudo raspi-config`
        2. Go to: `3 Interface Options` -> `I5 I2C`.
        3. Select `<Yes>` to enable the I2C interface and reboot.
        ```

### Legacy Code Management
- [ ] **Archive Redundant Scripts**
    -   **Problem:** Old scripts in `src/controller/` are now obsolete and create confusion.
    -   **Action:** Once `printer_comms.py` is fully refactored to use the `uart-wifi` library, move the following scripts to the `archive/` folder to finalize the clean architecture:
        -   `newmonox.py`
        -   `newcommunication.py`
        -   `guitest.py`
        -   `pollphoton.py` (if its logic is fully absorbed by `print_manager.py` and the GUI).

---

## 🔧 HIGH PRIORITY - Next Development Focus

### Network & Discovery
- [ ] **Integrated Network Manager** - GUI-based WiFi management
  - Replace shell script dependencies
  - Auto-scan and connect to networks
  - AP mode toggle from GUI

- [ ] **Auto-Discovery System** - Automatic printer detection
  - Network scanning for printer devices
  - Display printer information when connected
  - Graceful handling of connection failures

### Hardware Control
- [ ] **Pump Calibration System** - GUI-based pump testing
  - Individual pump control buttons
  - Forward/Reverse/Prime operations
  - Flow rate measurement and adjustment
  - Calibration history tracking

- [ ] **Pre-Print Validation** - System checks before printing
  - Printer connectivity verification
  - Material recipe validation  
  - Sufficient material level checks
  - Pump functionality tests

### Safety & Monitoring
- [ ] **Safety Features** - Emergency controls and limits
  - Emergency stop functionality
  - Maximum pump runtime limits
  - Temperature monitoring integration
  - Material level sensor integration

---

## 🚀 LOW PRIORITY - Advanced Features

### Smart Features
- [ ] **Material Management** - Advanced material handling
  - Material library with properties
  - Automatic mixing calculations
  - Usage tracking and optimization

- [ ] **Print Optimization** - Intelligent processing
  - Optimal layer change timing
  - Waste reduction algorithms
  - Quality prediction

### Analytics & Remote Access
- [ ] **Data Logging** - Comprehensive session tracking
  - Print session logs with material usage
  - System performance metrics
  - Maintenance recommendations

- [ ] **Remote Monitoring** - External access capabilities
  - Web interface for status checking
  - Notification systems
  - Mobile integration considerations

