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
from datetime import datetime
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional, Any

# Set up logger
logger = logging.getLogger(__name__)

# Import WebSocket IPC system (replaces file-based shared_status)
try:
    from .websocket_ipc import WebSocketIPCClient
    WEBSOCKET_IPC_AVAILABLE = True
except ImportError as e:
    try:
        from controller.websocket_ipc import WebSocketIPCClient
        WEBSOCKET_IPC_AVAILABLE = True
    except ImportError as e2:
        logger.warning(f"Could not import websocket_ipc: {e} | {e2}")
        WebSocketIPCClient = None
        WEBSOCKET_IPC_AVAILABLE = False

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
        self._recipe_active = False  # Flag to control recipe-based material changes

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

        # WebSocket IPC client for real-time communication with web app
        self.websocket_client = None
        self._command_processing_thread = None
        if WEBSOCKET_IPC_AVAILABLE:
            try:
                self.websocket_client = WebSocketIPCClient()
                self.websocket_client.on_command_received = self._handle_websocket_command
                self.websocket_client.on_connection_changed = self._handle_connection_change
                logger.info("WebSocket IPC client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize WebSocket IPC client: {e}")
                self.websocket_client = None
        else:
            logger.warning("WebSocket IPC not available - falling back to file-based communication")

        # Quiescence management: window where we intentionally avoid sending
        # additional printer control commands after a pause to allow mechanical
        # bed raise and firmware internal sequences to complete.
        self._quiescent_until: float = 0.0

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
        """Send status update to queue for GUI consumption and WebSocket/shared status."""
        try:
            update = StatusUpdate(
                timestamp=time.time(),
                level=level,
                tag=tag,
                message=message,
                data=data or {}
            )
            self._status_queue.put_nowait(update)

            # Send via WebSocket IPC system
            if self.websocket_client and self.websocket_client.is_connected():
                self._send_websocket_status_update(tag, message, data, level)
            else:
                # WebSocket not available - log locally only
                logger.debug(f"[{tag}] {message}" + (f" | Data: {data}" if data else ""))

        except queue.Full:
            logger.warning("Status queue full - dropping update")

    def _update_shared_status(self, tag: str, message: str, data: Optional[Dict[str, Any]] = None, level: str = "info"):
        """Legacy method - now handled by WebSocket IPC system."""
        # This method is now deprecated as status updates are handled
        # directly via WebSocket in _send_status_update()
        logger.debug(f"Legacy shared_status call for {tag}: {message}")

    def _handle_websocket_command(self, command_data: Dict[str, Any]):
        """Handle commands received via WebSocket IPC."""
        try:
            command_type = command_data.get('command_type')
            command_id = command_data.get('command_id')
            parameters = command_data.get('parameters', {})

            logger.info(f"Received WebSocket command: {command_type} ({command_id})")

            # Process the command using existing handler (adapt to expected format)
            command_dict = {
                "command": command_type,
                "parameters": parameters,
                "command_id": command_id
            }
            success = self._process_shared_command(command_dict)

            # Send result back via WebSocket
            if self.websocket_client and command_id:
                self.websocket_client.mark_command_processed(
                    command_id,
                    success=success,
                    result="Command executed successfully" if success else "Command failed"
                )

        except Exception as e:
            logger.error(f"Error handling WebSocket command: {e}")
            if self.websocket_client and 'command_id' in command_data:
                self.websocket_client.mark_command_processed(
                    command_data['command_id'],
                    success=False,
                    result=f"Error: {e}"
                )

    def _handle_connection_change(self, connected: bool):
        """Handle WebSocket connection status changes."""
        if connected:
            logger.info("Connected to web application via WebSocket")
            self._send_status_update("WEBSOCKET", "Connected to web application")
        else:
            logger.warning("Disconnected from web application")
            self._send_status_update("WEBSOCKET", "Disconnected from web application", level="warning")

    def _send_websocket_status_update(self, tag: str, message: str, data: Optional[Dict[str, Any]] = None, level: str = "info"):
        """Send status update via WebSocket IPC (replaces file-based communication)."""
        if self.websocket_client and self.websocket_client.is_connected():
            try:
                self.websocket_client.send_status_update(
                    component=tag,
                    status=message,
                    data=data,
                    level=level
                )
            except Exception as e:
                logger.warning(f"Failed to send WebSocket status update: {e}")

    def _monitoring_loop(self):
        """
        Main monitoring loop - research-focused logging only.
        """
        try:
            with self._state_lock:
                self.state = PrintManagerState.MONITORING
                self._experiment_start_time = time.time()

            # Start WebSocket connection if available
            if self.websocket_client:
                if self.websocket_client.connect():
                    logger.info("WebSocket connection established")
                else:
                    logger.warning("Failed to establish WebSocket connection - falling back to file-based communication")

            # Clean startup message
            self._send_status_update("EXPERIMENT", f"Multi-material experiment started",
                                   {"recipe": dict(sorted(self.recipe.items())), "printer_ip": self.printer_ip})

            loop_count = 0
            last_layer_logged = None

            while not self._stop_event.is_set():
                loop_count += 1

                # Handle commands via WebSocket (preferred) or file-based system (fallback)
                if self.websocket_client and self.websocket_client.is_connected():
                    # WebSocket commands are handled automatically via callbacks
                    # Process any queued commands from WebSocket
                    command = self.websocket_client.get_next_command(timeout=0.1)
                    if command:
                        command_dict = {
                            "command": command['command_type'],
                            "parameters": command.get('parameters', {}),
                            "command_id": command.get('command_id')
                        }
                        success = self._process_shared_command(command_dict)
                        self.websocket_client.mark_command_processed(
                            command['command_id'],
                            success=success,
                            result="Command executed" if success else "Command failed"
                        )
                else:
                    # No WebSocket connection available - log warning
                    if loop_count % 60 == 0:  # Log every 5 minutes (60 * 5s intervals)
                        logger.warning("No WebSocket connection available for receiving commands")

                # Get printer status (suppress debug output)
                status = None
                # Suppress polling during quiescent window to reduce printer command load
                if time.time() >= self._quiescent_until:
                    status = self._get_printer_status()
                else:
                    # Still emit a lightweight status heartbeat so UI knows we're alive
                    remaining = round(self._quiescent_until - time.time(), 1)
                    self._send_status_update("QUIESCENCE", f"Quiescent window active ({remaining}s remaining)")
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

                # Check for material changes (only if recipe is active)
                if self._recipe_active and current_layer in self.recipe and current_layer != self._last_processed_layer:
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
            # Disconnect WebSocket client
            if self.websocket_client:
                try:
                    self.websocket_client.disconnect()
                    logger.info("WebSocket client disconnected")
                except Exception as e:
                    logger.warning(f"Error disconnecting WebSocket client: {e}")

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
        Extract current layer from MonoXStatus object.

        Args:
            status: MonoXStatus object from uart-wifi library

        Returns:
            Layer number or None if parsing fails
        """
        if status and hasattr(status, 'current_layer'):
            try:
                layer_num = int(status.current_layer)
                return layer_num if layer_num > 0 else None
            except (ValueError, TypeError):
                return None
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
                self._enter_error_state("Failed to pause printer prior to material change", {"target_material": material})
                return False

            # Step 2: Wait for bed to rise
            self._send_status_update("TIMING", "Step 2: Waiting for bed to reach raised position...")
            self._wait_for_bed_raised()

            # Step 3: Execute material change
            self._send_status_update("TIMING", "Step 3: Starting pump sequence...")
            pump_start = time.time()

            if mmu_control is None:
                self._send_status_update("MATERIAL", "ERROR: MMU control not available - imports failed", level="error")
                self._enter_error_state("MMU controller unavailable", {"cwd": os.getcwd()})
                return False

            self._send_status_update("TIMING", f"Starting MMU change_material({material})...")
            success = mmu_control.change_material(material)
            pump_duration = time.time() - pump_start

            if success:
                self._send_status_update("TIMING", f"✓ Pump sequence completed in {pump_duration:.1f}s")
            else:
                self._send_status_update("MATERIAL", "ERROR: Pump sequence failed", level="error")
                self._enter_error_state("Pump sequence failed during material change", {"target_material": material, "duration": pump_duration})
                return False

            # Step 4: Resume printer
            self._send_status_update("TIMING", "Step 4: Resuming printer...")
            if self._resume_printer():
                self._send_status_update("MATERIAL", f"✓ Material change to {material} completed successfully")
                return True
            else:
                self._send_status_update("MATERIAL", "ERROR: Could not resume printer", level="error")
                self._enter_error_state("Failed to resume printer after material change", {"target_material": material})
                return False

        except Exception as e:
            self._send_status_update("MATERIAL", f"ERROR: Material change failed: {e}", level="error")
            self._enter_error_state("Unhandled exception in material change", {"error": str(e), "target_material": material})
            return False

    def _enter_error_state(self, reason: str, data: Optional[Dict[str, Any]] = None):
        """Centralize transition to ERROR state with status emission and stop signal."""
        with self._state_lock:
            self.state = PrintManagerState.ERROR
        self._stop_event.set()
        self._send_status_update("SYSTEM", f"ERROR STATE: {reason}", data or {}, level="error")

    def _pause_printer(self) -> bool:
        """Pause printer via uart-wifi."""
        try:
            if printer_comms is None:
                return False
            success = printer_comms.pause_print(self.printer_ip)
            if success:
                # Establish 10 second quiescent window (configurable via env var) to prevent
                # race conditions where subsequent commands interfere with firmware pause sequence.
                quiescent_seconds = float(os.environ.get('MMU_PAUSE_QUIESCENCE_SECONDS', '10'))
                self._quiescent_until = time.time() + quiescent_seconds
                self._send_status_update("QUIESCENCE", f"Quiescent window started for {quiescent_seconds}s after pause")
            return success
        except Exception as e:
            logger.error(f"Error pausing printer: {e}")
            return False

    def _resume_printer(self) -> bool:
        """Resume printer via uart-wifi."""
        try:
            if printer_comms is None:
                return False
            # Ensure we are outside quiescent window before resuming
            if time.time() < self._quiescent_until:
                wait_time = round(self._quiescent_until - time.time(), 2)
                self._send_status_update("QUIESCENCE", f"Waiting {wait_time}s to exit quiescent window before resume")
                while time.time() < self._quiescent_until and not self._stop_event.wait(0.25):
                    pass
            success = printer_comms.resume_print(self.printer_ip)
            if success:
                # Clear quiescent window on successful resume
                self._quiescent_until = 0.0
            return success
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
        cmd_type = command.get("command") if command else None
        params = command.get("parameters", {}) if command else {}
        command_id = command.get("command_id") if command else None

        if not cmd_type:
            self._send_status_update("COMMAND", "Received malformed command payload", level="error")
            return False

        if cmd_type == "start_multi_material":
            recipe_path = params.get("recipe_path")
            if recipe_path and os.path.exists(recipe_path):
                self.load_recipe(recipe_path)
                self._recipe_active = True
                self._send_status_update("COMMAND", f"Recipe activated: {recipe_path}")
        elif cmd_type == "stop_multi_material":
            self._recipe_active = False
            self._send_status_update("COMMAND", "Recipe deactivated - material changes disabled")
        elif cmd_type == "pause_print":
            # Pause the printer (not the print manager service)
            if printer_comms:
                try:
                    success = printer_comms.pause_print(self.printer_ip)
                    if success:
                        self._send_status_update("PRINTER", "Printer paused")
                    else:
                        self._send_status_update("PRINTER", "Failed to pause printer", level="error")
                except Exception as e:
                    self._send_status_update("PRINTER", f"Error pausing printer: {e}", level="error")
            else:
                self._send_status_update("PRINTER", "Printer communication unavailable", level="error")
        elif cmd_type == "resume_print":
            # Resume the printer
            if printer_comms:
                try:
                    success = printer_comms.resume_print(self.printer_ip)
                    if success:
                        self._send_status_update("PRINTER", "Printer resumed")
                    else:
                        self._send_status_update("PRINTER", "Failed to resume printer", level="error")
                except Exception as e:
                    self._send_status_update("PRINTER", f"Error resuming printer: {e}", level="error")
            else:
                self._send_status_update("PRINTER", "Printer communication unavailable", level="error")
        elif cmd_type == "stop_print":
            # Stop the current print job on the printer
            if printer_comms:
                try:
                    success = printer_comms.stop_print(self.printer_ip)
                    if success:
                        self._recipe_active = False  # Also disable recipe when print stops
                        self._send_status_update("PRINTER", "Print job stopped")
                    else:
                        self._send_status_update("PRINTER", "Failed to stop printer", level="error")
                except Exception as e:
                    self._send_status_update("PRINTER", f"Error stopping printer: {e}", level="error")
            else:
                self._send_status_update("PRINTER", "Printer communication unavailable", level="error")
        elif cmd_type == "emergency_stop":
            self._stop_event.set()
            self._send_status_update("COMMAND", "Emergency stop activated", level="warning")
        elif cmd_type == "pump_control":
            if mmu_control:
                motor = params.get("motor")
                direction = params.get("direction")
                duration = params.get("duration")

                if motor and direction and duration is not None:
                    self._send_status_update("PUMP", f"Executing manual pump command: {motor} {direction} for {duration}s")
                    success = mmu_control.run_pump_by_id(motor, direction, duration)
                    self._send_status_update("PUMP", f"Manual pump {motor} {direction} {duration}s: {'success' if success else 'failed'}")
                else:
                    self._send_status_update("PUMP", "Invalid manual pump command parameters", level="error")
        elif cmd_type == "run_material_change":
            # Handle manual material change sequence
            target_material = params.get("target_material")
            if target_material and mmu_control:
                self._send_status_update("SEQUENCE", f"Starting material change sequence to {target_material}")

                # Execute complete material change sequence with custom timing
                drain_time = params.get("drain_time", 30)
                fill_time = params.get("fill_time", 25)
                settle_time = params.get("settle_time", 5)

                success = self._execute_material_change_sequence(target_material, drain_time, fill_time, settle_time)

                if success:
                    self._send_status_update("SEQUENCE", f"Material change sequence to {target_material} completed successfully")
                else:
                    self._send_status_update("SEQUENCE", f"Material change sequence to {target_material} failed", level="error")
            else:
                self._send_status_update("SEQUENCE", "Invalid material change parameters or MMU control not available", level="error")
        elif cmd_type == "get_files":
            files = []
            success = False
            error_message = None

            if printer_comms:
                try:
                    files = printer_comms.get_files(self.printer_ip)
                    success = True
                except Exception as exc:
                    error_message = str(exc)
                    self._send_status_update(
                        "FILES",
                        f"File retrieval failed: {error_message}",
                        level="error"
                    )
            else:
                error_message = "Printer communication module unavailable"
                self._send_status_update("FILES", error_message, level="error")

            if success:
                self._send_status_update(
                    "FILES",
                    f"Retrieved {len(files)} file(s) from printer",
                    {"file_count": len(files)}
                )

            if self.websocket_client and self.websocket_client.is_connected():
                payload = {
                    "command_id": command_id,
                    "success": success,
                    "files": files,
                    "message": error_message or f"Retrieved {len(files)} files",
                    "timestamp": datetime.now().isoformat()
                }
                try:
                    self.websocket_client.emit('file_list_response', payload)
                except Exception as exc:
                    logger.warning(f"Failed to emit file list response: {exc}")

            return success
        elif cmd_type == "start_printer_print":
            filename = params.get('filename')
            if not filename:
                self._send_status_update("PRINTER", "Start print failed: filename not provided", level="error")
                return False

            if not printer_comms:
                self._send_status_update("PRINTER", "Start print failed: printer communication module unavailable", level="error")
                return False

            try:
                started = printer_comms.start_print(filename, self.printer_ip)
            except Exception as exc:
                self._send_status_update(
                    "PRINTER",
                    f"Start print encountered an error: {exc}",
                    {"filename": filename},
                    level="error"
                )
                return False

            if started:
                self._send_status_update(
                    "PRINTER",
                    f"Printer start initiated for {filename}",
                    {"filename": filename}
                )
                return True

            self._send_status_update(
                "PRINTER",
                f"Printer rejected start request for {filename}",
                {"filename": filename},
                level="error"
            )
            return False
        elif cmd_type == "test_i2c":
            # Test I2C communication with motor controllers
            self._send_status_update("DIAGNOSTICS", "Starting I2C communication test...")
            success = self._test_i2c_communication()
            result_msg = "I2C test completed successfully" if success else "I2C test failed"
            level = "info" if success else "error"
            self._send_status_update("DIAGNOSTICS", result_msg, level=level)
        elif cmd_type == "test_gpio":
            # Test GPIO pin accessibility
            self._send_status_update("DIAGNOSTICS", "Starting GPIO pin test...")
            success = self._test_gpio_pins()
            result_msg = "GPIO test completed successfully" if success else "GPIO test failed"
            level = "info" if success else "error"
            self._send_status_update("DIAGNOSTICS", result_msg, level=level)
        elif cmd_type == "test_pump_motors":
            # Test all pump motor connectivity
            self._send_status_update("DIAGNOSTICS", "Starting pump motor connectivity test...")
            results = self._test_pump_motors()
            self._send_status_update("DIAGNOSTICS", f"Pump motor test completed. Results: {results}")
        elif cmd_type == "run_full_diagnostics":
            # Run comprehensive system diagnostics
            self._send_status_update("DIAGNOSTICS", "Starting full system diagnostics...")
            self._run_full_diagnostics()
        elif cmd_type == "calibrate_pumps":
            # Start pump calibration wizard
            self._send_status_update("CALIBRATION", "Starting pump calibration wizard...")
            self._calibrate_all_pumps()
        elif cmd_type == "calibrate_single_pump":
            # Calibrate specific pump
            pump_id = params.get("pump_id")
            if pump_id:
                self._send_status_update("CALIBRATION", f"Starting calibration for pump {pump_id}...")
                self._calibrate_single_pump(pump_id)
            else:
                self._send_status_update("CALIBRATION", "Invalid pump ID for calibration", level="error")
        else:
            self._send_status_update("COMMAND", f"Unknown command: {cmd_type}", level="warning")
            return False

        # Default return for successful command processing
        return True

    def _execute_material_change_sequence(self, target_material: str, drain_time: int, fill_time: int, settle_time: int) -> bool:
        """
        Execute complete material change sequence with custom timing.

        Args:
            target_material: Target material (A, B, C, D)
            drain_time: Drain duration in seconds
            fill_time: Fill duration in seconds
            settle_time: Settle duration in seconds

        Returns:
            True if successful
        """
        try:
            total_steps = 3
            current_step = 0

            # Step 1: Drain current material
            current_step += 1
            self._send_status_update("SEQUENCE", f"Step {current_step}/{total_steps}: Draining current material for {drain_time}s",
                                   {"current_step": current_step, "total_steps": total_steps, "step_name": "drain"})

            success = mmu_control.run_pump_by_id('D', 'R', drain_time)  # Use drain pump in reverse
            if not success:
                self._send_status_update("SEQUENCE", "Drain step failed", level="error")
                return False

            # Step 2: Fill with new material
            current_step += 1
            self._send_status_update("SEQUENCE", f"Step {current_step}/{total_steps}: Filling with material {target_material} for {fill_time}s",
                                   {"current_step": current_step, "total_steps": total_steps, "step_name": "fill"})

            success = mmu_control.run_pump_by_id(target_material, 'F', fill_time)
            if not success:
                self._send_status_update("SEQUENCE", "Fill step failed", level="error")
                return False

            # Step 3: Settle (wait)
            current_step += 1
            self._send_status_update("SEQUENCE", f"Step {current_step}/{total_steps}: Settling for {settle_time}s",
                                   {"current_step": current_step, "total_steps": total_steps, "step_name": "settle"})

            time.sleep(settle_time)

            self._send_status_update("SEQUENCE", "Material change sequence completed successfully",
                                   {"current_step": total_steps, "total_steps": total_steps, "step_name": "complete"})
            return True

        except Exception as e:
            self._send_status_update("SEQUENCE", f"Material change sequence failed: {e}", level="error")
            return False

    def _test_i2c_communication(self) -> bool:
        """Test I2C communication with motor controllers"""
        try:
            # Import I2C testing modules
            try:
                import board
                import busio
                self._send_status_update("DIAGNOSTICS", "I2C modules imported successfully")
            except ImportError as e:
                self._send_status_update("DIAGNOSTICS", f"I2C module import failed: {e}", level="error")
                return False

            # Test I2C bus initialization
            try:
                i2c = busio.I2C(board.SCL, board.SDA)
                self._send_status_update("DIAGNOSTICS", "I2C bus initialized successfully")

                # Scan for devices
                while not i2c.try_lock():
                    pass
                devices = i2c.scan()
                i2c.unlock()

                if devices:
                    device_addrs = [hex(addr) for addr in devices]
                    self._send_status_update("DIAGNOSTICS", f"Found I2C devices at addresses: {', '.join(device_addrs)}")
                    return True
                else:
                    self._send_status_update("DIAGNOSTICS", "No I2C devices found", level="warning")
                    return False

            except Exception as e:
                self._send_status_update("DIAGNOSTICS", f"I2C bus test failed: {e}", level="error")
                return False

        except Exception as e:
            self._send_status_update("DIAGNOSTICS", f"I2C test failed: {e}", level="error")
            return False

    def _test_gpio_pins(self) -> bool:
        """Test GPIO pin accessibility"""
        try:
            # Get pump configuration to test configured GPIO pins
            config_path = self._find_config_path() / 'pump_profiles.json'
            if not config_path.exists():
                self._send_status_update("DIAGNOSTICS", "Pump configuration file not found", level="error")
                return False

            import json
            with open(config_path, 'r') as f:
                config = json.load(f)

            gpio_pins = []
            for pump_id, pump_config in config.get('pumps', {}).items():
                gpio_pin = pump_config.get('gpio_pin')
                if gpio_pin:
                    gpio_pins.append(gpio_pin)

            if not gpio_pins:
                self._send_status_update("DIAGNOSTICS", "No GPIO pins configured in pump profiles", level="warning")
                return False

            # Test GPIO access
            try:
                import RPi.GPIO as GPIO
                GPIO.setmode(GPIO.BCM)

                failed_pins = []
                for pin in gpio_pins:
                    try:
                        GPIO.setup(pin, GPIO.OUT)
                        self._send_status_update("DIAGNOSTICS", f"GPIO pin {pin} setup successful")
                    except Exception as e:
                        failed_pins.append(pin)
                        self._send_status_update("DIAGNOSTICS", f"GPIO pin {pin} setup failed: {e}", level="error")

                GPIO.cleanup()

                if failed_pins:
                    self._send_status_update("DIAGNOSTICS", f"GPIO test failed for pins: {failed_pins}", level="error")
                    return False
                else:
                    self._send_status_update("DIAGNOSTICS", "All configured GPIO pins accessible")
                    return True

            except ImportError:
                self._send_status_update("DIAGNOSTICS", "RPi.GPIO module not available", level="error")
                return False

        except Exception as e:
            self._send_status_update("DIAGNOSTICS", f"GPIO test failed: {e}", level="error")
            return False

    def _test_pump_motors(self) -> dict:
        """Test all pump motor connectivity"""
        results = {}
        try:
            if not mmu_control:
                self._send_status_update("DIAGNOSTICS", "MMU control not available", level="error")
                return {"error": "MMU control not available"}

            # Test each pump with a short movement
            pumps = ['A', 'B', 'C', 'D']
            for pump in pumps:
                try:
                    self._send_status_update("DIAGNOSTICS", f"Testing pump {pump}...")
                    success = mmu_control.run_pump_by_id(pump, 'F', 1)  # 1 second forward
                    results[pump] = "OK" if success else "FAILED"
                    self._send_status_update("DIAGNOSTICS", f"Pump {pump}: {'OK' if success else 'FAILED'}")
                except Exception as e:
                    results[pump] = f"ERROR: {e}"
                    self._send_status_update("DIAGNOSTICS", f"Pump {pump} error: {e}", level="error")

        except Exception as e:
            self._send_status_update("DIAGNOSTICS", f"Pump motor test failed: {e}", level="error")
            results["error"] = str(e)

        return results

    def _run_full_diagnostics(self):
        """Run comprehensive system diagnostics"""
        try:
            # Test I2C
            self._send_status_update("DIAGNOSTICS", "=== I2C Communication Test ===")
            i2c_ok = self._test_i2c_communication()

            # Test GPIO
            self._send_status_update("DIAGNOSTICS", "=== GPIO Pin Test ===")
            gpio_ok = self._test_gpio_pins()

            # Test pump motors
            self._send_status_update("DIAGNOSTICS", "=== Pump Motor Test ===")
            pump_results = self._test_pump_motors()

            # Test printer connectivity
            self._send_status_update("DIAGNOSTICS", "=== Printer Connectivity Test ===")
            printer_ok = False
            if printer_comms:
                try:
                    status = printer_comms.get_status(self.printer_ip)
                    printer_ok = status is not None
                    self._send_status_update("DIAGNOSTICS", f"Printer connection: {'OK' if printer_ok else 'FAILED'}")
                except Exception as e:
                    self._send_status_update("DIAGNOSTICS", f"Printer test failed: {e}", level="error")
            else:
                self._send_status_update("DIAGNOSTICS", "Printer communication module missing", level="warning")

            # Summary
            self._send_status_update("DIAGNOSTICS", "=== Diagnostics Summary ===")
            self._send_status_update("DIAGNOSTICS", f"I2C Communication: {'PASS' if i2c_ok else 'FAIL'}")
            self._send_status_update("DIAGNOSTICS", f"GPIO Pins: {'PASS' if gpio_ok else 'FAIL'}")
            self._send_status_update("DIAGNOSTICS", f"Printer Connection: {'PASS' if printer_ok else 'FAIL'}")
            self._send_status_update("DIAGNOSTICS", f"Pump Motors: {pump_results}")

        except Exception as e:
            self._send_status_update("DIAGNOSTICS", f"Full diagnostics failed: {e}", level="error")

    def _calibrate_all_pumps(self):
        """Start pump calibration wizard for all pumps"""
        try:
            pumps = ['A', 'B', 'C', 'D']
            self._send_status_update("CALIBRATION", "Starting calibration for all pumps...")

            for pump in pumps:
                self._send_status_update("CALIBRATION", f"Calibrating pump {pump}...")
                self._calibrate_single_pump(pump)

            self._send_status_update("CALIBRATION", "All pump calibration completed")

        except Exception as e:
            self._send_status_update("CALIBRATION", f"Pump calibration failed: {e}", level="error")

    def _calibrate_single_pump(self, pump_id: str):
        """Calibrate a specific pump"""
        try:
            if not mmu_control:
                self._send_status_update("CALIBRATION", "MMU control not available", level="error")
                return

            self._send_status_update("CALIBRATION", f"Starting calibration sequence for pump {pump_id}")

            # Run calibration sequence: multiple short runs to measure flow
            test_durations = [5, 10, 15]  # Test runs of different durations
            for duration in test_durations:
                self._send_status_update("CALIBRATION", f"Pump {pump_id}: Running {duration}s test...")
                success = mmu_control.run_pump_by_id(pump_id, 'F', duration)
                if success:
                    self._send_status_update("CALIBRATION", f"Pump {pump_id}: {duration}s test completed")
                else:
                    self._send_status_update("CALIBRATION", f"Pump {pump_id}: {duration}s test failed", level="error")

                # Wait between tests
                time.sleep(2)

            self._send_status_update("CALIBRATION", f"Calibration for pump {pump_id} completed. Please measure dispensed volumes and update pump_profiles.json")

        except Exception as e:
            self._send_status_update("CALIBRATION", f"Calibration for pump {pump_id} failed: {e}", level="error")


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