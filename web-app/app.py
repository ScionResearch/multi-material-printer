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
import subprocess

# Add the controller modules to the Python path
sys.path.append(str(Path(__file__).parent.parent / 'src' / 'controller'))

# Import existing controller modules
try:
    import printer_comms
    import mmu_control
    import photonmmu_pump
    CONTROLLERS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import controller modules: {e}")
    print("Make sure you're running from the Raspberry Pi with the controller modules installed")
    CONTROLLERS_AVAILABLE = False

# Import shared status system
try:
    from shared_status import get_shared_status
    shared_status = get_shared_status()
    print("Shared status system initialized")
except ImportError as e:
    print(f"Warning: Could not import shared_status: {e}")
    shared_status = None

app = Flask(__name__)
app.config['SECRET_KEY'] = 'scion-mmu-controller-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

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

status_monitor_thread = None
status_monitor_running = False

# Simple process tracking
active_processes = {}
import atexit

def cleanup_processes():
    """Clean up any running processes on shutdown"""
    for name, process in active_processes.items():
        if process and process.poll() is None:
            print(f"Terminating {name} process...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

atexit.register(cleanup_processes)

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
    """Get current printer status using existing controller"""
    if not CONTROLLERS_AVAILABLE:
        return None

    try:
        # Use existing printer communications module
        status_response = printer_comms.get_status()
        if status_response:
            # Parse the status response (this will need adjustment based on actual format)
            return parse_printer_status(status_response)
    except Exception as e:
        print(f"Error getting printer status: {e}")

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

    # Parse status text - adapt based on actual uart-wifi response format
    lines = status_text.strip().split('\n')
    for line in lines:
        line = line.strip().lower()
        if 'status:' in line:
            status['state'] = line.split(':', 1)[1].strip()
        elif 'current_layer:' in line:
            try:
                status['layer'] = int(line.split(':', 1)[1].strip())
            except ValueError:
                pass
        elif 'percent_complete:' in line:
            try:
                status['progress'] = float(line.split(':', 1)[1].strip())
            except ValueError:
                pass

    return status

def status_monitor():
    """Background thread to monitor printer status from shared files"""
    global status_monitor_running, current_status

    while status_monitor_running:
        try:
            if shared_status:
                # Read all status from shared files
                all_status = shared_status.get_all_status()

                # Update current_status with shared file data
                printer_status = all_status.get('printer', {})
                pump_status = all_status.get('pumps', {})
                recipe_status = all_status.get('recipe', {})

                current_status.update({
                    'printer_connected': printer_status.get('printer_connected', False),
                    'printer_status': printer_status.get('printer_status', 'Unknown'),
                    'current_layer': printer_status.get('current_layer', 0),
                    'total_layers': printer_status.get('total_layers', 0),
                    'progress_percent': printer_status.get('progress_percent', 0.0),
                    'current_material': recipe_status.get('current_material', 'None'),
                    'next_material': recipe_status.get('next_material', 'None'),
                    'next_change_layer': recipe_status.get('next_change_layer', 0),
                    'mm_active': recipe_status.get('recipe_active', False),
                    'last_update': all_status.get('last_update', datetime.now().isoformat()),
                    'current_operation': pump_status.get('current_operation', 'idle'),
                    'operation_start_time': recipe_status.get('operation_start_time'),
                    'operation_duration': recipe_status.get('operation_duration', 0),
                    'estimated_completion': recipe_status.get('estimated_completion'),
                    'pump_status': {
                        'pump_a': pump_status.get('pump_a', {}).get('status', 'idle'),
                        'pump_b': pump_status.get('pump_b', {}).get('status', 'idle'),
                        'pump_c': pump_status.get('pump_c', {}).get('status', 'idle'),
                        'drain_pump': pump_status.get('drain_pump', {}).get('status', 'idle')
                    },
                    'sequence_progress': {
                        'current_step': recipe_status.get('current_step', 0),
                        'total_steps': recipe_status.get('total_steps', 0),
                        'step_name': pump_status.get('operation_step', ''),
                        'step_progress': pump_status.get('step_progress', 0)
                    }
                })

                # Emit status update to connected clients
                socketio.emit('status_update', current_status)
            else:
                # Fallback to old method if shared status not available
                printer_status = get_printer_status()
                if printer_status:
                    current_status.update({
                        'printer_connected': printer_status['connected'],
                        'printer_status': printer_status['state'],
                        'current_layer': printer_status['layer'],
                        'progress_percent': printer_status['progress'],
                        'last_update': datetime.now().isoformat()
                    })
                    socketio.emit('status_update', current_status)

            time.sleep(2)  # Update every 2 seconds

        except Exception as e:
            print(f"Error in status monitor: {e}")
            time.sleep(5)  # Wait longer on error

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
    """API endpoint for printer control commands"""
    if not CONTROLLERS_AVAILABLE:
        return jsonify({'success': False, 'message': 'Controller modules not available'}), 503

    try:
        if action == 'pause':
            result = printer_comms.pause_print()
        elif action == 'resume':
            result = printer_comms.resume_print()
        elif action == 'stop':
            result = printer_comms.stop_print()
        else:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400

        return jsonify({'success': result, 'action': action})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/pump', methods=['POST'])
def api_pump_control():
    """API endpoint for manual pump control"""
    if not CONTROLLERS_AVAILABLE:
        return jsonify({'success': False, 'message': 'Controller modules not available'}), 503

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

        # Use shared command system for pump control
        if shared_status:
            command_id = shared_status.add_command('pump_control', {
                'motor': motor,
                'direction': direction,
                'duration': duration
            })
            shared_status.log_activity('INFO', f'Manual pump control requested: {motor} {direction} {duration}s (command {command_id})', 'web_app')

            return jsonify({
                'success': True,
                'message': f'Pump {motor} command sent ({direction} for {duration}s)',
                'command_id': command_id
            })
        else:
            # Fallback to direct control if shared status not available
            pump_map = {'A': 'pump_a', 'B': 'pump_b', 'C': 'pump_c', 'D': 'drain_pump'}
            pump_name = pump_map.get(motor, f'pump_{motor.lower()}')

            current_status['pump_status'][pump_name] = f'running_{direction.lower()}'
            current_status['current_operation'] = f'manual_pump_{pump_name}'
            current_status['operation_start_time'] = datetime.now().isoformat()
            socketio.emit('status_update', current_status)

            # Execute pump command using existing photonmmu_pump module
            result = photonmmu_pump.run_stepper(motor, direction, duration)

            # Reset pump status
            current_status['pump_status'][pump_name] = 'idle'
            current_status['current_operation'] = 'idle'
            if current_status['operation_start_time']:
                start_time = datetime.fromisoformat(current_status['operation_start_time'])
                current_status['operation_duration'] = (datetime.now() - start_time).total_seconds()

            socketio.emit('status_update', current_status)

            return jsonify({'success': True, 'message': f'Pump {motor} completed {direction} for {duration}s'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/multi-material/start', methods=['POST'])
def api_start_multi_material():
    """API endpoint to start multi-material printing"""
    try:
        recipe_path = get_recipe_path()
        if not recipe_path.exists():
            return jsonify({'success': False, 'message': 'No recipe file found'}), 400

        # Use shared command system to request multi-material start
        if shared_status:
            command_id = shared_status.add_command('start_multi_material', {
                'recipe_path': str(recipe_path)
            })
            shared_status.log_activity('INFO', f'Multi-material start requested via web app (command {command_id})', 'web_app')

            return jsonify({
                'success': True,
                'message': 'Multi-material printing start requested',
                'command_id': command_id
            })
        else:
            return jsonify({'success': False, 'message': 'Shared status system not available'}), 503

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/multi-material/stop', methods=['POST'])
def api_stop_multi_material():
    """API endpoint to stop multi-material printing"""
    try:
        # Use shared command system to request multi-material stop
        if shared_status:
            command_id = shared_status.add_command('stop_multi_material', {})
            shared_status.log_activity('INFO', f'Multi-material stop requested via web app (command {command_id})', 'web_app')

            return jsonify({
                'success': True,
                'message': 'Multi-material printing stop requested',
                'command_id': command_id
            })
        else:
            return jsonify({'success': False, 'message': 'Shared status system not available'}), 503

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/emergency-stop', methods=['POST'])
def api_emergency_stop():
    """API endpoint for emergency stop"""
    try:
        # Use shared command system for emergency stop
        if shared_status:
            command_id = shared_status.add_command('emergency_stop', {})
            shared_status.log_activity('WARN', f'Emergency stop requested via web app (command {command_id})', 'web_app')

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
        config_data = request.json
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
        config_data = request.json
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

        try:
            files = communicator.get_files()
            if files:
                # Convert files to a more structured format
                file_list = []
                for file_info in files:
                    if hasattr(file_info, '__dict__'):
                        file_data = {
                            'name': getattr(file_info, 'name', 'Unknown'),
                            'size': getattr(file_info, 'size', 0),
                            'date': getattr(file_info, 'date', 'Unknown'),
                            'type': getattr(file_info, 'type', 'Unknown')
                        }
                    else:
                        # Handle simple string format
                        file_data = {
                            'name': str(file_info),
                            'size': 0,
                            'date': 'Unknown',
                            'type': 'Unknown'
                        }
                    file_list.append(file_data)

                return jsonify({
                    'success': True,
                    'files': file_list,
                    'count': len(file_list)
                })
            else:
                return jsonify({
                    'success': True,
                    'files': [],
                    'count': 0,
                    'message': 'No files found on printer'
                })
        except Exception as files_err:
            return jsonify({
                'success': False,
                'message': f'Failed to get printer files: {str(files_err)}'
            })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/printer/start-print', methods=['POST'])
def api_start_printer_print():
    """API endpoint to start printing a file on the printer"""
    try:
        if not CONTROLLERS_AVAILABLE:
            return jsonify({'success': False, 'message': 'Controller modules not available'}), 503

        data = request.json
        filename = data.get('filename')

        if not filename:
            return jsonify({'success': False, 'message': 'Filename is required'}), 400

        # Start print using printer_comms module
        from printer_comms import PrinterCommunicator
        communicator = PrinterCommunicator()

        try:
            result = communicator.start_print(filename)
            if result:
                return jsonify({
                    'success': True,
                    'message': f'Print started: {filename}'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'Failed to start print: {filename}'
                })
        except Exception as print_err:
            return jsonify({
                'success': False,
                'message': f'Print start failed: {str(print_err)}'
            })

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
        data = request.json
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

@socketio.on('connect')
def handle_connect():
    """Handle client connection for WebSocket"""
    print('Client connected')
    emit('status_update', current_status)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

def start_status_monitor():
    """Start the background status monitoring thread"""
    global status_monitor_thread, status_monitor_running

    if status_monitor_thread is None or not status_monitor_thread.is_alive():
        status_monitor_running = True
        status_monitor_thread = threading.Thread(target=status_monitor, daemon=True)
        status_monitor_thread.start()
        print("Status monitor started")

def stop_status_monitor():
    """Stop the background status monitoring thread"""
    global status_monitor_running
    status_monitor_running = False
    print("Status monitor stopped")

def run_print_manager(recipe_path):
    """Run the print manager in a separate process"""
    try:
        # Get printer IP from config
        config_path = get_config_path() / 'network_settings.ini'
        printer_ip = '192.168.4.3'  # Default

        if config_path.exists():
            import configparser
            config = configparser.ConfigParser()
            config.read(config_path)
            printer_ip = config.get('printer', 'ip_address', fallback='192.168.4.3')

        # Build command to run print manager
        controller_dir = Path(__file__).parent.parent / 'src' / 'controller'
        script_path = controller_dir / 'print_manager.py'

        cmd = [
            'python3', str(script_path),
            '--recipe', recipe_path,
            '--printer-ip', printer_ip
        ]

        # Run print manager and capture output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(controller_dir)
        )

        # Track the process
        active_processes['print_manager'] = process

        # Update status with timing
        current_status['current_operation'] = 'multi_material_printing'
        current_status['operation_start_time'] = datetime.now().isoformat()
        socketio.emit('status_update', current_status)

        # Monitor output and emit via WebSocket
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                # Parse and emit status updates
                socketio.emit('material_change_log', {'message': output.strip()})

        # Check if process completed successfully
        return_code = process.poll()

        # Calculate operation duration
        if current_status['operation_start_time']:
            start_time = datetime.fromisoformat(current_status['operation_start_time'])
            duration = (datetime.now() - start_time).total_seconds()
            current_status['operation_duration'] = duration

        # Clean up process tracking
        active_processes.pop('print_manager', None)

        if return_code == 0:
            current_status['current_operation'] = 'completed'
            socketio.emit('system_alert', {
                'message': f'Multi-material printing completed successfully in {duration:.1f}s',
                'type': 'success'
            })
        else:
            current_status['current_operation'] = 'error'
            error_output = process.stderr.read()
            socketio.emit('system_alert', {
                'message': f'Print manager failed after {duration:.1f}s: {error_output}',
                'type': 'danger'
            })

        current_status['mm_active'] = False
        socketio.emit('status_update', current_status)

    except Exception as e:
        print(f"Error running print manager: {e}")
        socketio.emit('system_alert', {
            'message': f'Failed to start print manager: {e}',
            'type': 'danger'
        })
        current_status['mm_active'] = False
        socketio.emit('status_update', current_status)

if __name__ == '__main__':
    print("Scion Multi-Material Printer Web Interface")
    print("==========================================")
    print(f"Controllers available: {CONTROLLERS_AVAILABLE}")
    print(f"Config path: {get_config_path()}")
    print(f"Recipe path: {get_recipe_path()}")

    # Setup logging integration
    logging_available = setup_logging_integration()
    print(f"Logging integration: {'enabled' if logging_available else 'disabled'}")

    # Start background monitoring
    start_status_monitor()

    try:
        # Run the Flask application
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        stop_status_monitor()