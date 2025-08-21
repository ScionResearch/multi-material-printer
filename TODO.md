# Scion Multi-Material 3D Printer Controller - Project Roadmap

This document outlines the development plan to refactor the project from its current prototype state into a robust, user-friendly, and maintainable application. The plan is broken down into phases, starting with foundational cleanup and moving towards user-facing features.

## Project Goals

1.  **Simplify the User Workflow:** The user should be able to control the entire multi-material printing process from the GUI without using the command line or manually starting prints on the printer.
2.  **Improve Reliability:** Reduce errors by replacing manual text inputs with guided, visual UI elements.
3.  **Clean Up the Codebase:** Reorganize the project into a logical and standard file structure to make it easier to understand, maintain, and extend.
4.  **Enhance Functionality:** Add features for calibration, better status monitoring, and easier setup.

---

## Phase 1: Code Cleanup and Reorganization (Foundation)

*Goal: Establish a clean, logical file structure and refactor scripts into a maintainable module.*

-   [ ] **1. Create the New Directory Structure**
    -   Create the following folders in the project root:
        ```bash
        mkdir -p src/gui/assets src/controller config tools build
        ```

-   [ ] **2. Move Existing Files to Their New Homes**
    -   Move all C++/Qt source files (`dialog.cpp`, `dialog.h`, `main.cpp`, `dialog.ui`, `untitled6.pro`) from `gui_mafdl/` into `src/gui/`.
    -   Move image assets (`Picture1.png`, `Picture2.png`) into `src/gui/assets/`.
    -   Move all Python scripts (`newmonox.py`, `pollphoton.py`, `photonmmu_pump.py`, etc.) from `scripts/` into `src/controller/`.
    -   Move network scripts (`startAP.sh`, `stopAP.sh`) into `tools/`.
    -   Create a new `config/network_settings.ini` to eventually replace `wpa_supplicant.conf`.

-   [ ] **3. Clean the Project Root and Old Directories**
    -   Delete the now-empty `gui_mafdl/`, `gui_mafdl_backupwithWiFi/`, and `scripts/` directories.
    -   Remove any stray build artifacts (`Makefile`, `moc_*`, `.qmake.stash`) from the project root and former script directories.

-   [ ] **4. Refactor Python Scripts into an Importable Module**
    -   Create an empty `src/controller/__init__.py` file to mark it as a Python package.
    -   Rename scripts to reflect their purpose:
        -   `newmonox.py` -> `printer_comms.py`
        -   `photonmmu_pump.py` -> `mmu_control.py`
        -   `pollphoton.py` -> `print_manager.py`
    -   Refactor the scripts so that core logic is contained within functions. This allows `print_manager.py` to `import` and call functions from `printer_comms.py` and `mmu_control.py` instead of calling them as separate processes.

-   [ ] **5. Update the Build System**
    -   Edit the `src/gui/untitled6.pro` file to point to the new source and asset locations.
    -   **Example:** `SOURCES += main.cpp` becomes `SOURCES += ./main.cpp` (relative to the `.pro` file), and `DISTFILES += ../Picture1.png` becomes `DISTFILES += ./assets/Picture1.png`.
    -   Ensure that running `qmake` and `make` from the `build/` directory correctly compiles the application.

-   [ ] **6. Create a `.gitignore` file**
    -   Add a `.gitignore` file to the project root to ignore build files, IDE settings, and OS-specific files.
    -   **Example `.gitignore` content:**
        ```
        # Build output
        build/
        build-*/

        # Qt files
        *.user
        .qmake.stash

        # Python cache
        __pycache__/
        *.pyc

        # OS files
        .DS_Store
        Thumbs.db
        ```

---

## Phase 2: GUI and Workflow Overhaul (User Experience)

*Goal: Implement the new, simplified user workflow and make the GUI the single point of control.*

-   [ ] **1. Abstract Away Hardcoded IP Address**
    -   Create `config/network_settings.ini` with content like:
        ```ini
        [Printer]
        ip_address = 192.168.4.2
        port = 6000
        ```
    -   Add a "Settings" area in the GUI with an input field to edit and save this IP address.
    -   Modify the C++ `dialog.cpp` to read this IP address and pass it as a command-line argument to the Python scripts.

-   [ ] **2. Redesign the "Start Print" Workflow**
    -   Rename the "Begin MM" button to **"Start Multi-Material Print"**.
    -   Remove the file dialog that asks the user to select `pollphoton.py`.
    -   The button's logic should now be:
        1.  Check that a print file has been selected from the "Get Files" list.
        2.  Check that a valid recipe has been defined.
        3.  Automatically execute the `src/controller/print_manager.py` script, passing the selected print file and recipe as arguments.

