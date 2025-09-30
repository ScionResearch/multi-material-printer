#!/usr/bin/env python3
"""
Scion Multi-Material Printer Web Interface

A modern Flask-based web application to replace the Qt GUI with a user-friendly
web interface for recipe creation, print monitoring, and system control.

Features:
- Visual recipe builder with form validation
- Real-time print status monitoring
- Manual pump and printer controls
- Mobile-responsive design
- WebSocket support for live updates

Author: Claude Code Assistant
License: MIT
"""

import os
import sys
import json
import threading
import time
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
import subprocess  # TODO: remove if no longer needed after full refactor (left temporarily for any remaining usage)

# Add the controller modules to the Python path
sys.path.append(str(Path(__file__).parent.parent / 'src' / 'controller'))

# Import existing controller modules
try:
    import printer_comms, mmu_control, photonmmu_pump
    CONTROLLERS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import controller modules: {e}")
    print("Make sure you're running from the Raspberry Pi with the controller modules installed")
    CONTROLLERS_AVAILABLE = False

# WebSocket-based IPC replaces file-based shared_status
# Status and commands are now handled via SocketIO events
print("Using WebSocket-based IPC system (shared_status deprecated)")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'scion-mmu-controller-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# Global variables for application state
current_status = {
    'printer_connected': False,
    'printer_status': 'Unknown',
    'current_layer': 0,
    'total_layers': 0,
    'progress_percent': 0,
    'current_material': 'None',
    'next_material': 'None',
    'next_change_layer': 0,
    'mm_active': False,
    'last_update': datetime.now().isoformat(),
    # Enhanced timing and progress tracking
    'current_operation': 'idle',
    'operation_start_time': None,
    'operation_duration': 0,
    'estimated_completion': None,
    'pump_status': {
        'pump_a': 'idle',
        'pump_b': 'idle',
        'pump_c': 'idle',
        'drain_pump': 'idle'
    },
    'sequence_progress': {
        'current_step': 0,
        'total_steps': 0,
        'step_name': '',
        'step_progress': 0
    }
}

status_monitor_thread = None  # deprecated (will be removed)
status_monitor_running = False  # deprecated

def get_config_path():
    """Get the configuration directory path"""
    return Path(__file__).parent.parent / 'config'

def get_recipe_path():
    """Get the recipe file path"""
    return get_config_path() / 'recipe.txt'

def load_recipe():
    """Load the current recipe from file"""
    recipe_file = get_recipe_path()
    if recipe_file.exists():
        try:
            with open(recipe_file, 'r') as f:
                recipe_text = f.read().strip()
                if recipe_text:
                    return parse_recipe(recipe_text)
        except Exception as e:
            print(f"Error loading recipe: {e}")
    return []

def load_pump_config():
    """Load pump configuration from JSON file"""
    config_file = get_config_path() / 'pump_profiles.json'
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading pump config: {e}")
    return get_default_pump_config()

def load_network_config():
    """Load network configuration from INI file"""
    config_file = get_config_path() / 'network_settings.ini'
    config = {
        'printer_ip': '192.168.4.3',
        'printer_port': 8080,
        'wifi_ssid': '',
        'connection_timeout': 10
    }

    if config_file.exists():
        try:
            import configparser
            parser = configparser.ConfigParser()
            parser.read(config_file)

            if 'printer' in parser:
                config['printer_ip'] = parser.get('printer', 'ip_address', fallback=config['printer_ip'])
                config['printer_port'] = parser.getint('printer', 'port', fallback=config['printer_port'])
                config['connection_timeout'] = parser.getint('printer', 'timeout', fallback=config['connection_timeout'])

            if 'network' in parser:
                config['wifi_ssid'] = parser.get('network', 'ssid', fallback=config['wifi_ssid'])
        except Exception as e:
            print(f"Error loading network config: {e}")

    return config

