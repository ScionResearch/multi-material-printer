# Scion Multi-Material 3D Printer Controller - Development Roadmap

*Last Updated: August 2025*

This document outlines the current development status and remaining tasks for the multi-material printer controller. The project has undergone significant restructuring and many foundational tasks are now complete.

## Project Status Overview

✅ **Foundation Complete** - Project restructuring, configuration management, and core architecture are implemented  
✅ **GUI Enhancements Complete** - Advanced user interface with real-time monitoring and streamlined workflows  
🔧 **Active Development** - Network management, hardware control, and safety features  
📋 **Future Features** - Smart features, analytics, and remote monitoring  

---

## ✅ COMPLETED WORK (Phase 1 - Foundation)

### Code Structure & Organization
- ✅ **Directory Structure** - Clean `src/`, `config/`, `tools/`, `build/` organization
- ✅ **File Migration** - All source files moved to appropriate locations
- ✅ **Build System** - Updated Qt project files (`ScionMMUController.pro`)
- ✅ **Git Configuration** - `.gitignore` file created and configured
- ✅ **Python Module Structure** - Created `__init__.py` and proper package structure

### Configuration Management  
- ✅ **ConfigManager Class** - Dynamic configuration loading from INI files
- ✅ **Network Settings** - `network_settings.ini.template` for IP configuration
- ✅ **Pump Profiles** - `pump_profiles.json` for hardware settings
- ✅ **Path Resolution** - Eliminated all hardcoded paths

### Python Module Refactoring
- ✅ **printer_comms.py** - Clean interface for printer communication
- ✅ **mmu_control.py** - Multi-material unit control wrapper
- ✅ **print_manager.py** - Print orchestration module

### Bug Fixes
- ✅ **Script Path Issues** - Fixed hardcoded `/home/pidlp/pidlp/dev/scripts/` references
- ✅ **IP Address Configuration** - Removed hardcoded `192.168.4.2` references
- ✅ **Shell Script Errors** - Fixed typos in network management scripts

---

## ✅ COMPLETED WORK (Phase 2 - GUI Enhancements)

### GUI Workflow Improvements
- ✅ **Visual Recipe Editor** - Replace text input with table-based material change editor
  - ✅ Table widget with "Layer Number" and "Material" columns
  - ✅ Add/Remove row buttons for recipe management
  - ✅ Material dropdown selection (Pump A, B, C, D)
  - ✅ Automatic recipe file generation
  - ✅ Load/Save recipe functionality with file dialogs

- ✅ **Dynamic Printer Status Display** - Real-time status monitoring
  - ✅ Live status updates (Printing/Paused/Idle/Unknown) with color coding
  - ✅ Current file and progress display with progress bar
  - ✅ Next material change information
  - ✅ Connection status indicator with visual feedback
  - ✅ Auto-update toggle with 5-second intervals

- ✅ **Streamlined Print Management** - Single-button print workflow
  - ✅ "🚀 Start Multi-Material Print" button with enhanced styling
  - ✅ Comprehensive pre-print validation (recipe, connection, printer state)
  - ✅ Integrated file selection and recipe confirmation
  - ✅ Automatic recipe saving before print start
  - ✅ Detailed confirmation dialog with print summary

### System Reliability
- ✅ **Asynchronous Operations** - Prevent GUI freezing
  - ✅ Implemented ScriptWorker class running in separate QThread
  - ✅ Refactored all printer commands to use async operations
  - ✅ Non-blocking status checks with proper signal/slot connections
  - ✅ Process timeout handling (10-second timeouts)

- ✅ **Robust Error Handling** - Connection and hardware failure recovery
  - ✅ Consecutive failure tracking (connection lost after 3 failures)
  - ✅ Hardware error analysis (pump, motor, sensor failures)
  - ✅ User-friendly error dialogs with actionable guidance
  - ✅ Automatic operation stopping on hardware errors
  - ✅ Network connectivity validation and recovery suggestions