-   [ ] **3. Implement a Visual Recipe Editor**
    -   Replace the `QLineEdit` for the recipe string with a `QTableWidget`.
    -   The table should have columns for "Layer Number" and "Material" (a dropdown with Pump A, B, C, D).
    -   Add "Add Row" and "Remove Row" buttons to manage the recipe.
    -   When the user clicks "Start Multi-Material Print", the GUI reads the table and generates the recipe file (`output.txt`) in the required format (`A,50:B,120...`) behind the scenes.

-   [ ] **4. Create a Dynamic Printer Status Display**
    -   Add a dedicated status area in the GUI.
    -   Use a `QTimer` in `dialog.cpp` to periodically run the `printer_comms.py getstatus` command (every 2-3 seconds).
    -   Parse the output from the script and update labels in the GUI with live data:
        -   **Status:** `Printing`, `Paused`, `Idle`
        -   **File:** `MyPrint.pwmb`
        -   **Progress:** `55 / 2338 (2.3%)`
        -   **Next Change:** `Material B at Layer 120`

---

## Phase 3: Functionality Enhancements (Advanced Features)

*Goal: Add new capabilities that improve the system's utility and reliability.*

-   [ ] **1. Make GUI Operations Asynchronous**
    -   Implement script calls using `QProcess` signals (like `finished()`) or by moving them to a `QThread`.
    -   This will prevent the GUI from freezing while waiting for scripts to complete, especially during status checks or pump operations.

-   [ ] **2. Add a Pump Calibration and Priming Screen**
    -   Create a new tab or dialog in the GUI dedicated to the MMU.
    -   Add buttons for each pump:
        -   `Run Forward (5s)`
        -   `Run Reverse (5s)`
        -   `Prime (Run until purged)`
    -   This provides an easy way to set up and test the hardware without using the "Motor Control" text input.

-   [ ] **3. Implement Robust Error Handling**
    -   Add checks in the Python scripts to handle connection timeouts or unexpected responses from the printer.
    -   The GUI should display clear error messages to the user (e.g., "Connection to printer lost. Please check network.").

---

## Phase 4: Documentation and Deployment

*Goal: Make the project easy for a new user to install and operate.*

-   [ ] **1. Create an Installation Script (`tools/install_dependencies.sh`)**
    -   The script should automate the installation of all required packages.
    -   **Example commands:**
        ```bash
        #!/bin/bash
        echo "Installing system dependencies..."
        sudo apt-get update
        sudo apt-get install -y python3-pip qt5-default libqt5serialport5-dev build-essential git
        
        echo "Installing Python libraries..."
        pip3 install RPi.GPIO adafruit-circuitpython-motorkit
        
        echo "Installation complete."
        ```

-   [ ] **2. Update the README.md**
    -   Rewrite the "How to Use" section to reflect the new, simplified GUI-driven workflow.
    -   Add a clear "Installation" section that instructs the user to run the new installation script.

-   [ ] **3. Add Code-Level Documentation**
    -   Go through the C++ and Python files and add comments explaining complex functions and classes.
    -   Use Doxygen-style comments for C++ headers and Python docstrings for functions.




# Old todo items

# Development Roadmap and Tasks

This document outlines the development priorities for the Scion Multi-Material Unit Controller, organized by the new simplified user workflow vision.

## 🚀 Project Restructuring (COMPLETED)

- [x] **Clean Project Structure:** Reorganized files into logical directories (src/, config/, tools/, build/)
- [x] **Remove Build Artifacts:** Moved all build files to dedicated build/ directory
- [x] **Standardize Application Name:** Renamed from `untitled6` to `ScionMMUController`
- [x] **Configuration Management:** Created structured config files for network and pump settings
- [x] **Documentation:** Comprehensive README.md with new workflow explanation

## 🎯 Phase 1: Core Workflow Implementation (HIGH PRIORITY)

### GUI Enhancements for Simplified Workflow

- [ ] **Integrated Network Manager:** 
  - Add network configuration panel to GUI
  - Replace shell script dependency with built-in WiFi management
  - Auto-scan and connect to available networks
  - Toggle between AP mode and client mode from GUI

- [ ] **Auto-Discovery System:**
  - Implement printer discovery on network startup
  - Display connection status prominently in GUI
  - Show printer information (model, firmware, status) when connected
  - Handle connection failures gracefully with retry options

- [ ] **Enhanced Status Display:**
  - Real-time printer status (current layer, % complete, time remaining)
  - Live material level indicators
  - System health monitoring (temperatures, network status)
  - Last action/error message display

- [ ] **Visual Recipe Editor:**
  - Replace text input with table-based material change editor
  - Add/remove rows for layer-specific material changes
  - Dropdown selection for available materials/pumps
  - Validation to prevent formatting errors
  - Save/load recipe files for reuse

- [ ] **Streamlined Print Management:**
  - "Load Print File" button that fetches files directly from printer
  - File browser showing available files on printer with metadata
  - Single "Start Multi-Material Print" button
  - Automatic script execution without file dialogs

