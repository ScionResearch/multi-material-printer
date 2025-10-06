# Scion Multi-Material 3D Printer - Programming Manual

**Version:** 1.0
**Last Updated:** October 2025
**For Developers and System Administrators**

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Installation & Deployment](#installation--deployment)
3. [Configuration](#configuration)
4. [Code Structure](#code-structure)
5. [API Reference](#api-reference)
6. [WebSocket Protocol](#websocket-protocol)
7. [Hardware Integration](#hardware-integration)
8. [Development Workflow](#development-workflow)
9. [Testing & Debugging](#testing--debugging)
10. [Extending the System](#extending-the-system)

---

## System Architecture

### Overview

The system uses a **two-process WebSocket architecture** for real-time hardware control and status updates:

```
┌─────────────── Browser Client ────────────────┐
│  Dashboard  │  Recipe Builder  │  Manual      │
│  (React-like vanilla JS + Bootstrap)          │
└────────────────┬──────────────────────────────┘
                 │ HTTP REST + WebSocket
                 ▼
┌─────────────── Flask Web App ─────────────────┐
│  app.py (Port 5000)                           │
│  • HTTP API endpoints                         │
│  • Flask-SocketIO WebSocket server            │
│  • Command router                             │
│  • Status broadcaster                         │
└────────────────┬──────────────────────────────┘
                 │ WebSocket IPC
                 │ ('command' + 'status_update' events)
                 ▼
┌─────────────── Print Manager ─────────────────┐
│  print_manager.py                             │
│  • WebSocket client (socketio-client)         │
│  • Monitoring loop (4s interval)              │
│  • Material change orchestration              │
│  • Hardware command execution                 │
└────────────────┬──────────────────────────────┘
                 │ Direct function calls
                 ▼
┌─────────────── Hardware Modules ──────────────┐
│  printer_comms.py  │  mmu_control.py          │
│  photonmmu_pump.py │  solenoid_control.py     │
│  (uart-wifi)       │  (Adafruit MotorKit)     │
└────────────────┬──────────────────────────────┘
                 │ WiFi / I2C / GPIO
                 ▼
┌─────────────── Physical Hardware ─────────────┐
│  Anycubic Printer (192.168.4.2)               │
│  Stepper Pumps A/B/C/D (I2C 0x60/0x61)       │
│  Air Solenoid Valve (GPIO 22)                 │
└────────────────────────────────────────────────┘
```

### Design Principles

1. **Single Hardware Authority**: Only `print_manager.py` communicates with hardware
2. **Event-Driven Communication**: All commands flow via WebSocket events
3. **Stateless HTTP API**: REST endpoints for client commands, no server-side sessions
4. **Persistent Services**: Both processes run continuously as background services
5. **Real-Time Updates**: Status pushed to clients via WebSocket, not polling

---

## Installation & Deployment

### Prerequisites

**Hardware:**
- Raspberry Pi 4B (4GB RAM recommended)
- Raspbian/Raspberry Pi OS (Debian-based)
- I2C enabled (`sudo raspi-config` → Interface Options → I2C → Enable)
- Python 3.7+

**Software Dependencies:**
```bash
# System packages
sudo apt-get update
sudo apt-get install -y python3 python3-pip git i2c-tools

# Python packages (see requirements.txt)
pip3 install -r requirements.txt
```

### Initial Setup on Raspberry Pi

1. **Clone Repository:**
   ```bash
   cd /home/pidlp/pidlp
   git clone https://github.com/ScionResearch/multi-material-printer
   cd multi-material-printer
   ```

2. **Install Dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Configure Network:**
   - Edit `config/network_settings.ini`
   - Set printer IP (default: `192.168.4.2`)
   - Verify Pi can reach printer network

4. **Test Hardware:**
   ```bash
   # Test I2C devices
   i2cdetect -y 1
   # Should show 0x60 and 0x61

   # Test printer connection
   cd src/controller
   python3 -c "import printer_comms; print(printer_comms.get_status('192.168.4.2'))"

   # Test pump
   python3 mmu_control.py A F 3

   # Test solenoid
   python3 solenoid_control.py 2
   ```

5. **Start Services:**
   ```bash
   chmod +x start_services.sh stop_services.sh
   ./start_services.sh
   ```

6. **Verify Services Running:**
   ```bash
   pgrep -f "app.py"          # Should return web app PID
   pgrep -f "print_manager.py" # Should return print manager PID
   ```

7. **Access Web Interface:**
   - Open browser to: `http://10.10.36.109:5000`
   - Verify "Backend: Online" status

### Deployment Workflow

**After code changes, deploy to Pi:**

```bash
# From local development machine
cd multi-material-printer
git add -A
git commit -m "Description of changes"
git push origin main

# SSH deploy to Pi (one-line command)
ssh pidlp@10.10.36.109 "cd /home/pidlp/pidlp/multi-material-printer && \
  git stash && \
  git pull origin main && \
  chmod +x *.sh && \
  ./stop_services.sh && \
  ./start_services.sh && \
  echo '✓ Deployment complete'"
```

**Important:**
- Always restart services after code changes
- Force-refresh browser (Ctrl+Shift+R) after HTML/JS changes
- Monitor logs during deployment: `tail -f web_app.log print_manager.log`

---

## Configuration

### File Locations

```
config/
├── network_settings.ini      # Printer IP, port, timeouts
├── pump_profiles.json         # Pump parameters, material change timing
└── recipe.txt                 # Current material change recipe
```

### `network_settings.ini`

```ini
[printer]
ip_address = 192.168.4.2
port = 6000
timeout_seconds = 5
polling_interval_seconds = 4
```

**Parameters:**
- `ip_address`: Printer IP on WiFi network
- `port`: uart-wifi communication port
- `timeout_seconds`: Socket timeout for printer commands
- `polling_interval_seconds`: How often to query printer status

### `pump_profiles.json`

**Pump Definitions:**
```json
{
  "pumps": {
    "pump_a": {
      "name": "Pump A",
      "description": "Primary material pump",
      "flow_rate_ml_per_second": 5.0,
      "max_volume_ml": 200,
      "calibration": {
        "steps_per_ml": 100,
        "last_calibrated": null
      }
    }
  }
}
```

**Material Change Sequence Timing:**
```json
{
  "material_change": {
    "quiescence_seconds": 10,
    "bed_raise_delay_seconds": 1,
    "bed_raise_time_seconds": 1,
    "bed_raise_safety_buffer_seconds": 1,
    "drain_volume_ml": 50,
    "fill_volume_ml": 45,
    "settle_time_seconds": 5
  }
}
```

**Solenoid Configuration:**
```json
{
  "solenoid": {
    "enabled": true,
    "gpio_pin": 22,
    "description": "Air valve that blows air across vat to push resin toward drain",
    "active_during_drain": true,
    "activate_before_drain_delay_seconds": 0.5,
    "deactivate_after_drain_delay_seconds": 1.0
  }
}
```

### Environment Variables

Set in shell or systemd service files:

```bash
# Quiescent window override (default: from pump_profiles.json)
export MMU_PAUSE_QUIESCENCE_SECONDS=10

# Flask settings
export FLASK_ENV=production
export FLASK_DEBUG=0

# Logging levels
export LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

---

## Code Structure

### Directory Layout

```
multi-material-printer/
├── web-app/                   # Flask web application
│   ├── app.py                 # Main Flask app, HTTP API, SocketIO server
│   ├── static/
│   │   ├── app.js             # Frontend JavaScript (WebSocket client)
│   │   ├── style.css          # Custom CSS
│   │   └── config.js          # Config page JavaScript
│   └── templates/
│       ├── base.html          # Base template with navigation
│       ├── index.html         # Dashboard page
│       ├── recipe.html        # Recipe builder page
│       ├── manual.html        # Manual controls page
│       └── config.html        # Configuration page
│
├── src/controller/            # Hardware control modules
│   ├── print_manager.py       # Main orchestration service
│   ├── printer_comms.py       # Printer WiFi communication (uart-wifi)
│   ├── mmu_control.py         # Material change orchestration
│   ├── photonmmu_pump.py      # Low-level stepper pump control
│   ├── solenoid_control.py    # Air valve GPIO control
│   ├── websocket_ipc.py       # WebSocket client library
│   └── logging_config.py      # Centralized logging setup
│
├── config/                    # Configuration files
│   ├── network_settings.ini
│   ├── pump_profiles.json
│   └── recipe.txt
│
├── run/                       # Runtime files (created by scripts)
│   ├── web_app.pid
│   └── print_manager.pid
│
├── docs/                      # Documentation
│   ├── OPERATING_MANUAL.md
│   └── PROGRAMMING_MANUAL.md  # This file
│
├── start_services.sh          # Start both services
├── stop_services.sh           # Stop both services
├── web_app.log               # Web app logs
├── print_manager.log         # Print manager logs
├── requirements.txt          # Python dependencies
├── README.md                 # Project overview
└── CLAUDE.md                 # Claude Code assistant instructions
```

### Key Modules

#### `web-app/app.py`

**Responsibilities:**
- Flask HTTP server
- Flask-SocketIO WebSocket server
- REST API endpoints
- Client WebSocket connections
- Command routing to print manager
- Status broadcasting to clients

**Key Functions:**
- `send_command_to_print_manager(cmd_type, params)`: Emit command event to print manager
- `@socketio.on('status_update')`: Receive status from print manager, broadcast to clients
- `@app.route('/api/*')`: HTTP API endpoints

#### `src/controller/print_manager.py`

**Responsibilities:**
- WebSocket client connection to web app
- Printer status monitoring loop (4s interval)
- Recipe management and layer tracking
- Material change orchestration
- Hardware command execution

**Key Functions:**
- `_monitoring_loop()`: Main loop, polls printer status, triggers material changes
- `_process_shared_command(command)`: Handle commands from web app
- `_execute_material_change(layer, material)`: Full material change sequence
- `_send_status_update(category, message, data)`: Send status to web app

**State Management:**
- `_recipe_active`: Boolean, multi-material mode active
- `_recipe`: Dict of layer → material mappings
- `_last_processed_layer`: Prevent duplicate material changes

#### `src/controller/mmu_control.py`

**Class:** `MMUController`

**Methods:**
- `change_material(target_material)`: Execute drain → fill → settle sequence
- `run_pump(pump_name, direction, duration_seconds)`: Control individual pump
- `run_pump_volume(pump_name, direction, volume_ml)`: Volume-based pump control
- `_init_solenoid()`: Initialize air valve on startup

**Solenoid Integration:**
```python
# In change_material():
if solenoid_enabled:
    solenoid_control.activate_solenoid()  # Before drain
    time.sleep(activate_before_drain_delay_seconds)

# Run drain pump...

if solenoid_enabled:
    time.sleep(deactivate_after_drain_delay_seconds)
    solenoid_control.deactivate_solenoid()  # After drain
```

#### `src/controller/photonmmu_pump.py`

**Low-Level Pump Control:**

**Initialization:**
```python
from adafruit_motorkit import MotorKit

kit = MotorKit()           # I2C address 0x60
kit2 = MotorKit(address=0x61)  # I2C address 0x61

STEPPER_A = kit.stepper1   # Pump A
STEPPER_B = kit.stepper2   # Pump B
STEPPER_C = kit2.stepper1  # Pump C
STEPPER_D = kit2.stepper2  # Drain pump
```

**Function:**
- `run_stepper(pump_id, direction, duration_seconds)`: Run pump for time duration

**Important:** Only one stepper can run at a time on each MotorKit. Function automatically releases other motors.

#### `src/controller/solenoid_control.py`

**GPIO Control Module:**

**Functions:**
- `init_solenoid()`: Setup GPIO pin 22 as output
- `activate_solenoid()`: Set GPIO HIGH (valve opens, air flows)
- `deactivate_solenoid()`: Set GPIO LOW (valve closes, air stops)
- `test_solenoid(duration)`: Test cycle (open → wait → close)
- `cleanup()`: Release GPIO resources

**State Tracking:**
```python
_initialized = False      # GPIO setup complete
_current_state = False    # Valve open/closed
```

#### `src/controller/printer_comms.py`

**Printer Communication via uart-wifi:**

**Functions:**
- `get_status(ip_address)`: Query printer status
- `pause_print(ip_address)`: Send pause command
- `resume_print(ip_address)`: Send resume command
- `stop_print(ip_address)`: Send stop command
- `start_print(ip_address, filename)`: Start print job

**Status Object:**
```python
class MonoXStatus:
    status: str          # 'print', 'pause', 'stop', 'ERROR1'
    current_layer: int
    total_layers: int
    progress_percent: float
    elapsed_seconds: int
```

**Communication:**
- TCP socket to printer IP:port
- Commands: `getstatus`, `gopause`, `goresume`, `gostop`
- Response parsing from comma-separated values

---

## API Reference

### HTTP REST Endpoints

All endpoints return JSON: `{"success": bool, "message": str, ...}`

#### System Status

**`GET /api/status`**

Returns current system status.

**Response:**
```json
{
  "printer_status": "print",
  "current_layer": 42,
  "total_layers": 200,
  "progress_percent": 21.0,
  "elapsed_time": "00:15:32",
  "multi_material_active": true,
  "next_material_change": {"layer": 50, "material": "A"},
  "pumps": {
    "A": {"status": "idle", "last_operation": "..."},
    "B": {"status": "idle"},
    "C": {"status": "idle"},
    "D": {"status": "idle"}
  },
  "backend_connected": true
}
```

#### Printer Control

**`POST /api/printer/<action>`**

Control printer state.

**Actions:** `pause`, `resume`, `stop`

**Example:**
```bash
curl -X POST http://10.10.36.109:5000/api/printer/pause
```

**Response:**
```json
{
  "success": true,
  "action": "pause",
  "command_id": "web_1759741123_4"
}
```

#### Pump Control

**`POST /api/pump`**

Manual pump operation.

**Request Body:**
```json
{
  "motor": "A",           // A, B, C, or D
  "direction": "F",       // F = forward, R = reverse
  "duration": 10          // Seconds (1-300)
}
```

**Response:**
```json
{
  "success": true,
  "message": "Pump A command sent (F for 10s)",
  "command_id": "web_1759741124_5"
}
```

#### Solenoid Control

**`POST /api/solenoid/<action>`**

Control air valve.

**Actions:** `activate`, `deactivate`, `test`

**For test action, include duration in request body:**
```json
{
  "duration": 2  // Seconds (1-30)
}
```

**Example:**
```bash
# Activate valve
curl -X POST http://10.10.36.109:5000/api/solenoid/activate

# Test valve for 3 seconds
curl -X POST http://10.10.36.109:5000/api/solenoid/test \
  -H "Content-Type: application/json" \
  -d '{"duration": 3}'
```

#### Multi-Material Control

**`POST /api/multi-material/start`**

Activate multi-material mode (start monitoring recipe).

**Response:**
```json
{
  "success": true,
  "message": "Multi-material mode activated"
}
```

**`POST /api/multi-material/stop`**

Deactivate multi-material mode.

**`GET /api/recipe`**

Get current recipe.

**Response:**
```json
{
  "recipe_text": "A,50:B,120:C,200",
  "parsed": [
    {"material": "A", "layer": 50},
    {"material": "B", "layer": 120},
    {"material": "C", "layer": 200}
  ]
}
```

**`POST /api/recipe`**

Save new recipe.

**Request Body:**
```json
{
  "recipe": "A,50:B,120:C,200"
}
```

---

## WebSocket Protocol

### Connection

**Client → Server:**
```javascript
const socket = io('http://10.10.36.109:5000');

socket.on('connect', () => {
  console.log('Connected to server');
});
```

### Events

#### `status_update` (Server → Client)

Real-time status updates from print manager.

**Payload:**
```json
{
  "timestamp": 1759741123.4,
  "category": "PRINTER_STATUS",  // or MATERIAL, PUMP, SOLENOID, etc.
  "message": "Printer status: print",
  "level": "info",  // info, warning, error
  "data": {
    // Category-specific data
    "status": "print",
    "layer": 42,
    "progress": 21.0
  }
}
```

**Categories:**
- `PRINTER_STATUS`: Printer state changes
- `MATERIAL`: Material change events
- `TIMING`: Material change step timing
- `PUMP`: Pump operations
- `SOLENOID`: Air valve operations
- `COMMAND`: Command execution results
- `PROGRESS`: Layer progress updates
- `QUIESCENCE`: Quiescent window timing

**Client Handler:**
```javascript
socket.on('status_update', (data) => {
  console.log(`[${data.category}] ${data.message}`);

  // Update UI based on category
  if (data.category === 'PRINTER_STATUS') {
    updatePrinterStatus(data.data.status, data.data.layer);
  }
});
```

#### `command` (Web App → Print Manager)

Command from web app to print manager.

**Payload:**
```json
{
  "type": "pump_control",  // Command type
  "command_id": "web_1759741123_4",  // Unique ID
  "parameters": {
    "motor": "A",
    "direction": "F",
    "duration": 10
  }
}
```

**Command Types:**
- `start_multi_material`: Activate MM mode
- `stop_multi_material`: Deactivate MM mode
- `pause_print`: Pause printer
- `resume_print`: Resume printer
- `stop_print`: Stop print job
- `pump_control`: Manual pump control
- `solenoid_control`: Air valve control
- `emergency_stop`: Halt all operations

#### `command_result` (Print Manager → Web App)

Command execution result.

**Payload:**
```json
{
  "command_id": "web_1759741123_4",
  "status": "SUCCESS",  // or FAILED
  "message": "Command executed successfully",
  "data": {}  // Optional result data
}
```

#### `client_register` (Print Manager → Web App)

Print manager registers itself on connection.

**Payload:**
```json
{
  "client_type": "print_manager",
  "version": "1.0",
  "capabilities": ["pump_control", "printer_control", "material_change"]
}
```

---

## Hardware Integration

### I2C Motor Controllers

**Adafruit MotorKit Library:**

**Initialization:**
```python
from adafruit_motorkit import MotorKit

# First controller (0x60) - Pumps A, B
kit = MotorKit()

# Second controller (0x61) - Pumps C, D
kit2 = MotorKit(address=0x61)
```

**Stepper Motor Control:**
```python
from adafruit_motor import stepper

# Access stepper motor
motor = kit.stepper1  # or stepper2

# Step motor
for _ in range(200):  # 200 steps = 1 revolution
    motor.onestep(direction=stepper.FORWARD)
    time.sleep(0.005)  # 5ms step delay

# Release motor (reduces power consumption, prevents overheating)
motor.release()
```

**Troubleshooting I2C:**
```bash
# Check I2C enabled
sudo raspi-config
# Interface Options → I2C → Enable

# Detect I2C devices
i2cdetect -y 1
# Should show:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 60: 60 61 -- -- -- -- -- -- -- -- -- -- -- -- -- --
```

### GPIO Solenoid Control

**RPi.GPIO Library:**

**Setup:**
```python
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering
GPIO.setup(22, GPIO.OUT)  # Pin 22 as output
```

**Control:**
```python
# Activate (HIGH)
GPIO.output(22, GPIO.HIGH)

# Deactivate (LOW)
GPIO.output(22, GPIO.LOW)

# Read current state
state = GPIO.input(22)  # Returns 0 or 1
```

**Cleanup (important!):**
```python
# Always cleanup on exit
GPIO.cleanup()
# Or cleanup specific pin
GPIO.cleanup(22)
```

**Pin Reference:**
```
BCM Pin 22 = Physical Pin 15 (Header pin numbering)
```

### Printer WiFi Communication

**uart-wifi Protocol:**

The printer firmware exposes commands over TCP socket.

**Socket Communication:**
```python
import socket

def send_command(ip, port, command):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((ip, port))

    sock.send(command.encode())
    response = sock.recv(1024).decode()

    sock.close()
    return response

# Example: Get status
response = send_command('192.168.4.2', 6000, 'getstatus')
```

**Command Format:**
```
getstatus     → Returns: status,layer,total_layers,percent,...
gopause       → Returns: gopause,OK
goresume      → Returns: goresume,OK
gostop        → Returns: gostop,OK
getfile       → Returns: list of files on USB
```

**Status Response Parsing:**
```python
# Response format (comma-separated):
# status,current_layer,total_layers,percent,time,...
fields = response.split(',')

status = fields[0]           # 'print', 'pause', 'stop'
current_layer = int(fields[5])
total_layers = int(fields[6])
```

---

## Development Workflow

### Local Development

**Recommended Setup:**
- Development machine: Windows/Mac/Linux with Python 3.7+
- Code editor: VS Code with Python extension
- Git for version control
- SSH access to Raspberry Pi for testing

**Development Process:**

1. **Edit code locally** in preferred editor
2. **Commit changes** to Git
3. **Push to GitHub**
4. **Deploy to Pi** via SSH (see deployment commands above)
5. **Test on Pi** with real hardware
6. **Monitor logs** via SSH

### Testing Without Hardware

**Mock Printer:**

For testing without physical printer, mock `printer_comms.py`:

```python
# src/controller/printer_comms.py

MOCK_MODE = True  # Set to True for testing

def get_status(ip_address):
    if MOCK_MODE:
        return MonoXStatus(
            status='print',
            current_layer=42,
            total_layers=200,
            progress_percent=21.0,
            elapsed_seconds=930
        )
    else:
        # Real implementation
        ...
```

**Mock Pumps:**

Disable pump hardware in `photonmmu_pump.py`:

```python
MOCK_MODE = True

def run_stepper(pump_id, direction, duration):
    if MOCK_MODE:
        print(f"[MOCK] Pump {pump_id} {direction} for {duration}s")
        time.sleep(duration)
        return
    else:
        # Real implementation
        ...
```

### Adding New Features

**Example: Add new API endpoint for custom pump sequence**

1. **Add API endpoint** (`web-app/app.py`):
   ```python
   @app.route('/api/custom-sequence', methods=['POST'])
   def api_custom_sequence():
       data = request.json
       sequence_name = data.get('sequence_name')

       command_id = send_command_to_print_manager('custom_sequence', {
           'sequence_name': sequence_name
       })

       return jsonify({'success': True, 'command_id': command_id})
   ```

2. **Add command handler** (`src/controller/print_manager.py`):
   ```python
   def _process_shared_command(self, command):
       cmd_type = command.get("command")
       params = command.get("parameters", {})

       # ... existing handlers ...

       elif cmd_type == "custom_sequence":
           sequence_name = params.get("sequence_name")
           self._send_status_update("SEQUENCE", f"Starting {sequence_name}")

           # Execute custom sequence
           self._run_custom_sequence(sequence_name)

           self._send_status_update("SEQUENCE", f"{sequence_name} completed")
   ```

3. **Implement functionality** (`src/controller/print_manager.py`):
   ```python
   def _run_custom_sequence(self, sequence_name):
       if sequence_name == "clean_vat":
           # Drain → IPA rinse → Drain → Air dry
           mmu_control.run_pump('drain_pump', 'forward', 30)
           mmu_control.run_pump('pump_a', 'forward', 20)  # IPA
           mmu_control.run_pump('drain_pump', 'forward', 30)
           solenoid_control.activate_solenoid()
           time.sleep(15)
           solenoid_control.deactivate_solenoid()
   ```

4. **Add UI controls** (`web-app/templates/manual.html`):
   ```html
   <button onclick="runCustomSequence('clean_vat')">
       Clean Vat
   </button>

   <script>
   function runCustomSequence(name) {
       fetch('/api/custom-sequence', {
           method: 'POST',
           headers: {'Content-Type': 'application/json'},
           body: JSON.stringify({sequence_name: name})
       })
       .then(response => response.json())
       .then(data => {
           if (data.success) {
               showAlert('Sequence started', 'success');
           }
       });
   }
   </script>
   ```

5. **Test and deploy** (see deployment workflow above)

---

## Testing & Debugging

### Log Files

**Locations:**
```
web_app.log          # Flask app, HTTP requests, WebSocket events
print_manager.log    # Hardware operations, material changes, printer polling
```

**Monitoring Logs:**
```bash
# On Raspberry Pi
cd /home/pidlp/pidlp/multi-material-printer

# Watch both logs
tail -f web_app.log print_manager.log

# Search for errors
grep -i "error\|fail\|exception" *.log

# Filter by category
grep "MATERIAL" print_manager.log
grep "PUMP" print_manager.log
```

**Log Format:**
```
[TIMESTAMP] CATEGORY: Message
```

**Example:**
```
[1759741123.4] MATERIAL: Change #1: Layer 50 → Material A
[INFO] [PUMP] Starting Drain Pump - Direction: FORWARD, Duration: 10s
```

### Common Debugging Scenarios

#### WebSocket Not Connecting

**Symptoms:**
- Dashboard shows "Backend: Offline"
- No status updates

**Debug Steps:**
```bash
# Check print manager running
pgrep -f "print_manager.py"

# Check logs for connection errors
grep "connect" print_manager.log | tail -20

# Check web app listening
netstat -tlnp | grep 5000

# Test WebSocket from Python
cd src/controller
python3 -c "from websocket_ipc import WebSocketIPCClient; \
  client = WebSocketIPCClient('http://localhost:5000'); \
  client.connect(); \
  print('Connected' if client.connected else 'Failed')"
```

#### Material Change Not Triggering

**Debug Steps:**
```bash
# Check recipe active
grep "_recipe_active" print_manager.log | tail -5

# Check layer detection
grep "PROGRESS.*Layer.*reached" print_manager.log

# Check recipe loaded
grep "Successfully loaded" print_manager.log
```

**Expected Log Sequence:**
```
[INFO] Successfully loaded 3 material changes
[INFO] Layer range: 50 to 200
[1759741123.4] COMMAND: Recipe activated: /path/to/recipe.txt
...
[1759741456.7] PROGRESS: Layer 50 reached
[1759741456.7] MATERIAL: Change #1: Layer 50 → Material A
```

#### I2C / Pump Errors

**Debug Steps:**
```bash
# Check I2C devices detected
i2cdetect -y 1

# Check for I2C errors in logs
grep -i "i2c" print_manager.log | tail -20

# Test pump directly
cd src/controller
python3 mmu_control.py A F 5

# Check motor controller initialization
grep "MotorKit" print_manager.log
```

**Expected Initialization:**
```
[INFO] [I2C] Initializing MotorKit at default address 0x60...
[INFO] [I2C] ✓ MotorKit 0x60 initialized successfully
[INFO] [I2C] Controller 0x60 - PWM freq: 1600Hz, prescale: 3
```

### Unit Testing

**Test Individual Modules:**

```bash
# Test printer communications
cd src/controller
python3 -c "import printer_comms; \
  status = printer_comms.get_status('192.168.4.2'); \
  assert status.status in ['print', 'pause', 'stop'], 'Invalid status'; \
  print('✓ Printer comms OK')"

# Test pump control
python3 -c "import mmu_control; \
  controller = mmu_control.MMUController(); \
  success = controller.run_pump('pump_a', 'forward', 2); \
  assert success, 'Pump failed'; \
  print('✓ Pump control OK')"

# Test solenoid
python3 solenoid_control.py 2
# Verify: Should see "Test completed successfully"

# Test recipe parsing
python3 -c "from pathlib import Path; \
  import sys; \
  sys.path.insert(0, '../web-app'); \
  from app import parse_recipe; \
  recipe = parse_recipe('A,50:B,120'); \
  assert len(recipe) == 2; \
  assert recipe[0]['material'] == 'A'; \
  assert recipe[0]['layer'] == 50; \
  print('✓ Recipe parsing OK')"
```

### Integration Testing

**Test Full Material Change Sequence:**

```bash
# Start services
./start_services.sh

# Trigger material change via API
curl -X POST http://localhost:5000/api/sequence/material-change \
  -H "Content-Type: application/json" \
  -d '{"target_material": "A", "config": {"drain_time": 10, "fill_time": 10, "settle_time": 5}}'

# Monitor logs
tail -f print_manager.log | grep -E "MATERIAL|PUMP|SOLENOID|TIMING"
```

**Expected Output:**
```
[MATERIAL] Starting material change to A
[TIMING] Step 1: Pausing printer...
[TIMING] Step 2: Waiting for bed to reach raised position...
[TIMING] Step 3: Starting pump sequence...
[SOLENOID] ✓ Air valve OPENED
[PUMP] Starting Drain Pump - Direction: FORWARD, Duration: 10s
[PUMP] ✓ Drain Pump completed successfully
[SOLENOID] ✓ Air valve CLOSED
[PUMP] Starting Pump A - Direction: FORWARD, Duration: 10s
[PUMP] ✓ Pump A completed successfully
[TIMING] Step 4: Resuming printer...
[MATERIAL] ✓ Material change to A completed successfully
```

---

## Extending the System

### Adding New Pump

**Example: Add Pump E for support material**

1. **Hardware:**
   - Connect stepper motor to third MotorKit (I2C address 0x62)

2. **Update `photonmmu_pump.py`:**
   ```python
   kit3 = MotorKit(address=0x62)
   STEPPER_E = kit3.stepper1

   def run_stepper(pumpmat, direction, usr_time):
       # ... existing code ...
       elif pumpmat == 'E':
           stpr = STEPPER_E
           controller_addr = "0x62"
           stepper_num = 1
   ```

3. **Update `pump_profiles.json`:**
   ```json
   {
     "pumps": {
       "pump_e": {
         "name": "Pump E",
         "description": "Support material",
         "flow_rate_ml_per_second": 5.0,
         "max_volume_ml": 200
       }
     }
   }
   ```

4. **Update `mmu_control.py`:**
   ```python
   id_map = {
       "A": "pump_a",
       "B": "pump_b",
       "C": "pump_c",
       "D": "drain_pump",
       "E": "pump_e"  # Add new pump
   }
   ```

5. **Update UI** (`web-app/templates/manual.html`):
   ```html
   <option value="E">Pump E</option>
   ```

### Adding New Hardware Sensor

**Example: Add vat level sensor**

1. **Hardware:**
   - Connect analog sensor to ADC (e.g., ADS1115 via I2C)
   - Or use digital sensor on GPIO pin

2. **Create sensor module** (`src/controller/level_sensor.py`):
   ```python
   import RPi.GPIO as GPIO

   SENSOR_PIN = 23  # Example GPIO pin

   def init_sensor():
       GPIO.setmode(GPIO.BCM)
       GPIO.setup(SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

   def read_level():
       """Returns True if vat full, False if empty."""
       return GPIO.input(SENSOR_PIN) == GPIO.HIGH

   def wait_for_full(timeout=30):
       """Wait for vat to fill, with timeout."""
       import time
       start = time.time()
       while time.time() - start < timeout:
           if read_level():
               return True
           time.sleep(0.5)
       return False
   ```

3. **Integrate into material change** (`src/controller/print_manager.py`):
   ```python
   import level_sensor

   # In __init__:
   level_sensor.init_sensor()

   # In material change sequence:
   def _execute_material_change(self, layer, material):
       # ... drain ...
       # ... fill ...

       # Wait for vat to reach full level
       self._send_status_update("SENSOR", "Waiting for vat to fill...")
       if level_sensor.wait_for_full(timeout=30):
           self._send_status_update("SENSOR", "Vat full - proceeding")
       else:
           self._send_status_update("SENSOR", "Vat fill timeout - check pump", level="warning")

       # ... settle and resume ...
   ```

### Custom Logging

**Add custom log category:**

```python
# In print_manager.py

def _send_status_update(self, category, message, data=None, level="info"):
    """
    category: String identifier (e.g., PRINTER_STATUS, MATERIAL, CUSTOM_CATEGORY)
    message: Human-readable message
    data: Optional dict with structured data
    level: info, warning, error
    """
    # ... existing implementation ...
```

**Usage:**
```python
self._send_status_update(
    "CALIBRATION",  # Custom category
    "Pump A calibration: 5.2 ml/s measured vs 5.0 ml/s configured",
    data={"pump": "A", "measured_flow": 5.2, "configured_flow": 5.0},
    level="info"
)
```

**Receive in client:**
```javascript
socket.on('status_update', (data) => {
    if (data.category === 'CALIBRATION') {
        console.log('Calibration data:', data.data);
        updateCalibrationDisplay(data.data);
    }
});
```

---

## Appendix A: Service Management

### Systemd Service Files (Optional)

For automatic startup on boot, create systemd services:

**`/etc/systemd/system/scion-web-app.service`:**
```ini
[Unit]
Description=Scion Multi-Material Printer Web App
After=network.target

[Service]
Type=simple
User=pidlp
WorkingDirectory=/home/pidlp/pidlp/multi-material-printer
ExecStart=/usr/bin/python3 /home/pidlp/pidlp/multi-material-printer/web-app/app.py
Restart=always
RestartSec=10
StandardOutput=append:/home/pidlp/pidlp/multi-material-printer/web_app.log
StandardError=append:/home/pidlp/pidlp/multi-material-printer/web_app.log

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/scion-print-manager.service`:**
```ini
[Unit]
Description=Scion Multi-Material Printer Manager
After=network.target scion-web-app.service
Requires=scion-web-app.service

[Service]
Type=simple
User=pidlp
WorkingDirectory=/home/pidlp/pidlp/multi-material-printer/src/controller
ExecStart=/usr/bin/python3 /home/pidlp/pidlp/multi-material-printer/src/controller/print_manager.py
Restart=always
RestartSec=10
StandardOutput=append:/home/pidlp/pidlp/multi-material-printer/print_manager.log
StandardError=append:/home/pidlp/pidlp/multi-material-printer/print_manager.log

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable scion-web-app.service
sudo systemctl enable scion-print-manager.service
sudo systemctl start scion-web-app.service
sudo systemctl start scion-print-manager.service

# Check status
sudo systemctl status scion-web-app.service
sudo systemctl status scion-print-manager.service

# View logs
journalctl -u scion-web-app.service -f
journalctl -u scion-print-manager.service -f
```

---

## Appendix B: Network Configuration

### Raspberry Pi Network Setup

**Dual Network Configuration:**

Pi must connect to:
1. **Ethernet/WiFi** for web UI access (10.10.36.109)
2. **Printer WiFi** for printer communication (192.168.4.x network)

**Option 1: USB WiFi Adapter (Recommended)**
- Primary network: Ethernet (10.10.36.109)
- Secondary network: USB WiFi adapter (connect to printer's PHOTON-WIFI network)

**Option 2: WiFi + Ethernet**
- Primary network: WiFi (10.10.36.109)
- Secondary network: Ethernet (bridge to printer network)

**Configure USB WiFi:**
```bash
# List network interfaces
ip addr show

# Identify USB WiFi interface (e.g., wlan1)
# Edit /etc/wpa_supplicant/wpa_supplicant-wlan1.conf
sudo nano /etc/wpa_supplicant/wpa_supplicant-wlan1.conf
```

Add printer WiFi network:
```
network={
    ssid="PHOTON-WIFI"
    psk="printer_password"
    priority=1
}
```

Enable interface:
```bash
sudo systemctl enable wpa_supplicant@wlan1
sudo systemctl start wpa_supplicant@wlan1
```

Verify printer reachable:
```bash
ping 192.168.4.2
```

---

## Appendix C: Troubleshooting Reference

### Quick Diagnostics

```bash
# Check services running
pgrep -f "app.py" && echo "✓ Web app running" || echo "✗ Web app stopped"
pgrep -f "print_manager.py" && echo "✓ Print manager running" || echo "✗ Print manager stopped"

# Check network connectivity
ping -c 1 192.168.4.2 && echo "✓ Printer reachable" || echo "✗ Printer unreachable"

# Check I2C devices
i2cdetect -y 1 | grep -q "60" && echo "✓ I2C controller 0x60 detected" || echo "✗ Missing 0x60"
i2cdetect -y 1 | grep -q "61" && echo "✓ I2C controller 0x61 detected" || echo "✗ Missing 0x61"

# Check GPIO available
python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.setup(22, GPIO.OUT); GPIO.cleanup(); print('✓ GPIO OK')"

# Check recent errors
grep -i "error\|exception\|failed" print_manager.log web_app.log | tail -10
```

### Error Code Reference

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Connection refused` | Web app not running | Start services: `./start_services.sh` |
| `I2C address 0x60 not found` | Motor controller disconnected | Check I2C connections, power |
| `Print manager not connected` | WebSocket not established | Restart services, check logs |
| `Printer disconnected` | Cannot reach printer | Check printer power, network |
| `HTTPConnectionPool... Max retries` | Network timeout | Check printer IP, network connectivity |
| `[Errno 20] Not a directory` | Config file path error | Check config file paths in code |
| `Could not load pump config` | JSON syntax error | Validate `pump_profiles.json` syntax |

---

## Document Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | October 2025 | Initial release |

---

**For user-focused documentation, see [OPERATING_MANUAL.md](OPERATING_MANUAL.md)**
