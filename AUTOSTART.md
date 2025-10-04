# Raspberry Pi Autostart Configuration

The Scion Multi-Material Printer system is configured to start automatically on boot.

## Systemd Services

Two systemd services run the backend:

### 1. printer-webapp.service
- **Description:** Flask web app and WebSocket server
- **Location:** `/etc/systemd/system/printer-webapp.service`
- **Starts:** After network is available
- **User:** pidlp
- **Logs:** `/home/pidlp/pidlp/multi-material-printer/web_app.log`

### 2. printer-manager.service
- **Description:** Print manager and hardware controller
- **Location:** `/etc/systemd/system/printer-manager.service`
- **Starts:** After web app is running (8 second delay for Flask to initialize)
- **User:** pidlp
- **Logs:** `/home/pidlp/pidlp/multi-material-printer/print_manager.log`

## Browser Kiosk Mode

Chromium browser launches automatically in fullscreen kiosk mode:

- **Desktop Entry:** `~/.config/autostart/printer-kiosk.desktop`
- **URL:** http://localhost:5000
- **Mode:** Kiosk (fullscreen, no toolbars)
- **Delay:** 10 seconds after desktop login (allows services to fully start)

## Service Management

### Check Status
```bash
sudo systemctl status printer-webapp.service printer-manager.service
```

### View Logs
```bash
# Live log monitoring
sudo journalctl -u printer-webapp.service -f
sudo journalctl -u printer-manager.service -f

# Or application logs directly
tail -f ~/pidlp/multi-material-printer/web_app.log
tail -f ~/pidlp/multi-material-printer/print_manager.log
```

### Restart Services
```bash
sudo systemctl restart printer-webapp.service printer-manager.service
```

### Stop Services
```bash
sudo systemctl stop printer-webapp.service printer-manager.service
```

### Disable Autostart
```bash
# Disable systemd services
sudo systemctl disable printer-webapp.service printer-manager.service

# Remove browser autostart
rm ~/.config/autostart/printer-kiosk.desktop
```

## Manual Control (Development)

For development, you can use the manual scripts while services are stopped:

```bash
# Stop systemd services first
sudo systemctl stop printer-webapp.service printer-manager.service

# Use manual scripts
cd /home/pidlp/pidlp/multi-material-printer
./start_services.sh
./stop_services.sh

# Re-enable systemd when done
sudo systemctl start printer-webapp.service printer-manager.service
```

## Boot Sequence

1. **Pi boots** → Network initializes
2. **printer-webapp.service** starts → Flask server on port 5000
3. **8 second delay** → Allows Flask SocketIO server to fully initialize
4. **printer-manager.service** starts → Connects to web app via WebSocket
5. **Desktop loads** (if auto-login enabled)
6. **10 second delay**
7. **Chromium launches** in kiosk mode → http://localhost:5000

## Troubleshooting

**Services won't start:**
```bash
sudo systemctl status printer-webapp.service
sudo journalctl -u printer-webapp.service -n 50
```

**Browser doesn't launch:**
- Check `~/.config/autostart/printer-kiosk.desktop` exists
- Verify auto-login is enabled for user `pidlp`
- Check desktop environment is running

**Connection issues:**
- Ensure web app starts before print manager (dependency configured)
- Check logs for WebSocket connection errors
- Verify localhost:5000 is accessible: `curl http://localhost:5000`