- ✅ **Memory Management** - Qt object lifecycle fixes
  - ✅ Proper QProcess cleanup with terminate/kill fallbacks
  - ✅ Thread-safe worker cleanup using deleteLater()
  - ✅ Custom table widget cleanup (QSpinBox/QComboBox)
  - ✅ Timer management and proper parent-child relationships
  - ✅ Memory leak prevention in process handling

---

## 🚨 CRITICAL PRIORITY - Installation & Infrastructure Fixes

**URGENT:** These issues must be resolved before the project can be successfully installed on a fresh Raspberry Pi system.

### Missing Dependencies & Installation Issues
- [ ] **Integrate the `anycubic-python` Dependency**
  - ⚠️ **Critical Issue:** Core communication scripts depend on the `uart_wifi` library from `anycubic-python` repository
  - Scripts like `newcommunication.py` import `from uart_wifi.errors import ConnectionException` but the dependency is missing
  - **Action:** Add to `requirements.txt`:
    ```
    # Anycubic printer communication library
    anycubic-python @ git+https://github.com/adamoutler/anycubic-python.git
    ```
  - **Sub-Task:** Verify and fix Python imports in `src/controller/newcommunication.py`
  - **Sub-Task:** Test imports may need to change from relative to absolute paths

- [ ] **Strengthen Installation Script (`tools/install_dependencies.sh`)**
  - **Problem:** Current script doesn't reliably install all Python packages from `requirements.txt`
  - **Action:** Replace Python installation section with robust command:
    ```bash
    echo "Installing all required Python packages..."
    pip3 install -r requirements.txt
    echo "Python dependencies installed successfully."
    ```
  - **Sub-Task:** Ensure `adafruit-circuitpython-motorkit` and `anycubic-python` install correctly

- [ ] **Document Required Hardware Configuration (I2C)**
  - **Critical:** Adafruit motor controllers require I2C interface (disabled by default on new Pi)
  - **Action:** Add mandatory setup step to README.md:
    ```markdown
    ### 1a. Enable Hardware Interfaces (First-Time Raspberry Pi Setup)
    
    **This step is critical for the pumps to function.**
    
    1. Run: `sudo raspi-config`
    2. Select `3 Interface Options`
    3. Select `I5 I2C`
    4. Select `<Yes>` to enable ARM I2C interface
    5. Reboot when prompted
    ```

### Legacy Code Management
- [ ] **Archive Legacy Python Scripts**
  - **Problem:** Old scripts in `src/controller/` cause confusion and import conflicts
  - **Action:** Move to `archive/controller_legacy/`:
    - `newmonox.py` (replaced by modular approach)
    - `pollphoton.py` (functionality integrated into GUI)
    - `guitest.py` (development artifact)
    - Consider archiving `newcommunication.py` if using `anycubic-python` directly

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

## 📊 Development Priorities

### CRITICAL (Immediate - Next 1-2 weeks)
1. 🚨 **Fix missing `anycubic-python` dependency** - Project currently cannot install on fresh Pi
2. 🚨 **Strengthen installation script** - Ensure reliable dependency installation  
3. 🚨 **Document I2C hardware setup** - Critical for pump functionality
4. 🚨 **Archive legacy scripts** - Remove import conflicts and confusion

### Recently Completed (Phase 2 - GUI Enhancements)
1. ✅ Visual Recipe Editor implementation
2. ✅ Dynamic Printer Status Display  
3. ✅ Asynchronous operation refactoring
4. ✅ Comprehensive error handling improvements
5. ✅ Memory management and Qt lifecycle fixes

### Short Term (After Critical Fixes - 1-2 months)
1. Network management integration
2. Pump calibration system
3. Pre-print validation enhancements
4. Safety feature implementation

### Long Term (6+ months)
1. Advanced material management
2. Print optimization algorithms
3. Remote monitoring capabilities
4. Analytics and reporting features

---

## 🎯 Success Metrics

- **Setup Time:** < 30 minutes for new users
- **Print Start Time:** < 5 minutes from GUI launch to print start  
- **Error Rate:** < 1% failed material changes
- **Build Time:** < 2 minutes on Raspberry Pi 4
- **Memory Usage:** < 100MB during operation

---

*This roadmap is regularly updated based on development progress and user feedback.*



