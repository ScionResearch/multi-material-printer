# Print File Functionality Testing Procedure

## Overview

This document provides step-by-step testing procedures to verify the print file retrieval functionality fixes implemented for the multi-material 3D printer web interface.

## Background

The web UI previously showed empty print file lists while the Qt GUI could properly browse and select files. This was due to a broken stdout capture mechanism in the `_run_printer_command()` method that failed to capture output from the uart-wifi library.

## Fixed Components

- **`src/controller/printer_comms.py`**: Fixed stdout capture using subprocess approach
- **`web-app/app.py`**: Enhanced API endpoint to handle new dictionary format
- **`test_print_files.py`**: Comprehensive test script for verification

## Prerequisites

### Hardware Requirements
- Raspberry Pi 4 with network access
- Anycubic Photon printer connected and powered on
- ESP32 WiFi gateway (creates 192.168.4.x network)
- Print files loaded on the printer's storage

### Software Requirements
- uart-wifi library >= 0.2.1 installed on Raspberry Pi
- Web app dependencies (Flask, Socket.IO, etc.)
- Git repository pulled with latest changes

## Testing Procedure

### Step 1: Deploy Changes to Raspberry Pi

```bash
# SSH to Raspberry Pi
ssh pidlp@10.10.36.109

# Navigate to project directory
cd /path/to/multi-material-printer

# Pull latest changes
git pull origin feature/webui-operational-improvements

# Verify files are updated
git log --oneline -3
```

### Step 2: Verify Network Connectivity

```bash
# Test printer connectivity
ping 192.168.4.6  # or current printer IP

# Test direct printer communication
python3 -c "
import sys
sys.path.append('src/controller')
from printer_comms import PrinterCommunicator
comm = PrinterCommunicator()
print(f'Printer IP: {comm.printer_ip}')
status = comm.get_status()
print(f'Status: {status}')
"
```

### Step 3: Run Comprehensive Test Script

```bash
# Run the automated test script
python3 test_print_files.py

# For verbose output with detailed debugging
python3 test_print_files.py --verbose
```

**Expected Output:**
```
Comprehensive Print File Functionality Test
============================================================

1. Testing direct PrinterCommunicator functionality...
   Printer IP: 192.168.4.6
   Testing connection...
   ✓ Connection successful. Status: status: stop...
   Testing get_files() method...
   ✓ Found X print files:
     1. 'filename.pwmb' (internal: '1.pwmb')
     2. 'another_file.pwmb' (internal: '2.pwmb')

2. Testing web app API endpoint...
   ✓ Web API returned X files:
     1. 'filename.pwmb' (internal: '1.pwmb')
     2. 'another_file.pwmb' (internal: '2.pwmb')

3. Testing shared status integration...
   ✓ Shared status manager available
   ✓ Logged test activity to shared status

============================================================
Test Summary:
- Direct printer communication: Tested
- Web API endpoint: Tested (if app running)
- Shared status integration: Tested
```

### Step 4: Test Web Interface Manually

#### Start Web Application
```bash
# Navigate to web-app directory
cd web-app

# Start the Flask application
python3 app.py
```

#### Access Web Interface
1. Open browser to `http://192.168.4.2:5000` (or Pi's IP)
2. Navigate to the "Print Files" section
3. Click "Refresh" button
4. Verify print files are displayed with names and internal IDs

#### Expected Web UI Behavior
- Files should load and display in cards
- Each file shows display name and internal name
- "Select for Print" button should be enabled
- No "No files found" message should appear

### Step 5: Compare with Qt GUI

#### Start Qt GUI
```bash
# Build and run Qt application (if not already built)
cd src/gui
qmake ScionMMUController.pro
make
../../build/ScionMMUController
```

#### Verify Consistency
1. Both Qt GUI and Web UI should show the same files
2. File names and internal names should match
3. File count should be identical

## Troubleshooting

### If Test Script Shows Errors

#### Connection Failed
```
✗ Connection failed: [Errno 111] Connection refused
```
**Solutions:**
- Check printer power and network connection
- Verify printer IP in `config/network_settings.ini`
- Test with: `ping <printer_ip>`

#### No Files Found
```
✗ No print files found or get_files() returned empty list
```
**Solutions:**
- Ensure printer has files loaded on storage
- Check debug output for raw response
- Verify `getfileinfo` command works: `python3 -c "...comm._run_printer_command('getfileinfo')"`

#### Import Errors
```
Import error: No module named 'uart_wifi'
```
**Solutions:**
- Install uart-wifi: `pip install uart-wifi>=0.2.1`
- Check Python path and virtual environment

### If Web API Test Fails

#### Web App Not Running
```
⚠ Web app not running on localhost:5000 - skipping web API test
```
**Solutions:**
- Start web app: `cd web-app && python3 app.py`
- Check for port conflicts
- Verify Flask dependencies installed

#### API Returns Error
```
✗ Web API failed: Controller modules not available
```
**Solutions:**
- Ensure `src/controller` path is accessible from web-app
- Check Python module imports in web-app
- Verify file permissions

## Success Criteria

✅ **All tests must pass:**
1. Direct printer communication works
2. get_files() returns non-empty list with proper format
3. Web API endpoint returns same files
4. Both Qt GUI and Web UI show identical file lists

✅ **Web UI functionality:**
1. Print files load without errors
2. File names display correctly
3. Internal names are captured for print selection
4. User can browse and select files

## Regression Testing

After successful verification, test these scenarios:

### Multi-File Scenario
- Load multiple files on printer
- Verify all files appear in both interfaces
- Test file selection and printing workflow

### Network Recovery
- Disconnect printer briefly
- Reconnect and test file refresh
- Verify error handling and recovery

### Concurrent Access
- Access files from both Qt GUI and Web UI simultaneously
- Verify no conflicts or data corruption

## Documentation Updates

After successful testing, update:

1. **CLAUDE.md**: Note print file functionality is operational
2. **README**: Update feature status and testing notes
3. **Issue tracking**: Close related GitHub issues

## Contact

For testing issues or questions:
- Check project documentation in `CLAUDE.md`
- Review error logs in shared_status activity log
- Test individual components using direct Python imports

---

**Test completion checklist:**
- [ ] Changes deployed to Raspberry Pi
- [ ] Network connectivity verified
- [ ] Automated test script passes
- [ ] Web interface manual testing successful
- [ ] Qt GUI comparison completed
- [ ] No regressions found
- [ ] Documentation updated