"""
Print Manager - Production Multi-Material Printing Orchestration

Modern, GUI-friendly version with proper threading, logging, and queue communication.
Replaces blocking while loop with background threading to prevent GUI freezing.

Key Features:
- Background threading prevents GUI freezing
- Standard logging library for structured output
- Queue-based communication for safe cross-thread messaging
- Clean start/stop/pause/resume API for GUI integration
- Exception handling and graceful shutdown
- Real-time status updates and progress monitoring

Usage:
    manager = PrintManager()
    manager.load_recipe('recipe.txt')
    manager.start_monitoring('192.168.4.3')

    while manager.is_running():
        try:
            status = manager.get_status_update(timeout=1.0)
            print(f"{status.tag}: {status.message}")
        except queue.Empty:
            pass

    manager.stop_monitoring()

Requires: printer_comms (uart-wifi), mmu_control, threading, queue, logging
"""

import logging
import threading
import queue
import time
import argparse
import json
import configparser
import os
import sys
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional, Any

# Set up logger
logger = logging.getLogger(__name__)

# Import shared status system
try:
    from shared_status import get_shared_status
    shared_status = get_shared_status()
except ImportError as e:
    logger.warning(f"Could not import shared_status: {e}")
    shared_status = None

# Import controller modules with robust error handling
mmu_control = None
printer_comms = None

def _import_controller_modules():
    """Import controller modules with fallback strategies."""
    global mmu_control, printer_comms

    logger.debug("Attempting to import controller modules...")
    logger.debug(f"Current working directory: {os.getcwd()}")
    logger.debug(f"Script location: {__file__}")
    logger.debug(f"Python path: {sys.path}")

    try:
        # Try relative imports first (package mode)
        from . import mmu_control
        from . import printer_comms
        logger.info("✓ Relative imports successful")
        return True
    except ImportError as e:
        logger.debug(f"Relative import failed: {e}")
        try:
            # Try absolute imports (direct execution mode)
            import mmu_control
            import printer_comms
            logger.info("✓ Absolute imports successful")
            return True
        except ImportError as e2:
            logger.debug(f"Absolute import failed: {e2}")
            try:
                # Try adding current directory to path
                script_dir = Path(__file__).parent
                sys.path.insert(0, str(script_dir))
                import mmu_control
                import printer_comms
                logger.info("✓ Path-adjusted imports successful")
                return True
            except ImportError as e3:
                print("FATAL: All import methods failed!")
                print(f"  Relative import error: {e}")
                print(f"  Absolute import error: {e2}")
                print(f"  Path-adjusted import error: {e3}")
                print(f"  Current working directory: {os.getcwd()}")
                print(f"  Script directory: {Path(__file__).parent}")
                print(f"  Python path: {sys.path}")
                return False

# Initialize imports
_import_controller_modules()

class PrintManagerState(Enum):
    """Print manager operational states."""
    IDLE = "idle"
    STARTING = "starting"
    MONITORING = "monitoring"
    MATERIAL_CHANGING = "material_changing"
    PAUSING = "pausing"
    STOPPING = "stopping"
    ERROR = "error"

@dataclass
class StatusUpdate:
    """Status update message for queue communication."""
    timestamp: float
    level: str  # 'info', 'warning', 'error', 'debug'
    tag: str   # 'MONITOR', 'MATERIAL_CHANGE', 'STATUS', etc.
    message: str
    data: Optional[Dict[str, Any]] = None

