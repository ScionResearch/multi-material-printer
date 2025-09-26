# Scion Multi-Material 3D Printer Controller - Development Roadmap

*Last Updated: August 2025*

This document outlines the current development status and remaining tasks for the multi-material printer controller. The project has undergone significant restructuring and many foundational tasks are now complete.

## Project Status Overview

✅ **Foundation Complete** - Project restructuring, configuration management, and core architecture are implemented.
✅ **GUI Enhancements Complete** - Advanced user interface with real-time monitoring and streamlined workflows.
✅ **Installation & Dependencies Complete** - uart-wifi integration, modern library architecture, and legacy code cleanup.
🔧 **Active Development** - Network management, hardware control, and safety features.
📋 **Future Features** - Advanced analytics, remote monitoring, and smart optimization features.

---

## ✅ COMPLETED WORK (Phases 1, 2 & 3)

### Code Structure, Configuration & GUI Workflow
- ✅ **Clean Architecture:** Well-defined `src/`, `config/`, `tools/`, and `build/` directories.
- ✅ **Externalized Configuration:** All hardcoded paths and settings (IP addresses, pump profiles) have been moved to `.ini` and `.json` files.
- ✅ **Modular Python Code:** Core logic refactored into `printer_comms.py`, `mmu_control.py`, and `print_manager.py`.
- ✅ **Visual Recipe Editor:** A table-based UI allows for intuitive creation and management of material change recipes, eliminating manual entry errors.
- ✅ **Dynamic Status Display:** The GUI provides real-time, color-coded feedback on printer status, progress, and upcoming material changes.
- ✅ **Asynchronous Operations:** A `QThread`-based worker (`ScriptWorker`) ensures the GUI remains responsive by running all communication and hardware tasks in the background.
- ✅ **Robust Error Handling:** The system can detect and gracefully handle connection failures and hardware errors, providing clear feedback to the user.

### Installation & Architecture (Phase 3 - COMPLETE)
- ✅ **uart-wifi Dependency Integrated:** Added `uart-wifi>=0.2.1` to `requirements.txt` for reliable PyPI installation.
- ✅ **printer_comms.py Modernized:** Fully refactored to use uart-wifi library with structured responses, proper error handling, and connection management.
- ✅ **Legacy Scripts Archived:** Moved obsolete scripts (`newmonox.py`, `newcommunication.py`, `guitest.py`, `pollphoton.py`) to `src/controller/archive/` folder.
- ✅ **Clean Library Architecture:** Application now imports uart-wifi library instead of running external scripts via subprocess.
- ✅ **Installation Script Updated:** `tools/install_dependencies.sh` simplified to use standardized `requirements.txt`.

- [ ] **Document Required Hardware Configuration (I2C)**
    -   **Remaining:** Add I2C setup instructions to `README.md` installation guide.
    -   **Action:** Document the mandatory Raspberry Pi I2C interface setup for Adafruit motor controllers.

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

---
Future Enhancements (not yet implemented):
1. Introduce a simple line-based JSON protocol: each status message = one JSON object.
2. Heartbeat ping every N seconds to detect stalled processes.
3. Graceful cancellation signal via temp file or dedicated command channel.
Future Enhancement (not yet implemented): Add a `--validate-recipe` flag to `print_manager.py` to perform these checks before starting.

 - Current status polling likely parses stdout lines (e.g., JSON or key=value—formalize format in future)
 - Error handling: non-zero Python exit codes should surface a modal dialog (planned improvement if not implemented)
 - Suggested log routing (future): Write structured logs to `logs/print_manager_<timestamp>.log` while still streaming to stdout for GUI consumption.
 Planned Enhancement: Introduce a "mock printer" mode in `print_manager.py` to emulate layer advancement for local dry-runs (not yet implemented).