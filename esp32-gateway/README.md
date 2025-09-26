# ESP32 WiFi Gateway Firmware

This directory contains firmware for the ESP32 that creates an isolated WiFi network for the multi-material printer system, ensuring consistent IP addressing between the Raspberry Pi and Anycubic printer.

## Overview

The ESP32 acts as a WiFi gateway/router creating a dedicated 192.168.4.x network for:
- **192.168.4.1** - ESP32 Gateway (this device)
- **192.168.4.2+** - Raspberry Pi and Anycubic Printer (automatic DHCP)
- **Software auto-discovery** handles finding the printer's current IP

**Key Features:**
- Simple WiFi access point (no complex DHCP reservations needed)
- Device monitoring and MAC address logging
- Automatic printer IP discovery in Python software
- Robust solution that works even when IPs change

## Files

- `wifi_gateway.ino` - Main firmware file
- `README.md` - This documentation
- `platformio.ini` - PlatformIO configuration (optional)

## Hardware Requirements

- ESP32 development board (any variant with WiFi)
- USB cable for programming
- Computer with Arduino IDE or PlatformIO

## Installation Methods

### Method 1: Arduino IDE (Recommended)

1. **Install Arduino IDE**
   - Download from https://www.arduino.cc/en/software
   - Install ESP32 board support:
     - Go to File → Preferences
     - Add to "Additional Board Manager URLs":
       ```
       https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
       ```
     - Go to Tools → Board → Boards Manager
     - Search "esp32" and install "ESP32 by Espressif Systems"

2. **Configure Arduino IDE**
   - Connect ESP32 to computer via USB
   - Select Tools → Board → ESP32 Dev Module (or your specific board)
   - Select Tools → Port → [Your ESP32 port]
   - Set Tools → Upload Speed → 115200

3. **Upload Firmware**
   - Open `wifi_gateway.ino` in Arduino IDE
   - Click Upload button (→) or press Ctrl+U
   - Monitor serial output at 115200 baud to verify success

### Method 2: PlatformIO (Advanced Users)

1. **Install PlatformIO**
   - Install VS Code
   - Add PlatformIO extension

2. **Create Project**
   ```bash
   pio project init --board esp32dev
   cp wifi_gateway.ino src/main.cpp
   ```

3. **Upload**
   ```bash
   pio run -t upload
   pio device monitor
   ```

### Method 3: ESP32 Flash Tool

1. **Download ESP32 Flash Tool**
   - Get from Espressif official site
   - Or use esptool.py

2. **Compile and Flash**
   - Compile .ino file to .bin using Arduino IDE
   - Use flash tool to upload .bin file

## Configuration

### Before Flashing

The firmware works out-of-the-box with default settings, but you can customize:

```cpp
// Network Configuration
const char* ssid = "PumpedMMP";        // WiFi network name
const char* password = "00000000";     // WiFi password

// IP Configuration
IPAddress gateway_ip(192, 168, 4, 1);    // ESP32 IP
IPAddress dhcp_start(192, 168, 4, 4);    // DHCP range start
IPAddress dhcp_end(192, 168, 4, 10);     // DHCP range end
```

### After Flashing

1. **Verify ESP32 Operation**
   - Open Arduino IDE Serial Monitor (Tools → Serial Monitor)
   - Set baud rate to 115200
   - Reset ESP32 - you should see startup messages
   - Look for "Access Point created successfully"

2. **Connect Devices to WiFi Network**
   - Connect Raspberry Pi to "PumpedMMP" network (password: "00000000")
   - Connect printer to "PumpedMMP" network
   - Devices will get automatic IP addresses via DHCP

3. **Test Auto-Discovery** (on Raspberry Pi)
   ```bash
   ssh pildp@10.10.36.109
   cd /path/to/multi-material-printer
   python3 src/controller/printer_comms.py --discover
   ```

   This will scan the network and find the printer automatically.

4. **Update Project Configuration** (optional)
   ```bash
   cp config/network_settings.ini.template config/network_settings.ini
   ```

   The software now auto-discovers the printer IP, so manual configuration is optional.

## Verification

### Test Network Connectivity

1. **Check ESP32 is broadcasting**
   ```bash
   # On any device, scan for WiFi networks
   # Look for "PumpedMMP" network
   ```

2. **Test Pi connectivity** (from Pi)
   ```bash
   ping 192.168.4.1  # Should reach ESP32
   ```

3. **Auto-discover printer** (from Pi)
   ```bash
   cd /path/to/multi-material-printer
   python3 src/controller/printer_comms.py --discover
   ```

4. **Test printer communication with auto-connect**
   ```bash
   python3 src/controller/printer_comms.py --auto-connect
   ```

5. **Manual IP test if known**
   ```bash
   python3 src/controller/printer_comms.py -i 192.168.4.3 -c getstatus
   ```

### Monitor Connected Devices

The ESP32 firmware prints connected devices every 30 seconds to serial monitor:
```
Connected devices: 2
  Device 1: IP 192.168.4.2, MAC aa:bb:cc:dd:ee:ff
  Device 2: IP 192.168.4.3, MAC 11:22:33:44:55:66
```

## Troubleshooting

### ESP32 Won't Flash
- Check USB cable (data + power, not just power)
- Hold BOOT button while pressing RESET, then release RESET
- Try different USB port or cable
- Verify correct board selection in Arduino IDE

### WiFi Network Not Visible
- Check serial monitor for error messages
- Verify ESP32 power supply (USB or external)
- Try different WiFi channel (modify code)
- Check antenna connection (if external)

### Devices Can't Connect
- Verify password is correct ("00000000")
- Check if maximum connections reached (default: 4)
- Try restarting ESP32
- Check device compatibility with 2.4GHz networks

### IP Conflicts
- Ensure no other 192.168.4.x networks nearby
- Verify static IP configuration on Pi and printer
- Check DHCP range doesn't overlap with static IPs

## Advanced Configuration

### Enable Web Interface (Optional)

Uncomment the web interface section in the code to enable status monitoring via browser at `http://192.168.4.1`.

### MAC Address Filtering

To restrict access to specific devices, modify the code to check MAC addresses before allowing connections.

### Different IP Range

To use a different IP range (e.g., 192.168.5.x), modify:
```cpp
IPAddress gateway_ip(192, 168, 5, 1);
// Update all related IPs and documentation
```

## Firmware Updates

To update the firmware:
1. Keep existing network settings if they work
2. Flash new firmware using same method as initial installation
3. Verify all devices reconnect properly
4. Check serial monitor for any configuration changes needed

## Support

- Check serial monitor output for diagnostic information
- Verify all IP configurations match between devices
- Test individual components (ESP32 → Pi → Printer) systematically
- Review main project documentation in `../CLAUDE.md` for integration details