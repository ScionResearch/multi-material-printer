# Migration Guide: From Old Structure to New Architecture

This guide helps existing users transition from the old project structure to the new organized architecture.

## 🔄 What Changed

### Directory Structure Changes

| Old Location | New Location | Purpose |
|-------------|-------------|---------|
| `gui_mafdl/` | `src/gui/` | Qt C++ source code |
| `scripts/` | `src/controller/` | Python control modules |
| Root directory | `tools/` | Shell scripts and utilities |
| Root directory | `config/` | Configuration files |
| `build-*/` | `build/` | All build outputs |

### File Renames

| Old Name | New Name | Change |
|----------|----------|--------|
| `untitled6` | `ScionMMUController` | More descriptive name |
| `untitled6.pro` | `ScionMMUController.pro` | Project file rename |
| `pollphoton.py` | `print_manager.py` | Clearer purpose |
| `photonmmu_pump.py` | `mmu_control.py` | Clearer purpose |
| `newmonox.py` | `printer_comms.py` | Clearer purpose |

## 📦 Migration Steps

### For Existing Installations

1. **Backup your current working setup:**
   ```bash
   cp -r your-current-project your-current-project-backup
   ```

2. **Save your current configuration:**
   ```bash
   # If you have modified any scripts or settings, note them down
   # Check for custom IP addresses, pump settings, etc.
   ```

3. **Pull the new structure:**
   ```bash
   git pull origin main
   ```

4. **Migrate your personal settings:**
   - Copy your WiFi credentials to `config/network_settings.ini`
   - Update pump settings in `config/pump_profiles.json`
   - Any custom modifications should be noted for re-implementation

5. **Clean old build files:**
   ```bash
   rm -rf build-untitled6-*
   rm -f gui_mafdl/*.o gui_mafdl/moc_* gui_mafdl/Makefile
   rm -f scripts/*.o scripts/moc_* scripts/Makefile
   ```

6. **Build with new structure:**
   ```bash
   cd src/gui
   qmake ScionMMUController.pro
   make
   ```

### For New Installations

Simply follow the installation guide in the README.md - no migration needed!

## ⚙️ Configuration Migration

### Network Settings
If you previously edited `wpa_supplicant.conf` or used shell scripts for network setup:

**Old way:**
```bash
./startAP.sh  # or ./stopAP.sh
# Edit wpa_supplicant.conf manually
```

**New way:**
Edit `config/network_settings.ini`:
```ini
[wifi]
ssid = "YourNetwork"
password = "YourPassword"
enabled = true

[access_point]
enabled = false
```

### Hardcoded IPs
If you previously modified Python scripts with hardcoded printer IP addresses:

**Old way:**
```python
# In various .py files
printer_ip = "192.168.4.2"  # Hardcoded
```

**New way:**
The IP is now read from `config/network_settings.ini`:
```ini
[printer]
ip_address = "192.168.4.2"  # Or leave empty for auto-discovery
```

### Pump Settings
If you previously modified pump control parameters in Python scripts:

**Old way:**
```python
# Hardcoded in photonmmu_pump.py
pump_steps = 100
flow_rate = 2.5
```

**New way:**
Settings are in `config/pump_profiles.json`:
```json
{
  "pumps": {
    "pump_a": {
      "flow_rate_ml_per_second": 2.5,
      "calibration": {
        "steps_per_ml": 100
      }
    }
  }
}
```

## 🔧 Build System Changes

### Old Build Process
```bash
cd build-untitled6-LinuxKit-Release/
qmake ../gui_mafdl/untitled6.pro
make
./untitled6
```

### New Build Process
```bash
cd src/gui
qmake ScionMMUController.pro
make
../../build/ScionMMUController
```

## 🐛 Common Migration Issues

### Issue: "File not found" errors
**Cause:** Old paths in configuration or scripts
**Solution:** Update any references to old directory structure

### Issue: Build fails with missing files
**Cause:** Old build files interfering
**Solution:** Clean all old build artifacts:
```bash
find . -name "*.o" -delete
find . -name "moc_*" -delete
find . -name "Makefile" -delete
```

### Issue: Python scripts don't work
**Cause:** Import paths changed
**Solution:** The controller scripts are now a proper Python package. If calling from GUI, use:
```cpp
// Old way
process.start("python3", QStringList() << "../scripts/pollphoton.py");

// New way  
process.start("python3", QStringList() << "-m" << "src.controller.print_manager");
```

### Issue: Configuration not loading
**Cause:** Looking for files in old locations
**Solution:** Update any hardcoded paths to use the new `config/` directory

## 📋 Post-Migration Checklist

- [ ] Application builds successfully with new project file
- [ ] Can connect to printer with new configuration system
- [ ] Pump controls work with new configuration
- [ ] Network setup works (test both WiFi and AP mode)
- [ ] All custom modifications have been migrated
- [ ] Old build directories have been cleaned up
- [ ] Documentation reflects your actual setup

## 🆘 Rollback Plan

If you encounter issues and need to go back to the old structure:

1. **Restore your backup:**
   ```bash
   rm -rf current-project
   cp -r your-current-project-backup current-project
   cd current-project
   ```

2. **Rebuild old version:**
   ```bash
   cd build-untitled6-LinuxKit-Release/
   qmake ../gui_mafdl/untitled6.pro
   make
   ```

3. **Report the issue:**
   Please create an issue on GitHub with details about what went wrong, so we can improve the migration process.

## 📞 Support

If you encounter issues during migration:

1. Check this guide first
2. Review the troubleshooting section in README.md
3. Check existing GitHub issues
4. Create a new issue with:
   - Your previous setup details
   - Error messages
   - What you were trying to do when it failed

The new structure is designed to be much more maintainable and user-friendly. Once migrated, you'll benefit from better organization, clearer configuration, and easier troubleshooting.