def get_default_pump_config():
    """Get default pump configuration"""
    return {
        "pumps": {
            "pump_a": {
                "name": "Pump A",
                "description": "Primary material pump",
                "gpio_pin": 18,
                "flow_rate_ml_per_second": 2.5,
                "max_volume_ml": 500,
                "calibration": {"steps_per_ml": 100, "last_calibrated": None}
            },
            "pump_b": {
                "name": "Pump B",
                "description": "Secondary material pump",
                "gpio_pin": 19,
                "flow_rate_ml_per_second": 2.5,
                "max_volume_ml": 500,
                "calibration": {"steps_per_ml": 100, "last_calibrated": None}
            },
            "pump_c": {
                "name": "Pump C",
                "description": "Third material pump",
                "gpio_pin": 21,
                "flow_rate_ml_per_second": 2.5,
                "max_volume_ml": 500,
                "calibration": {"steps_per_ml": 100, "last_calibrated": None}
            },
            "drain_pump": {
                "name": "Drain Pump",
                "description": "Vat drainage pump",
                "gpio_pin": 20,
                "flow_rate_ml_per_second": 5.0,
                "max_volume_ml": 1000,
                "calibration": {"steps_per_ml": 80, "last_calibrated": None}
            }
        },
        "material_change": {
            "drain_volume_ml": 50,
            "fill_volume_ml": 45,
            "mixing_time_seconds": 10,
            "settle_time_seconds": 5
        },
        "safety": {
            "max_pump_runtime_seconds": 300,
            "emergency_stop_enabled": True,
            "sensor_check_interval_seconds": 1
        },
        "maintenance": {
            "pump_cycle_count": {"pump_a": 0, "pump_b": 0, "pump_c": 0, "drain_pump": 0},
            "last_maintenance_date": None,
            "maintenance_interval_cycles": 1000
        }
    }

def parse_recipe(recipe_text):
    """Parse recipe text format (A,50:B,120:C,200) into structured data"""
    recipe = []
    if not recipe_text:
        return recipe

    try:
        entries = recipe_text.split(':')
        for entry in entries:
            if ',' in entry:
                material, layer = entry.split(',', 1)
                recipe.append({
                    'material': material.strip(),
                    'layer': int(layer.strip())
                })
    except Exception as e:
        print(f"Error parsing recipe: {e}")

    return sorted(recipe, key=lambda x: x['layer'])

def save_recipe(recipe_data):
    """Save recipe data to file in the expected format"""
    recipe_file = get_recipe_path()
    try:
        # Convert structured data back to text format
        recipe_text = ':'.join([f"{item['material']},{item['layer']}" for item in recipe_data])
        with open(recipe_file, 'w') as f:
            f.write(recipe_text)
        return True
    except Exception as e:
        print(f"Error saving recipe: {e}")
        return False

def get_printer_status():
    """Deprecated: Printer status now pushed from print_manager via WebSocket."""
    return None

def parse_printer_status(status_text):
    """Parse printer status response into structured data"""
    status = {
        'connected': True,
        'state': 'Unknown',
        'layer': 0,
        'progress': 0
    }

    if not status_text:
        status['connected'] = False
        return status

    # Handle both object and string responses
    if hasattr(status_text, 'status'):
        # Handle MonoXStatus object directly
        status['state'] = getattr(status_text, 'status', 'Unknown')
        status['layer'] = getattr(status_text, 'current_layer', 0)
        status['progress'] = getattr(status_text, 'percent_complete', 0)
    else:
        # Parse string format
        lines = str(status_text).strip().split('\n')
        for line in lines:
            line = line.strip().lower()
            if 'status:' in line:
                status['state'] = line.split(':', 1)[1].strip()
            elif any(x in line for x in ['current_layer:', 'current_lay:', 'layer:']):
                try:
                    import re
                    match = re.search(r'(\d+)', line)
                    if match:
                        status['layer'] = int(match.group(1))
                except ValueError:
                    pass
            elif 'percent' in line:
                try:
                    import re
                    match = re.search(r'(\d+(?:\.\d+)?)', line)
                    if match:
                        status['progress'] = float(match.group(1))
                except ValueError:
                    pass

    return status

def status_monitor():  # deprecated
    return

@app.route('/')
def index():
    """Main dashboard page"""
    recipe = load_recipe()
    return render_template('index.html',
                         status=current_status,
                         recipe=recipe)

@app.route('/recipe')
def recipe_page():
    """Recipe builder page"""
    recipe = load_recipe()
    return render_template('recipe.html', recipe=recipe)

@app.route('/manual')
def manual_page():
    """Manual controls page"""
    return render_template('manual.html', status=current_status)

