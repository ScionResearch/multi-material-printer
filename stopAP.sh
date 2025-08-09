#!/bin/bash

echo "Switiching to WiFi mode..."
sudo systemctl stop hostapd
sudo systemctl stop dnsmasq
sudo systemctl stop dhcpcd

sudo systemctl disable hostapd
sydo systemctl disable dnsmasq
sydo systemctl disable dhcpcd

#sudo systemctl enable wpa_supplicant
sudo systemctl enable NetworkManager
#sudo systemctl start wpa_supplicant
sudo systemctl start NetworkManager

echo "Switched to WiFi Mode..."

sudo reboot
