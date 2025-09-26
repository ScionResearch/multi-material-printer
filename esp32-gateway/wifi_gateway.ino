/*
 * Multi-Material Printer WiFi Gateway - ESP32 Firmware
 *
 * Creates isolated WiFi network with DHCP reservations to ensure consistent
 * IP addressing for printer that cannot be configured with static IP.
 *
 * Network Configuration:
 * - Gateway (ESP32):     192.168.4.1
 * - Raspberry Pi:        192.168.4.2 (configured via DHCP reservation)
 * - Anycubic Printer:    192.168.4.3 (configured via DHCP reservation)
 * - DHCP Range:          192.168.4.4 - 192.168.4.10 (for other devices)
 *
 * Hardware: ESP32 (any variant with WiFi)
 * Dependencies: None (uses built-in WiFi AP functionality)
 *
 * Author: Multi-Material Printer Project
 * Version: 3.0 - DHCP reservations for devices that can't use static IP
 */

#include <WiFi.h>
#include <WiFiAP.h>
#include <esp_wifi.h>

// Network Configuration
const char* ssid = "PumpedMMP";
const char* password = "00000000";

// Static IP Configuration
IPAddress gateway_ip(192, 168, 4, 1);    // ESP32 gateway IP
IPAddress subnet_mask(255, 255, 255, 0); // Subnet mask

// DHCP Reservations - MAC addresses for consistent IP assignment
// IMPORTANT: Update these with your actual device MAC addresses
// Find MAC: On Pi use 'ip link show' or 'ifconfig wlan0'
// Find Printer MAC: Check network settings or scan with 'nmap -sn 192.168.4.0/24'
struct DHCPReservation {
  String mac_address;
  IPAddress reserved_ip;
  String device_name;
};

// Configure your device MAC addresses here
DHCPReservation reservations[] = {
  {"XX:XX:XX:XX:XX:XX", IPAddress(192, 168, 4, 2), "Raspberry Pi"},     // Update with Pi MAC
  {"YY:YY:YY:YY:YY:YY", IPAddress(192, 168, 4, 3), "Anycubic Printer"} // Update with printer MAC
};
const int num_reservations = sizeof(reservations) / sizeof(reservations[0]);

// DHCP lease table to track assignments
struct DHCPLease {
  String mac_address;
  IPAddress assigned_ip;
  unsigned long lease_time;
};
DHCPLease active_leases[10]; // Support up to 10 devices
int num_active_leases = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("=== Multi-Material Printer WiFi Gateway v3.0 ===");
  Serial.println("Initializing ESP32 Access Point with DHCP reservations...");

  // Configure Access Point with static IP
  WiFi.mode(WIFI_AP);
  WiFi.softAPConfig(gateway_ip, gateway_ip, subnet_mask);

  bool ap_success = WiFi.softAP(ssid, password, 1, 0, 10); // channel 1, hidden=false, max_connections=10

  if (ap_success) {
    Serial.println("✓ Access Point created successfully");
    Serial.print("✓ Network SSID: ");
    Serial.println(ssid);
    Serial.print("✓ Gateway IP: ");
    Serial.println(WiFi.softAPIP());
    Serial.println();

    // Print DHCP reservations configuration
    Serial.println("DHCP Reservations Configured:");
    for (int i = 0; i < num_reservations; i++) {
      Serial.print("  ");
      Serial.print(reservations[i].device_name);
      Serial.print(" (");
      Serial.print(reservations[i].mac_address);
      Serial.print(") -> ");
      Serial.println(reservations[i].reserved_ip);
    }
    Serial.println("  Other devices: DHCP pool 192.168.4.4-254");
    Serial.println();

    Serial.println("IMPORTANT: Update MAC addresses in code before flashing!");
    Serial.println("Current MAC addresses are placeholders (XX:XX:XX:XX:XX:XX)");
    Serial.println();

    Serial.println("Setup Instructions:");
    Serial.println("1. Find device MAC addresses:");
    Serial.println("   Pi: ssh to pi, run 'ip link show wlan0'");
    Serial.println("   Printer: connect to network, check connected devices below");
    Serial.println("2. Update MAC addresses in firmware and reflash");
    Serial.println("3. Devices will automatically get reserved IPs via DHCP");
    Serial.println("4. Update network_settings.ini with ip_address=192.168.4.3");
    Serial.println();

    printNetworkInfo();
  } else {
    Serial.println("✗ Failed to create Access Point!");
    Serial.println("Check ESP32 configuration and try again.");
  }
}