@app.route('/config')
def config_page():
    """Configuration management page"""
    pump_config = load_pump_config()
    network_config = load_network_config()
    return render_template('config.html',
                         pump_config=pump_config,
                         network_config=network_config)

@app.route('/api/recipe', methods=['POST'])
def api_save_recipe():
    """API endpoint to save recipe"""
    try:
        recipe_data = request.json
        if save_recipe(recipe_data):
            return jsonify({'success': True, 'message': 'Recipe saved successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to save recipe'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/recipe', methods=['GET'])
def api_get_recipe():
    """API endpoint to get current recipe"""
    recipe = load_recipe()
    return jsonify(recipe)

@app.route('/api/status')
def api_status():
    """API endpoint to get current status"""
    return jsonify(current_status)

@app.route('/api/printer/<action>', methods=['POST'])
def api_printer_control(action):
    """API endpoint for printer control commands (delegated)."""
    valid = {'pause': 'pause_print', 'resume': 'resume_print', 'stop': 'stop_print'}
    if action not in valid:
        return jsonify({'success': False, 'message': 'Invalid action'}), 400

    command_id = send_command_to_print_manager(valid[action], {})
    if not command_id:
        return jsonify({'success': False, 'message': 'Print manager not connected'}), 503

    return jsonify({'success': True, 'action': action, 'command_id': command_id})

@app.route('/api/pump', methods=['POST'])
def api_pump_control():
    """API endpoint for manual pump control"""
    try:
        data = request.json
        motor = data.get('motor', '').upper()
        direction = data.get('direction', '').upper()
        duration = int(data.get('duration', 0))

        # Validate input
        if motor not in ['A', 'B', 'C', 'D']:
            return jsonify({'success': False, 'message': 'Invalid motor (must be A, B, C, or D)'}), 400

        if direction not in ['F', 'R']:
            return jsonify({'success': False, 'message': 'Invalid direction (must be F or R)'}), 400

        if duration <= 0 or duration > 300:  # Max 5 minutes
            return jsonify({'success': False, 'message': 'Invalid duration (1-300 seconds)'}), 400

        # Use new WebSocket communication for pump control
        command_id = send_command_to_print_manager('pump_control', {
            'motor': motor,
            'direction': direction,
            'duration': duration
        })

        if not command_id:
            return jsonify({'success': False, 'message': 'Print manager not connected'}), 503

        return jsonify({
            'success': True,
            'message': f'Pump {motor} command sent ({direction} for {duration}s)',
            'command_id': command_id
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/multi-material/start', methods=['POST'])
def api_start_multi_material():
    """API endpoint to start multi-material printing"""
    try:
        recipe_path = get_recipe_path()
        if not recipe_path.exists():
            return jsonify({'success': False, 'message': 'No recipe file found'}), 400

        # Use new WebSocket communication instead of file-based shared_status
        command_id = send_command_to_print_manager('start_multi_material', {
            'recipe_path': str(recipe_path)
        })

        if not command_id:
            return jsonify({'success': False, 'message': 'Print manager not connected'}), 503

        return jsonify({
            'success': True,
            'message': 'Multi-material printing start requested',
            'command_id': command_id
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/multi-material/stop', methods=['POST'])
def api_stop_multi_material():
    """API endpoint to stop multi-material printing"""
    try:
        command_id = send_command_to_print_manager('stop_multi_material', {})
        if not command_id:
            return jsonify({'success': False, 'message': 'Print manager not connected'}), 503
        return jsonify({'success': True, 'message': 'Stop requested', 'command_id': command_id})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/sequence/material-change', methods=['POST'])
def api_material_change_sequence():
    """API endpoint to run complete material change sequence"""
    try:
        data = request.json or {}
        target_material = data.get('target_material')
        sequence_config = data.get('config', {})

        if not target_material:
            return jsonify({'success': False, 'message': 'Target material is required'}), 400

        if target_material not in ['A', 'B', 'C', 'D']:
            return jsonify({'success': False, 'message': 'Invalid target material'}), 400

        # Use helper to ensure print manager connection and consistent command handling
        command_id = send_command_to_print_manager('run_material_change', {
            'target_material': target_material,
            'drain_time': sequence_config.get('drain_time', 30),
            'fill_time': sequence_config.get('fill_time', 25),
            'mix_time': sequence_config.get('mix_time', 10),
            'settle_time': sequence_config.get('settle_time', 5)
        })

        if not command_id:
            return jsonify({'success': False, 'message': 'Print manager not connected'}), 503

        return jsonify({
            'success': True,
            'message': f'Material change sequence to {target_material} started',
            'command_id': command_id
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/emergency-stop', methods=['POST'])
def api_emergency_stop():
    """API endpoint for emergency stop"""
    try:
        # Use shared command system for emergency stop
        # Send emergency stop command via WebSocket to print manager
        command_data = {
            'type': 'emergency_stop',
            'parameters': {},
            'timestamp': datetime.now().isoformat()
        }
        socketio.emit('command', command_data)

        socketio.emit('system_alert', {
            'message': 'Emergency stop activated',
            'type': 'danger'
        })

        return jsonify({'success': True, 'message': 'Emergency stop activated'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/config/pump', methods=['GET'])
def api_get_pump_config():
    """API endpoint to get pump configuration"""
    try:
        config = load_pump_config()
        return jsonify(config)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/config/pump', methods=['POST'])
def api_save_pump_config():
    """API endpoint to save pump configuration"""
    try:
        config_data = request.json or {}
        config_file = get_config_path() / 'pump_profiles.json'

        # Validate configuration structure
        if not validate_pump_config(config_data):
            return jsonify({'success': False, 'message': 'Invalid pump configuration format'}), 400

        # Create backup
        backup_file = get_config_path() / f'pump_profiles_backup_{int(time.time())}.json'
        if config_file.exists():
            import shutil
            shutil.copy2(config_file, backup_file)

        # Save new configuration
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)

        socketio.emit('system_alert', {
            'message': 'Pump configuration saved successfully',
            'type': 'success'
        })

        return jsonify({'success': True, 'message': 'Pump configuration saved successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/config/network', methods=['GET'])
def api_get_network_config():
    """API endpoint to get network configuration"""
    try:
        config = load_network_config()
        return jsonify(config)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/config/network', methods=['POST'])
def api_save_network_config():
    """API endpoint to save network configuration"""
    try:
        config_data = request.json or {}
        config_file = get_config_path() / 'network_settings.ini'

        # Create backup
        backup_file = get_config_path() / f'network_settings_backup_{int(time.time())}.ini'
        if config_file.exists():
            import shutil
            shutil.copy2(config_file, backup_file)

        # Create INI configuration
        import configparser
        parser = configparser.ConfigParser()

        parser['printer'] = {
            'ip_address': config_data.get('printer_ip', '192.168.4.3'),
            'port': str(config_data.get('printer_port', 8080)),
            'timeout': str(config_data.get('connection_timeout', 10))
        }

        parser['network'] = {
            'ssid': config_data.get('wifi_ssid', '')
        }

        # Save configuration
        with open(config_file, 'w') as f:
            parser.write(f)

        socketio.emit('system_alert', {
            'message': 'Network configuration saved successfully',
            'type': 'success'
        })

        return jsonify({'success': True, 'message': 'Network configuration saved successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/config/test-connection', methods=['POST'])
def api_test_connection():
    """API endpoint to test printer connection"""
    try:
        if not CONTROLLERS_AVAILABLE:
            return jsonify({'success': False, 'message': 'Controller modules not available'}), 503

        # Get printer IP from request or config
        printer_ip = request.json.get('printer_ip') if request.json else None
        if not printer_ip:
            network_config = load_network_config()
            printer_ip = network_config['printer_ip']

        # Test connection using printer_comms module
        # Create a communicator instance and test the connection
        from printer_comms import PrinterCommunicator
        communicator = PrinterCommunicator()

        # Try to get status as a connection test
        try:
            status = communicator.get_status()
            result = status is not None

            # Parse the status string (e.g., "status: stop")
            if status and isinstance(status, str):
                # Extract status from string like "status: stop"
                if ':' in status:
                    status_value = status.split(':', 1)[1].strip()
                else:
                    status_value = status.strip()
                connection_details = f"Printer status: {status_value}"
            else:
                connection_details = f"Raw response: {status}" if status else "No response"
        except Exception as conn_err:
            result = False
            connection_details = str(conn_err)

        return jsonify({
            'success': result,
            'message': f'Connection {"successful" if result else "failed"}: {connection_details}',
            'ip': printer_ip
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/printer/files', methods=['GET'])
def api_get_printer_files():
    """API endpoint to get list of print files from printer"""
    try:
        if not CONTROLLERS_AVAILABLE:
            return jsonify({'success': False, 'message': 'Controller modules not available'}), 503

        # Get printer files using printer_comms module
        from printer_comms import PrinterCommunicator
        communicator = PrinterCommunicator()

        files = communicator.get_files()
        return jsonify({
            'success': True,
            'files': files,
            'count': len(files)
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/printer/start-print', methods=['POST'])
def api_start_printer_print():
    """API endpoint to start printing a file on the printer"""
    try:
        data = request.json or {}
        filename = data.get('filename')
        if not filename:
            return jsonify({'success': False, 'message': 'Filename is required'}), 400
        command_id = send_command_to_print_manager('start_printer_print', {'filename': filename})
        if not command_id:
            return jsonify({'success': False, 'message': 'Print manager not connected'}), 503
        return jsonify({'success': True, 'message': f'Print start requested: {filename}', 'command_id': command_id})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/logging/config', methods=['GET'])
def api_get_logging_config():
    """API endpoint to get logging configuration"""
    try:
        # Try to get config from logging_config module
        if 'logging_config' in sys.modules:
            config = sys.modules['logging_config'].get_logging_config()
            return jsonify(config)
        else:
            # Return default config
            return jsonify({
                'levels': {
                    'print_manager': 'INFO',
                    'mmu_control': 'INFO',
                    'pump_control': 'INFO',
                    'printer_comms': 'INFO',
                    'web_interface': 'INFO'
                },
                'outputs': {
                    'console': True,
                    'file': False,
                    'web_stream': True
                }
            })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/logging/config', methods=['POST'])
def api_save_logging_config():
    """API endpoint to save logging configuration"""
    try:
        config_data = request.json

        # Try to update logging configuration
        if 'logging_config' in sys.modules:
            sys.modules['logging_config'].configure_logging(config_data)

        # Also store in session for immediate use
        socketio.emit('system_alert', {
            'message': 'Logging configuration updated',
            'type': 'success'
        })

        return jsonify({'success': True, 'message': 'Logging configuration saved'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/logging/recent', methods=['GET'])
def api_get_recent_logs():
    """API endpoint to get recent log entries"""
    try:
        count = request.args.get('count', 100, type=int)

        if 'logging_config' in sys.modules:
            logs = sys.modules['logging_config'].get_recent_logs(count)
            return jsonify(logs)
        else:
            # Return sample logs if logging module not available
            return jsonify([
                {
                    'timestamp': datetime.now().isoformat(),
                    'level': 'INFO',
                    'logger': 'web_interface',
                    'message': 'Web interface initialized'
                }
            ])
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/logging/level', methods=['POST'])
def api_set_log_level():
    """API endpoint to change log level for a component"""
    try:
        data = request.json or {}
        component = data.get('component')
        level = data.get('level')

        if not component or not level:
            return jsonify({'success': False, 'message': 'Component and level required'}), 400

        if 'logging_config' in sys.modules:
            sys.modules['logging_config'].set_log_level(component, level)

        socketio.emit('log_message', {
            'level': 'info',
            'message': f'Log level for {component} changed to {level}',
            'timestamp': datetime.now().isoformat()
        })

        return jsonify({'success': True, 'message': f'Log level updated for {component}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

def validate_pump_config(config):
    """Validate pump configuration structure"""
    try:
        required_keys = ['pumps', 'material_change', 'safety', 'maintenance']
        if not all(key in config for key in required_keys):
            return False

        # Validate pump entries
        for pump_id, pump_data in config['pumps'].items():
            required_pump_keys = ['name', 'description', 'gpio_pin', 'flow_rate_ml_per_second', 'max_volume_ml', 'calibration']
            if not all(key in pump_data for key in required_pump_keys):
                return False

            # Validate data types
            if not isinstance(pump_data['gpio_pin'], int):
                return False
            if not isinstance(pump_data['flow_rate_ml_per_second'], (int, float)):
                return False
            if not isinstance(pump_data['max_volume_ml'], (int, float)):
                return False

        return True
    except Exception:
        return False

def setup_logging_integration():
    """Setup integration with controller logging system"""
    try:
        # Import logging configuration module
        sys.path.append(str(Path(__file__).parent.parent / 'src' / 'controller'))
        import logging_config

        # Set up web callback for real-time log streaming AND console mirroring
        def web_log_callback(level, message):
            # Print to console with color coding
            timestamp = datetime.now().strftime('%H:%M:%S')
            level_colors = {
                'debug': '\033[36m',    # Cyan
                'info': '\033[32m',     # Green
                'warning': '\033[33m',  # Yellow
                'error': '\033[31m',    # Red
                'critical': '\033[35m'  # Magenta
            }
            reset = '\033[0m'
            color = level_colors.get(level.lower(), '')

            # Print to console
            print(f"{color}[{timestamp}] {level.upper()}: {message}{reset}")

            # Emit to web interface
            socketio.emit('log_message', {
                'level': level,
                'message': message,
                'timestamp': datetime.now().isoformat()
            })

        logging_config.set_web_callback(web_log_callback)

        # Also setup a logger for the web interface itself
        web_logger = logging_config.setup_logging('web_interface', level='INFO')
        web_logger.info("Web interface logging initialized")

        return True
    except Exception as e:
        print(f"Could not setup logging integration: {e}")
        return False

# Diagnostic and Calibration API Endpoints

@app.route('/api/diagnostics/i2c', methods=['POST'])
def api_test_i2c():
    """API endpoint to test I2C communication with motor controllers"""
    try:
        command_id = send_command_to_print_manager('test_i2c', {})
        if command_id:
            return jsonify({'success': True, 'message': 'I2C test initiated', 'command_id': command_id})
        else:
            return jsonify({'success': False, 'message': 'Print manager not connected'}), 503
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/diagnostics/gpio', methods=['POST'])
def api_test_gpio():
    """API endpoint to test GPIO pin accessibility"""
    try:
        command_id = send_command_to_print_manager('test_gpio', {})
        if command_id:
            return jsonify({'success': True, 'message': 'GPIO test initiated', 'command_id': command_id})
        else:
            return jsonify({'success': False, 'message': 'Print manager not connected'}), 503
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/diagnostics/pumps', methods=['POST'])
def api_test_pump_motors():
    """API endpoint to test all pump motor connectivity"""
    try:
        command_id = send_command_to_print_manager('test_pump_motors', {})
        if command_id:
            return jsonify({'success': True, 'message': 'Pump motor test initiated', 'command_id': command_id})
        else:
            return jsonify({'success': False, 'message': 'Print manager not connected'}), 503
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/diagnostics/full', methods=['POST'])
def api_run_full_diagnostics():
    """API endpoint to run comprehensive system diagnostics"""
    try:
        command_id = send_command_to_print_manager('run_full_diagnostics', {})
        if command_id:
            return jsonify({'success': True, 'message': 'Full diagnostics initiated', 'command_id': command_id})
        else:
            return jsonify({'success': False, 'message': 'Print manager not connected'}), 503
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/calibration/pumps', methods=['POST'])
def api_calibrate_pumps():
    """API endpoint to start pump calibration wizard"""
    try:
        data = request.json or {}
        command_id = send_command_to_print_manager('calibrate_pumps', data)
        if command_id:
            return jsonify({'success': True, 'message': 'Pump calibration started', 'command_id': command_id})
        else:
            return jsonify({'success': False, 'message': 'Print manager not connected'}), 503
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/calibration/pump/<pump_id>', methods=['POST'])
def api_calibrate_single_pump(pump_id):
    """API endpoint to calibrate a specific pump"""
    try:
        data = request.json or {}
        data['pump_id'] = pump_id
        command_id = send_command_to_print_manager('calibrate_single_pump', data)
        if command_id:
            return jsonify({'success': True, 'message': f'Calibration started for pump {pump_id}', 'command_id': command_id})
        else:
            return jsonify({'success': False, 'message': 'Print manager not connected'}), 503
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Global tracking for connected clients
connected_clients = {
    'print_manager': None,
    'web_clients': set()
}

@socketio.on('connect')
def handle_connect():
    """Handle client connection for WebSocket"""
    # Flask-SocketIO provides request.sid at runtime; ignore static type checker
    sid = getattr(request, 'sid', None)  # type: ignore[attr-defined]
    if sid:
        print(f'Client connected: {sid}')
        connected_clients['web_clients'].add(sid)
    emit('status_update', current_status)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    sid = getattr(request, 'sid', None)  # type: ignore[attr-defined]
    if sid:
        print(f'Client disconnected: {sid}')
        connected_clients['web_clients'].discard(sid)
        if connected_clients['print_manager'] == sid:
            connected_clients['print_manager'] = None
            print('Print manager disconnected')
            emit('system_status', {
                'print_manager_connected': False,
                'timestamp': datetime.now().isoformat()
            }, broadcast=True)

@socketio.on('client_register')
def handle_client_register(data):
    """Handle client registration (print manager identification)"""
    print(f"[DEBUG] client_register event received! Data: {data}")
    client_type = data.get('client_type') if isinstance(data, dict) else None
    sid = getattr(request, 'sid', None)  # type: ignore[attr-defined]
    print(f"Client registration: {client_type} from {sid}")

    if client_type == 'print_manager' and sid:
        connected_clients['print_manager'] = sid
        print('Print manager registered and connected')
        emit('system_status', {
            'print_manager_connected': True,
            'timestamp': datetime.now().isoformat()
        }, broadcast=True)

@socketio.on('command_result')
def handle_command_result(data):
    """Handle command result from print manager"""
    command_id = data.get('command_id')
    success = data.get('success')
    result = data.get('result', '')

    print(f"Command {command_id} result: {'SUCCESS' if success else 'FAILED'} - {result}")

    # Broadcast result to web clients
    emit('command_completed', {
        'command_id': command_id,
        'success': success,
        'result': result,
        'timestamp': datetime.now().isoformat()
    }, broadcast=True, include_self=False)

@socketio.on('status_update')
def handle_status_update_from_manager(data):
    """Handle status updates from print manager"""
    component = data.get('component', 'UNKNOWN')
    status = data.get('status', '')
    level = data.get('level', 'info')
    timestamp = data.get('timestamp', datetime.now().isoformat())

    print(f"[{component}] {status}")

    # Update global status cache
    global current_status
    current_status[component.lower()] = {
        'status': status,
        'level': level,
        'timestamp': timestamp,
        'data': data.get('data', {})
    }

    # Broadcast to web clients
    emit('status_update', {
        'component': component,
        'status': status,
        'level': level,
        'timestamp': timestamp,
        'data': data.get('data', {})
    }, broadcast=True, include_self=False)

@socketio.on('log_message')
def handle_log_message_from_manager(data):
    """Handle log messages from print manager"""
    level = data.get('level', 'info')
    message = data.get('message', '')
    component = data.get('component', 'SYSTEM')
    timestamp = data.get('timestamp', datetime.now().isoformat())

    # Broadcast to web clients
    emit('log_message', {
        'level': level,
        'message': message,
        'component': component,
        'timestamp': timestamp
    }, broadcast=True, include_self=False)

def send_command_to_print_manager(command_type, parameters=None, command_id=None):
    """
    Send command to print manager via WebSocket.

    This replaces the old shared_status file-based communication.
    """
    if not connected_clients['print_manager']:
        print("Warning: Print manager not connected, cannot send command")
        return None

    if command_id is None:
        command_id = f"web_{int(time.time())}_{len(connected_clients['web_clients'])}"

    command_data = {
        'command_id': command_id,
        'type': command_type,
        'parameters': parameters or {},
        'timestamp': datetime.now().isoformat()
    }

    print(f"Sending command to print manager: {command_type}")

    # Send command directly to print manager client
    socketio.emit('command', command_data, to=connected_clients['print_manager'])

    return command_id

def start_status_monitor():  # deprecated
    pass

def stop_status_monitor():  # deprecated
    pass


if __name__ == '__main__':
    print("Scion Multi-Material Printer Web Interface")
    print("==========================================")
    print(f"Controllers available: {CONTROLLERS_AVAILABLE}")
    print(f"Config path: {get_config_path()}")
    print(f"Recipe path: {get_recipe_path()}")

    # Setup logging integration
    logging_available = setup_logging_integration()
    print(f"Logging integration: {'enabled' if logging_available else 'disabled'}")

    print("Expecting external persistent print_manager service (no auto-spawn).")

    try:
        # Run the Flask application
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)  # Debug mode disabled to fix event handler registration
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        stop_status_monitor()