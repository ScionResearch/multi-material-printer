# ESP32 WiFi Gateway Firmware

This directory contains firmware for the ESP32 that creates an isolated WiFi network for the multi-material printer system, ensuring consistent IP addressing between the Raspberry Pi and Anycubic printer.

## Overview

The ESP32-C3 acts as a WiFi gateway/router creating a dedicated 192.168.4.x network for:
- **192.168.4.1** - ESP32-C3 Gateway (this device)
- **192.168.4.2** - Anycubic Printer (automatic DHCP - first device to connect)
- **192.168.4.3** - Raspberry Pi (static IP configured on Pi)

**Key Features:**
- Simple WiFi access point with DHCP server
- Device monitoring and MAC address logging
- Consistent IP addressing (printer always gets .2, Pi uses static .3)
- Network isolation for reliable printer communication

## Files

- `src/main.cpp` - Main firmware file (PlatformIO)
- `wifi_gateway.ino` - Legacy Arduino sketch (for reference)
- `README.md` - This documentation
- `platformio.ini` - PlatformIO configuration

## Hardware Requirements

- **ESP32-C3** development board (or other ESP32 variants: ESP32, ESP32-S3)
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
   - Select Tools → Board → ESP32C3 Dev Module (or ESP32 Dev Module for other variants)
   - Select Tools → Port → [Your ESP32 port]
   - Set Tools → Upload Speed → 921600

3. **Upload Firmware**
   - Open `wifi_gateway.ino` in Arduino IDE
   - Click Upload button (→) or press Ctrl+U
   - Monitor serial output at 115200 baud to verify success

### Method 2: PlatformIO (Recommended for ESP32-C3)

1. **Install PlatformIO**
   - Install VS Code
   - Add PlatformIO extension from marketplace

2. **Build and Upload**
   ```bash
   # Default environment is esp32c3 (set in platformio.ini)
   platformio run --target upload

   # Or for specific board type:
   platformio run -e esp32c3 --target upload    # For ESP32-C3
   platformio run -e esp32dev --target upload   # For ESP32
   platformio run -e esp32s3 --target upload    # For ESP32-S3
   ```

3. **Monitor Serial Output**
   ```bash
   platformio device monitor

   # Or upload and monitor in one command:
   platformio run --target upload --target monitor
   ```

4. **Serial Monitor on Raspberry Pi**
   ```bash
   # Find the port (ESP32-C3 typically shows as /dev/ttyACM0)
   ls /dev/tty* | grep -E "(USB|ACM)"

   # Connect with screen
   screen /dev/ttyACM0 115200
   # Exit: Ctrl+A then K, then Y

   # Or use minicom
   sudo minicom -D /dev/ttyACM0 -b 115200
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

1. **Verify ESP32-C3 Operation**
   - Open PlatformIO Serial Monitor: `platformio device monitor`
   - Set baud rate to 115200
   - Reset ESP32-C3 - you should see startup messages
   - Look for "Access Point created successfully"

2. **Configure Raspberry Pi Static IP**
   ```bash
   # On Raspberry Pi, edit network configuration
   sudo nano /etc/dhcpcd.conf

   # Add these lines for wlan0:
   interface wlan0
   static ip_address=192.168.4.3/24
   static routers=192.168.4.1

   # Save and restart networking
   sudo systemctl restart dhcpcd
   ```

3. **Connect Devices to WiFi Network**
   - Connect Anycubic Printer to "PumpedMMP" network (password: "00000000")
   - Printer will automatically get IP **192.168.4.2** via DHCP
   - Connect Raspberry Pi to "PumpedMMP" network
   - Pi will use static IP **192.168.4.3**

4. **Verify Network Configuration**
   ```bash
   # On Raspberry Pi
   ip addr show wlan0          # Should show 192.168.4.3
   ping 192.168.4.1            # Ping ESP32-C3 gateway
   ping 192.168.4.2            # Ping printer

   # Test printer communication
   cd /path/to/multi-material-printer
   python3 src/controller/printer_comms.py -i 192.168.4.2 -c getstatus
   ```

## Verification

### Test Network Connectivity

1. **Check ESP32-C3 is broadcasting**
   ```bash
   # On any device, scan for WiFi networks
   # Look for "PumpedMMP" network
   ```

2. **Test Pi connectivity** (from Pi)
   ```bash
   ping 192.168.4.1  # Should reach ESP32-C3 gateway
   ping 192.168.4.2  # Should reach printer
   ```

3. **Test printer communication**
   ```bash
   cd /path/to/multi-material-printer
   python3 src/controller/printer_comms.py -i 192.168.4.2 -c getstatus
   ```

### Monitor Connected Devices

The ESP32-C3 firmware prints connected devices every 30 seconds to serial monitor:
```
--- Connected Devices ---
Total devices: 2
  Device 1: 192.168.4.2 (MAC: 28:6D:CD:A6:D9:F6) -> Anycubic Printer [OK]
  Device 2: 0.0.0.0 (MAC: B8:27:EB:48:32:7B) -> Raspberry Pi [OK]
--- End Device List ---
```

Note: The Pi shows as 0.0.0.0 because it uses a static IP (not assigned by DHCP).

## Troubleshooting

### ESP32-C3 Won't Flash
- Check USB cable (data + power, not just power)
- Hold BOOT button while pressing RESET, then release RESET
- Try different USB port or cable
- Verify correct board selection: `esp32c3` environment in PlatformIO

### WiFi Network Not Visible
- Check serial monitor for error messages
- Verify ESP32-C3 power supply (USB or external)
- Try different WiFi channel (modify code)
- Press RESET button on ESP32-C3

### Devices Can't Connect
- Verify password is correct ("00000000")
- Check if maximum connections reached (default: 10)
- Try restarting ESP32-C3
- Check device compatibility with 2.4GHz networks

### Printer Gets Wrong IP
- Ensure printer boots and connects **before** Raspberry Pi
- Printer should always get 192.168.4.2 (first DHCP client)
- Pi uses static IP 192.168.4.3 (no conflict)
- Power cycle both devices if IPs are swapped

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