class PrintManager:
    """
    Production-ready multi-material printing coordinator.

    Features background monitoring thread, structured logging, and queue-based
    communication for GUI integration. Manages printer monitoring and material
    changes without blocking the main application thread.

    Attributes:
        state (PrintManagerState): Current operational state
        recipe (Dict[int, str]): Layer->material mapping
        printer_ip (str): Target printer IP address
        is_monitoring (bool): True if monitoring thread is active
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize print manager with configuration.

        Args:
            config_path: Optional path to configuration file
        """
        logger.info("Initializing PrintManager...")

        # Configuration
        self.config_path = config_path or self._find_config_path()
        self.config = self._load_config()
        self.printer_ip = self.config.get('printer', 'ip_address', fallback='192.168.4.2')
        self.printer_port = self.config.getint('printer', 'port', fallback=80)
        self.timeout = self.config.getint('printer', 'timeout', fallback=10)

        # State management
        self.state = PrintManagerState.IDLE
        self.recipe: Dict[int, str] = {}
        self._last_processed_layer: Optional[int] = None

        # Threading and communication
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._status_queue = queue.Queue()
        self._state_lock = threading.RLock()

        # Monitoring configuration
        self.poll_interval = 5.0  # seconds between status polls
        self.log_cycle_frequency = 20  # log every N cycles (reduced frequency)
        self.progress_frequency = 40  # show progress every N cycles (reduced frequency)

        # Research logging setup
        self._experiment_start_time = None
        self._material_change_count = 0

        logger.info(f"Multi-Material Printer Ready - IP: {self.printer_ip}")

    def _find_config_path(self) -> Path:
        """Find configuration file path."""
        script_dir = Path(__file__).parent
        config_dir = script_dir.parent.parent / 'config'
        return config_dir / 'network_settings.ini'

    def _load_config(self) -> configparser.ConfigParser:
        """Load configuration from INI file."""
        config = configparser.ConfigParser()
        try:
            config.read(self.config_path)
            logger.info(f"Loaded configuration from: {self.config_path}")
        except Exception as e:
            logger.warning(f"Could not load config file: {e} - using defaults")
        return config

    def load_recipe(self, recipe_path: str) -> bool:
        """
        Load material change recipe from file.

        Args:
            recipe_path: Path to recipe file

        Returns:
            True if successful

        Format: "A,50:B,120:C,200" (material,layer pairs)
        """
        try:
            logger.info(f"Loading recipe: {recipe_path}")

            if not os.path.exists(recipe_path):
                logger.error(f"Recipe file does not exist: {recipe_path}")
                return False

            with open(recipe_path, 'r') as f:
                recipe_text = f.read().strip()

            if not recipe_text:
                logger.warning("Recipe file is empty")
                self.recipe = {}
                return True

            # Parse recipe format: "A,50:B,120"
            self.recipe = {}
            valid_materials = ['A', 'B', 'C', 'D']
            pairs = recipe_text.split(':')

            for i, pair in enumerate(pairs):
                if ',' not in pair:
                    logger.warning(f"Skipping invalid pair (no comma): '{pair}'")
                    continue

                try:
                    material, layer_str = pair.split(',', 1)
                    material = material.strip().upper()
                    layer_str = layer_str.strip()

                    # Validate material
                    if material not in valid_materials:
                        logger.error(f"Invalid material '{material}'. Must be one of: {valid_materials}")
                        continue

                    # Validate layer number
                    try:
                        layer = int(layer_str)
                        if layer <= 0:
                            logger.error(f"Invalid layer number '{layer}'. Must be positive integer.")
                            continue
                    except ValueError:
                        logger.error(f"Invalid layer number '{layer_str}'. Must be integer.")
                        continue

                    # Check for duplicate layers
                    if layer in self.recipe:
                        logger.warning(f"Duplicate layer {layer}. Overriding {self.recipe[layer]} with {material}")

                    self.recipe[layer] = material
                    logger.debug(f"Added layer mapping: {layer} -> {material}")

                except Exception as e:
                    logger.error(f"Failed to parse pair '{pair}': {e}")
                    continue

            if self.recipe:
                sorted_layers = sorted(self.recipe.keys())
                logger.info(f"Successfully loaded {len(self.recipe)} material changes")
                logger.info(f"Layer range: {min(sorted_layers)} to {max(sorted_layers)}")
            else:
                logger.warning("No valid material changes found in recipe")

            return True

        except Exception as e:
            logger.error(f"Critical error loading recipe: {e}", exc_info=True)
            return False

    def start_monitoring(self, printer_ip: Optional[str] = None, recipe_path: Optional[str] = None) -> bool:
        """
        Start background monitoring thread.

        Args:
            printer_ip: Optional printer IP override
            recipe_path: Optional recipe file to load first

        Returns:
            True if started successfully
        """
        with self._state_lock:
            if self.state != PrintManagerState.IDLE:
                logger.warning(f"Cannot start monitoring - current state: {self.state}")
                return False

            self.state = PrintManagerState.STARTING

            # Load recipe if provided
            if recipe_path and not self.load_recipe(recipe_path):
                logger.error("Failed to load recipe, aborting.")
                self.state = PrintManagerState.ERROR
                return False

            # Override printer IP if provided
            if printer_ip:
                self.printer_ip = printer_ip
                logger.info(f"Printer IP set to: {printer_ip}")

            # Clear stop event and reset state
            self._stop_event.clear()
            self._last_processed_layer = None

            # Start monitoring thread
            self._monitor_thread = threading.Thread(
                target=self._monitoring_loop,
                name="PrintManager-Monitor",
                daemon=True
            )

            try:
                self._monitor_thread.start()
                logger.info("Background monitoring thread started")
                self._send_status_update("STATUS", "Monitoring started", {"printer_ip": self.printer_ip})
                return True
            except Exception as e:
                logger.error(f"Failed to start monitoring thread: {e}")
                self.state = PrintManagerState.ERROR
                return False

    def stop_monitoring(self) -> bool:
        """
        Stop background monitoring thread gracefully.

        Returns:
            True if stopped successfully
        """
        with self._state_lock:
            if self.state == PrintManagerState.IDLE:
                logger.info("Monitoring already stopped")
                return True

            logger.info("Stopping monitoring thread...")
            self.state = PrintManagerState.STOPPING
            self._stop_event.set()

            # Wait for thread to complete
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=10.0)

                if self._monitor_thread.is_alive():
                    logger.warning("Monitoring thread did not stop gracefully")
                    return False

            self.state = PrintManagerState.IDLE
            logger.info("Monitoring stopped successfully")
            self._send_status_update("STATUS", "Monitoring stopped")
            return True

    def is_running(self) -> bool:
        """Check if monitoring thread is active."""
        with self._state_lock:
            return self.state in [PrintManagerState.STARTING, PrintManagerState.MONITORING, PrintManagerState.MATERIAL_CHANGING]

    def get_status_update(self, timeout: Optional[float] = None) -> StatusUpdate:
        """
        Get next status update from queue.

        Args:
            timeout: Maximum time to wait (None = block indefinitely)

        Returns:
            StatusUpdate object

        Raises:
            queue.Empty: If no update available within timeout
        """
        return self._status_queue.get(timeout=timeout)

    def get_current_state(self) -> Dict[str, Any]:
        """
        Get current manager state information.

        Returns:
            Dictionary with current state details
        """
        with self._state_lock:
            return {
                "state": self.state.value,
                "printer_ip": self.printer_ip,
                "recipe_count": len(self.recipe),
                "is_monitoring": self.is_running(),
                "last_processed_layer": self._last_processed_layer,
                "remaining_changes": list(sorted(self.recipe.keys()))
            }

    def _send_status_update(self, tag: str, message: str, data: Optional[Dict[str, Any]] = None, level: str = "info"):
        """Send status update to queue for GUI consumption and shared status files."""
        try:
            update = StatusUpdate(
                timestamp=time.time(),
                level=level,
                tag=tag,
                message=message,
                data=data or {}
            )
            self._status_queue.put_nowait(update)

            # Also update shared status files
            self._update_shared_status(tag, message, data, level)

        except queue.Full:
            logger.warning("Status queue full - dropping update")

    def _update_shared_status(self, tag: str, message: str, data: Optional[Dict[str, Any]] = None, level: str = "info"):
        """Update shared status files for both Qt GUI and web app access."""
        if shared_status is None:
            return

        try:
            # Log activity
            shared_status.log_activity(level, message, tag.lower())

            # Update specific status based on tag
            if tag == "PRINTER_STATUS" and data:
                shared_status.update_printer_status(**data)
            elif tag == "PUMP_STATUS" and data:
                pump_name = data.get("pump_name")
                if pump_name:
                    pump_data = {k: v for k, v in data.items() if k != "pump_name"}
                    shared_status.update_pump_status(pump_name, **pump_data)
                else:
                    shared_status.update_pump_status(**data)
            elif tag == "MATERIAL_CHANGE" and data:
                shared_status.update_recipe_progress(**data)
            elif tag == "MONITOR" and data:
                # General monitoring updates
                if "current_layer" in data:
                    shared_status.update_printer_status(**data)
                if "recipe_active" in data:
                    shared_status.update_recipe_progress(**data)

        except Exception as e:
            logger.warning(f"Failed to update shared status: {e}")

    def _monitoring_loop(self):
        """
        Main monitoring loop - research-focused logging only.
        """
        try:
            with self._state_lock:
                self.state = PrintManagerState.MONITORING
                self._experiment_start_time = time.time()

            # Clean startup message
            self._send_status_update("EXPERIMENT", f"Multi-material experiment started",
                                   {"recipe": dict(sorted(self.recipe.items())), "printer_ip": self.printer_ip})

            loop_count = 0
            last_layer_logged = None

            while not self._stop_event.is_set():
                loop_count += 1

                # Check for commands from shared status system
                if shared_status:
                    pending_commands = shared_status.get_pending_commands()
                    for command in pending_commands:
                        if command["status"] == "pending":
                            self._process_shared_command(command)
                            shared_status.mark_command_processed(command["id"])

                # Get printer status (suppress debug output)
                status = self._get_printer_status()
                if not status:
                    # Update shared status for printer disconnection
                    self._send_status_update("PRINTER_STATUS", "Printer disconnected",
                                           {"printer_connected": False, "printer_status": "Disconnected"}, "warning")
                    if not self._stop_event.wait(self.poll_interval):
                        continue
                    break

                # Update shared status for printer connection
                printer_status_str = getattr(status, 'status', 'Unknown')
                self._send_status_update("PRINTER_STATUS", f"Printer status: {printer_status_str}",
                                       {"printer_connected": True, "printer_status": printer_status_str})

                # Extract current layer
                current_layer = self._extract_current_layer(status)
                if current_layer is None:
                    if not self._stop_event.wait(2.0):
                        continue
                    break

                # Update current layer in shared status
                elapsed = time.time() - self._experiment_start_time
                layer_data = {
                    "current_layer": current_layer,
                    "elapsed_minutes": round(elapsed/60, 1),
                    "printer_connected": True,
                    "printer_status": printer_status_str
                }

                # Only log layer progress when it changes
                if current_layer != last_layer_logged:
                    self._send_status_update("PROGRESS", f"Layer {current_layer} reached", layer_data)
                    last_layer_logged = current_layer
                else:
                    # Still update shared status even if not logging
                    self._send_status_update("MONITOR", "Layer monitoring update", layer_data)

                # Check for material changes
                if current_layer in self.recipe and current_layer != self._last_processed_layer:
                    material = self.recipe[current_layer]
                    self._material_change_count += 1

                    change_start = time.time()
                    self._send_status_update("MATERIAL", f"Change #{self._material_change_count}: Layer {current_layer} → Material {material}",
                                           {"layer": current_layer, "material": material, "change_number": self._material_change_count})

                    with self._state_lock:
                        self.state = PrintManagerState.MATERIAL_CHANGING

                    if self._handle_material_change(material):
                        # Mark processed and remove from recipe
                        self._last_processed_layer = current_layer
                        del self.recipe[current_layer]

                        change_duration = time.time() - change_start
                        remaining = len(self.recipe)

                        self._send_status_update("MATERIAL", f"Change #{self._material_change_count} completed in {change_duration:.1f}s",
                                               {"material": material, "duration_seconds": round(change_duration, 1), "remaining_changes": remaining})

                        if remaining > 0:
                            next_layer = min(self.recipe.keys())
                            self._send_status_update("MATERIAL", f"Next change: Layer {next_layer} (Material {self.recipe[next_layer]})",
                                                   {"next_layer": next_layer, "next_material": self.recipe[next_layer]})
                    else:
                        self._send_status_update("MATERIAL", f"Change #{self._material_change_count} FAILED", level="error")
                        self._last_processed_layer = current_layer

                    with self._state_lock:
                        self.state = PrintManagerState.MONITORING

                # Check if print is complete
                if self._is_print_complete(status):
                    total_time = time.time() - self._experiment_start_time
                    self._send_status_update("EXPERIMENT", f"Experiment completed in {total_time/60:.1f} minutes",
                                           {"total_changes": self._material_change_count, "duration_minutes": round(total_time/60, 1)})
                    break

                # Wait for next cycle or stop signal
                if self._stop_event.wait(self.poll_interval):
                    break

        except Exception as e:
            self._send_status_update("EXPERIMENT", f"Critical error: {e}", level="error")
            with self._state_lock:
                self.state = PrintManagerState.ERROR

        finally:
            with self._state_lock:
                if self.state != PrintManagerState.ERROR:
                    self.state = PrintManagerState.IDLE

    def _get_printer_status(self):
        """Get current printer status via uart-wifi."""
        try:
            if printer_comms is None:
                return None
            return printer_comms.get_status(self.printer_ip)
        except Exception as e:
            return None

    def _extract_current_layer(self, status) -> Optional[int]:
        """
        Extract current layer from status response.

        Args:
            status: MonoXStatus object or string

        Returns:
            Layer number or None if parsing fails
        """
        try:
            # Handle MonoXStatus object directly
            if hasattr(status, 'current_layer'):
                layer_num = status.current_layer

                # Convert to int if it's a string
                if isinstance(layer_num, str) and layer_num.isdigit():
                    layer_num = int(layer_num)
                elif isinstance(layer_num, (int, float)):
                    layer_num = int(layer_num)
                else:
                    return None

                # Layer 0 means print hasn't started yet
                if layer_num <= 0:
                    return None

                return layer_num

            # If no current_layer attribute, check other attributes
            if hasattr(status, 'percent_complete') and hasattr(status, 'status'):
                # If just started printing, assume layer 1
                if status.status in ['print', 'printing'] and str(getattr(status, 'percent_complete', '0')) == '0':
                    return 1

            # Fallback to string parsing
            status_str = str(status)

            import re
            # Try multiple patterns to find current layer
            patterns = [
                r'current_layer:\s*(\d+)',
                r'current_lay[er]*:\s*(\d+)',
                r'layer:\s*(\d+)',
                r'current_layer\s*=\s*(\d+)',
                r'current_layer":\s*(\d+)',
            ]

            for pattern in patterns:
                match = re.search(pattern, status_str, re.IGNORECASE)
                if match:
                    layer_num = int(match.group(1))
                    if layer_num <= 0:
                        return None
                    return layer_num

            # If no pattern matches, try to find any number after "current" or "layer"
            current_match = re.search(r'current.*?(\d+)', status_str, re.IGNORECASE)
            if current_match:
                layer_num = int(current_match.group(1))
                if layer_num <= 0:
                    return None
                return layer_num

            return None

        except Exception as e:
            return None

    def _handle_material_change(self, material: str) -> bool:
        """
        Execute material change: pause -> change -> resume.

        Args:
            material: Target material (A, B, C, D)

        Returns:
            True if successful
        """
        try:
            self._send_status_update("MATERIAL", f"Starting material change to {material}")

            # Step 1: Pause printer
            self._send_status_update("TIMING", "Step 1: Pausing printer...")
            if not self._pause_printer():
                self._send_status_update("MATERIAL", "ERROR: Could not pause printer", level="error")
                return False

            # Step 2: Wait for bed to rise
            self._send_status_update("TIMING", "Step 2: Waiting for bed to reach raised position...")
            self._wait_for_bed_raised()

            # Step 3: Execute material change
            self._send_status_update("TIMING", "Step 3: Starting pump sequence...")
            pump_start = time.time()

            if mmu_control is None:
                self._send_status_update("MATERIAL", "ERROR: MMU control not available - imports failed", level="error")
                # Log import status for debugging
                self._send_status_update("MATERIAL", f"Current working directory: {os.getcwd()}", level="error")
                self._send_status_update("MATERIAL", f"Python path: {sys.path}", level="error")
                return False

            self._send_status_update("TIMING", f"Starting MMU change_material({material})...")
            success = mmu_control.change_material(material)
            pump_duration = time.time() - pump_start

            if success:
                self._send_status_update("TIMING", f"✓ Pump sequence completed in {pump_duration:.1f}s")
            else:
                self._send_status_update("MATERIAL", "ERROR: Pump sequence failed", level="error")
                return False

            # Step 4: Resume printer
            self._send_status_update("TIMING", "Step 4: Resuming printer...")
            if self._resume_printer():
                self._send_status_update("MATERIAL", f"✓ Material change to {material} completed successfully")
                return True
            else:
                self._send_status_update("MATERIAL", "ERROR: Could not resume printer", level="error")
                return False

        except Exception as e:
            self._send_status_update("MATERIAL", f"ERROR: Material change failed: {e}", level="error")
            return False

    def _pause_printer(self) -> bool:
        """Pause printer via uart-wifi."""
        try:
            if printer_comms is None:
                return False
            return printer_comms.pause_print(self.printer_ip)
        except Exception as e:
            logger.error(f"Error pausing printer: {e}")
            return False

    def _resume_printer(self) -> bool:
        """Resume printer via uart-wifi."""
        try:
            if printer_comms is None:
                return False
            return printer_comms.resume_print(self.printer_ip)
        except Exception as e:
            logger.error(f"Error resuming printer: {e}")
            return False

    def _wait_for_bed_raised(self):
        """
        Wait for bed to reach raised position after pause.

        Critical timing for material changes - detailed logging for troubleshooting.
        """
        self._send_status_update("TIMING", "Bed positioning: Initial 2s pause command delay...")
        time.sleep(2)

        # Extended wait for mechanical bed movement
        bed_raise_time = 15
        self._send_status_update("TIMING", f"Bed positioning: {bed_raise_time}s mechanical movement...")

        for i in range(bed_raise_time):
            if self._stop_event.wait(1.0):  # Respect stop signal
                return

            if (i + 1) % 5 == 0:  # Progress update every 5 seconds
                self._send_status_update("TIMING", f"Bed positioning: {i + 1}/{bed_raise_time}s elapsed")

        # Verify printer is still paused
        status = self._get_printer_status()
        if status and hasattr(status, 'status'):
            if status.status.lower() == 'pause':
                self._send_status_update("TIMING", "✓ Bed positioned, printer still paused")
            else:
                self._send_status_update("TIMING", f"WARNING: Expected pause, got {status.status}", level="warning")
        else:
            self._send_status_update("TIMING", "WARNING: Could not verify pause status", level="warning")

        # Additional safety buffer
        self._send_status_update("TIMING", "Bed positioning: 3s safety buffer...")
        time.sleep(3)
        self._send_status_update("TIMING", "✓ Bed positioning complete - ready for material change")

    def _is_print_complete(self, status) -> bool:
        """Check if print is complete based on status."""
        try:
            # Handle MonoXStatus object
            if hasattr(status, 'status'):
                printer_status = status.status
                percent = getattr(status, 'percent_complete', 0)
                current_layer = getattr(status, 'current_layer', 0)
                total_layers = getattr(status, 'total_layers', 0)

                # Print is complete if status is specifically "complete" or "finished"
                if printer_status.lower() in ['complete', 'finished', 'done']:
                    return True

                if printer_status.lower() == 'stop' and percent >= 100:
                    return True

                if total_layers > 0 and current_layer >= total_layers and percent >= 99:
                    return True

                # Print is NOT complete if actively printing
                if printer_status.lower() in ['print', 'printing']:
                    return False

                # Print is NOT complete if stopped but not at end
                if printer_status.lower() == 'stop' and percent < 100:
                    return False

            # Fallback to string checking
            status_str = str(status).lower()
            if 'status: complete' in status_str or 'status: finished' in status_str:
                return True

            return False

        except Exception as e:
            return False

    def _process_shared_command(self, command):
        """Process commands from shared status system."""
        cmd_type = command["command"]
        params = command.get("parameters", {})

        if cmd_type == "start_multi_material":
            recipe_path = params.get("recipe_path")
            if recipe_path and os.path.exists(recipe_path):
                self.load_recipe(recipe_path)
                self._send_status_update("COMMAND", f"Loaded recipe: {recipe_path}")
        elif cmd_type == "stop_multi_material":
            self._stop_event.set()
            self._send_status_update("COMMAND", "Stop command received")
        elif cmd_type == "emergency_stop":
            self._stop_event.set()
            self._send_status_update("COMMAND", "Emergency stop activated", level="warning")
        elif cmd_type == "pump_control":
            # Handle manual pump control
            if mmu_control:
                motor = params.get("motor")
                direction = params.get("direction")
                duration = params.get("duration")
                success = mmu_control.run_pump_manual(motor, direction, duration)
                self._send_status_update("PUMP", f"Manual pump {motor} {direction} {duration}s: {'success' if success else 'failed'}")