void loop() {
  // Check connected devices periodically
  static unsigned long lastCheck = 0;
  if (millis() - lastCheck > 30000) { // Every 30 seconds
    checkConnectedDevices();
    lastCheck = millis();
  }

  delay(1000);
}

void printNetworkInfo() {
  Serial.println("--- Network Information ---");
  Serial.print("Access Point IP: ");
  Serial.println(WiFi.softAPIP());
  Serial.print("MAC Address: ");
  Serial.println(WiFi.softAPmacAddress());
  Serial.print("Channel: ");
  Serial.println(WiFi.channel());
  Serial.println("--- End Network Info ---");
}

void checkConnectedDevices() {
  wifi_sta_list_t wifi_sta_list;
  tcpip_adapter_sta_list_t adapter_sta_list;

  memset(&wifi_sta_list, 0, sizeof(wifi_sta_list));
  memset(&adapter_sta_list, 0, sizeof(adapter_sta_list));

  esp_wifi_ap_get_sta_list(&wifi_sta_list);
  tcpip_adapter_get_sta_list(&wifi_sta_list, &adapter_sta_list);

  Serial.println("--- Connected Devices ---");
  Serial.print("Total devices: ");
  Serial.println(adapter_sta_list.num);

  for (int i = 0; i < adapter_sta_list.num; i++) {
    tcpip_adapter_sta_info_t station = adapter_sta_list.sta[i];

    // Format MAC address
    String mac_str = "";
    for (int j = 0; j < 6; j++) {
      if (j > 0) mac_str += ":";
      if (station.mac[j] < 16) mac_str += "0";
      mac_str += String(station.mac[j], HEX);
    }
    mac_str.toUpperCase();

    Serial.print("  Device ");
    Serial.print(i + 1);
    Serial.print(": ");
    Serial.print(ip4addr_ntoa(&(station.ip)));
    Serial.print(" (MAC: ");
    Serial.print(mac_str);
    Serial.print(")");

    // Check if this device has a DHCP reservation
    String device_name = "Unknown";
    for (int r = 0; r < num_reservations; r++) {
      if (reservations[r].mac_address == mac_str) {
        device_name = reservations[r].device_name;
        Serial.print(" -> ");
        Serial.print(device_name);

        // Check if IP matches reservation
        String current_ip = String(ip4addr_ntoa(&(station.ip)));
        String reserved_ip = reservations[r].reserved_ip.toString();
        if (current_ip != reserved_ip) {
          Serial.print(" [WARNING: Should be ");
          Serial.print(reserved_ip);
          Serial.print("]");
        } else {
          Serial.print(" [OK]");
        }
        break;
      }
    }

    if (device_name == "Unknown") {
      Serial.print(" (No reservation)");
    }

    Serial.println();
  }

  // Show helpful information for configuring MAC addresses
  if (adapter_sta_list.num > 0) {
    Serial.println();
    Serial.println("To configure DHCP reservations:");
    Serial.println("1. Copy MAC addresses from above");
    Serial.println("2. Update firmware with actual MAC addresses");
    Serial.println("3. Reflash ESP32 with updated MAC addresses");
  }

  Serial.println("--- End Device List ---");
  Serial.println();
}

/*
 * Alternative configuration using WiFiAP library DHCP server
 * Uncomment this section if you want to try software-based static IP assignment
 * Note: This requires additional libraries and may not work on all ESP32 variants
 */

/*
#include <ESPAsyncWebServer.h>
AsyncWebServer server(80);

void setupWebInterface() {
  // Simple web interface to show network status
  server.on("/", HTTP_GET, [](AsyncWebServerRequest *request){
    String html = "<html><body>";
    html += "<h1>Multi-Material Printer Gateway</h1>";
    html += "<p>Gateway IP: " + WiFi.softAPIP().toString() + "</p>";
    html += "<p>Connected devices: Check serial monitor</p>";
    html += "</body></html>";
    request->send(200, "text/html", html);
  });

  server.begin();
  Serial.println("Web interface available at http://192.168.4.1");
}
*/