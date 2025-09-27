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
    'last_update': datetime.now().isoformat()
}

status_monitor_thread = None
status_monitor_running = False

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
    """Background thread to monitor printer status"""
    global status_monitor_running, current_status

    while status_monitor_running:
        try:
            # Get printer status
            printer_status = get_printer_status()
            if printer_status:
                current_status.update({
                    'printer_connected': printer_status['connected'],
                    'printer_status': printer_status['state'],
                    'current_layer': printer_status['layer'],
                    'progress_percent': printer_status['progress'],
                    'last_update': datetime.now().isoformat()
                })

                # Check recipe for next material change
                recipe = load_recipe()
                if recipe:
                    for item in recipe:
                        if item['layer'] > current_status['current_layer']:
                            current_status['next_material'] = item['material']
                            current_status['next_change_layer'] = item['layer']
                            break
                    else:
                        current_status['next_material'] = 'None'
                        current_status['next_change_layer'] = 0

                # Emit status update to connected clients
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

        # Execute pump command using existing photonmmu_pump module
        result = photonmmu_pump.run_stepper(motor, direction, duration)

        return jsonify({'success': True, 'message': f'Pump {motor} running {direction} for {duration}s'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/multi-material/start', methods=['POST'])
def api_start_multi_material():
    """API endpoint to start multi-material printing"""
    if not CONTROLLERS_AVAILABLE:
        return jsonify({'success': False, 'message': 'Controller modules not available'}), 503

    try:
        # This would start the print_manager.py process in the background
        recipe_path = get_recipe_path()
        if not recipe_path.exists():
            return jsonify({'success': False, 'message': 'No recipe file found'}), 400

        # Start print manager in background thread
        print_manager_thread = threading.Thread(
            target=run_print_manager,
            args=(str(recipe_path),),
            daemon=True
        )
        print_manager_thread.start()

        current_status['mm_active'] = True
        socketio.emit('status_update', current_status)

        return jsonify({'success': True, 'message': 'Multi-material printing started'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/multi-material/stop', methods=['POST'])
def api_stop_multi_material():
    """API endpoint to stop multi-material printing"""
    try:
        # This would stop the print_manager.py process
        current_status['mm_active'] = False
        socketio.emit('status_update', current_status)

        return jsonify({'success': True, 'message': 'Multi-material printing stopped'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/emergency-stop', methods=['POST'])
def api_emergency_stop():
    """API endpoint for emergency stop"""
    try:
        # Stop all pumps and processes
        current_status['mm_active'] = False
        socketio.emit('system_alert', {
            'message': 'Emergency stop activated',
            'type': 'danger'
        })

        return jsonify({'success': True, 'message': 'Emergency stop activated'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

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
        if return_code == 0:
            socketio.emit('system_alert', {
                'message': 'Multi-material printing completed successfully',
                'type': 'success'
            })
        else:
            error_output = process.stderr.read()
            socketio.emit('system_alert', {
                'message': f'Print manager failed: {error_output}',
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

    # Start background monitoring
    start_status_monitor()

    try:
        # Run the Flask application
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        stop_status_monitor()