def main():
    """
    Command-line interface for the modernized print manager.

    Demonstrates usage and provides CLI access for testing.
    """
    import sys

    # Configure clean logging for GUI integration
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',  # Clean format without timestamps/levels
        stream=sys.stdout      # Send to stdout, not stderr
    )

    parser = argparse.ArgumentParser(description='Multi-Material Print Manager')
    parser.add_argument('--recipe', '-r', help='Path to recipe file')
    parser.add_argument('--config', '-c', help='Path to config file')
    parser.add_argument('--printer-ip', '-i', help='Printer IP address override')

    args = parser.parse_args()

    try:
        # Create manager
        manager = PrintManager(args.config)
        logger.info("PrintManager created successfully")

        # Load recipe
        recipe_path = args.recipe or manager._find_config_path().parent / 'recipe.txt'
        if not manager.load_recipe(str(recipe_path)):
            logger.error("Failed to load recipe")
            return 1

        # Start monitoring
        printer_ip = args.printer_ip or manager.printer_ip
        if not manager.start_monitoring(printer_ip):
            logger.error("Failed to start monitoring")
            return 1

        # Monitor status updates
        logger.info("Monitoring started - press Ctrl+C to stop")
        try:
            while manager.is_running():
                try:
                    update = manager.get_status_update(timeout=1.0)
                    print(f"[{update.timestamp:.1f}] {update.tag}: {update.message}")
                    sys.stdout.flush()  # Force immediate output for GUI
                except queue.Empty:
                    pass
        except KeyboardInterrupt:
            logger.info("Stopping monitoring...")

        # Clean shutdown
        manager.stop_monitoring()
        logger.info("Print manager completed successfully")
        return 0

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())