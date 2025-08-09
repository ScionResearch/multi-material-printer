#!/bin/bash

echo "Switiching to AP mode..."

sudo systemctl stop NetworkManager
sudo systemctl disable NetworkManager

sudo systemctl stop wpa_supplicant
#sudo systemctl stop dhcpcd

sudo systemctl disable wpa_supplicant
#sudo systemctl disable dhcpcd

sudo systemctl enable dhcpcd
sudo systemctl enable hostapd
sudo systemctl enable dnsmasq
sudo systemctl start dhcpcd
sudo systemctl start hostapd
sudo systemctl start dnsmasq

echo "Switched to AP mode..."

sudo reboot