### Backend Improvements

- [ ] **Refactor Python Controller Modules:**
  - Rename and reorganize scripts to match new structure:
    - `pollphoton.py` → `print_manager.py`
    - `photonmmu_pump.py` → `mmu_control.py`
    - `newmonox.py` → `printer_comms.py`
  - Add proper error handling and logging
  - Implement configuration file reading
  - Add simulation mode for testing without hardware

- [ ] **Configuration System:**
  - Implement INI file reading in GUI application
  - Dynamic pump configuration loading
  - Network settings integration
  - User preference persistence

## 🔧 Phase 2: Reliability and User Experience (MEDIUM PRIORITY)

### Error Handling and Recovery

- [ ] **Robust Error Handling:**
  - Connection loss recovery during prints
  - Pump failure detection and alerts
  - Network connectivity monitoring
  - Graceful degradation when hardware unavailable

- [ ] **Pre-Print Validation:**
  - Check printer connectivity before starting
  - Validate material recipe (layer numbers, pump availability)
  - Confirm sufficient material levels
  - Test pump functionality

- [ ] **Asynchronous Operations:**
  - Move all network and hardware operations to background threads
  - Keep GUI responsive during long operations
  - Progress indicators for all async tasks
  - Cancellable operations

### Hardware Integration

- [ ] **Pump Calibration System:**
  - Built-in calibration wizard in GUI
  - "Dispense X ml" test buttons for each pump
  - Flow rate measurement and adjustment
  - Calibration history and maintenance tracking

- [ ] **Safety Features:**
  - Emergency stop functionality
  - Maximum pump runtime limits
  - Temperature monitoring integration
  - Material level sensor integration

## 🚧 Phase 3: Advanced Features (LOW PRIORITY)

### Smart Features

- [ ] **Material Management:**
  - Material library with properties (viscosity, cure time, etc.)
  - Automatic mixing calculations
  - Purge volume optimization
  - Material usage tracking

- [ ] **Print Optimization:**
  - Intelligent layer change timing
  - Minimal material waste algorithms
  - Print time estimation with material changes
  - Quality prediction based on material combinations

### Monitoring and Analytics

- [ ] **Data Logging:**
  - Print session logs with material usage
  - System performance metrics
  - Error frequency tracking
  - Maintenance schedule recommendations

- [ ] **Remote Monitoring:**
  - Web interface for remote status checking
  - Email/SMS notifications for print completion
  - Mobile app integration considerations
  - Cloud-based print queue management

## 🐛 Critical Bug Fixes (IMMEDIATE)

- [ ] **Fix Typo in `stopAP.sh`:** Correct `sydo` to `sudo` in the stopAP.sh script
- [ ] **Remove Hardcoded IP Addresses:** 
  - Replace hardcoded `192.168.4.2` in dialog.cpp
  - Make printer IP configurable through settings
  - Update all Python scripts to use configuration
- [ ] **Memory Leak Investigation:** Check for Qt object cleanup in dialog destruction
- [ ] **Thread Safety:** Ensure all GUI updates happen on main thread

## 📋 Legacy System Migration Tasks

### File Organization
- [ ] **Remove Legacy Directories:**
  - Archive or remove `gui/` experimental directory
  - Archive `gui_mafdl_backupwithWiFi/` 
  - Clean up old build directories
  - Remove temporary and swap files

- [ ] **Update Build System:**
  - Update all build scripts to use new directory structure
  - Test compilation on target platform (Raspberry Pi)
  - Create automated build pipeline
  - Package distribution creation

### Documentation Updates
- [ ] **Code Documentation:**
  - Add comprehensive comments to C++ source files
  - Document Python module interfaces
  - Create developer setup guide
  - API documentation for inter-module communication

- [ ] **User Documentation:**
  - Step-by-step setup guide with images
  - Troubleshooting guide with common issues
  - Hardware wiring diagrams
  - Material compatibility guide

## 📊 Success Metrics

### User Experience Goals
- Setup time: < 30 minutes for new users
- Print start time: < 5 minutes from GUI launch to print start
- Error rate: < 1% failed material changes
- User support requests: 50% reduction after UI improvements

### Technical Goals
- Build time: < 2 minutes on Raspberry Pi 4
- Memory usage: < 100MB during operation
- Network latency: < 500ms for printer communication
- Code coverage: > 80% for critical paths

## 🗓️ Timeline Estimates

- **Phase 1 (Core Workflow):** 6-8 weeks
- **Phase 2 (Reliability):** 4-6 weeks  
- **Phase 3 (Advanced Features):** 8-12 weeks
- **Bug Fixes:** Ongoing, 1-2 weeks for current critical issues

---

*This roadmap is a living document. Priorities may shift based on user feedback and testing results.*