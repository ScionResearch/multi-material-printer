#!/usr/bin/env python3
"""
WebSocket-based IPC Communication System
========================================

This module replaces the file-based shared_status.py with a real-time
WebSocket communication system. The print manager connects directly to
the Flask-SocketIO server as a client, eliminating file I/O overhead
and race conditions.

Architecture:
- Web App: Flask-SocketIO server (host)
- Print Manager: SocketIO client (connects to web app)
- Qt GUI: Can connect as additional client or use HTTP API

Benefits:
- Real-time bidirectional communication
- No file system dependencies
- Automatic reconnection handling
- Built-in error handling and timeouts
- Scalable to multiple clients
"""

import json
import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from queue import Queue, Empty

try:
    import socketio
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False

logger = logging.getLogger(__name__)

class WebSocketIPCClient:
    """
    SocketIO client for print manager to communicate with web application.

    This client connects to the Flask-SocketIO server and provides:
    - Command reception from web app
    - Status updates to web app
    - Real-time bidirectional communication
    - Automatic reconnection
    """

    def __init__(self, server_url: str = "http://localhost:5000", namespace: str = "/"):
        """
        Initialize WebSocket IPC client.

        Args:
            server_url: URL of the Flask-SocketIO server
            namespace: SocketIO namespace to use
        """
        self.server_url = server_url
        self.namespace = namespace
        self.sio = None
        self.connected = False
        self.connection_thread = None
        self.command_queue = Queue()
        self.command_handlers = {}
        self.status_cache = {}

        # Event callbacks
        self.on_command_received = None
        self.on_connection_changed = None

        # Auto-reconnect settings
        self.auto_reconnect = True
        self.reconnect_delay = 5  # seconds

        if not SOCKETIO_AVAILABLE:
            logger.error("python-socketio not available. Install with: pip install python-socketio")
            raise ImportError("python-socketio library required for WebSocket IPC")

    def connect(self) -> bool:
        """
        Connect to the SocketIO server.

        Returns:
            bool: True if connection successful
        """
        try:
            if self.sio is None:
                self.sio = socketio.Client(
                    reconnection=self.auto_reconnect,
                    reconnection_delay=self.reconnect_delay,
                    logger=False,  # Disable socketio internal logging
                    engineio_logger=False
                )
                self._setup_event_handlers()

            logger.info(f"Connecting to SocketIO server at {self.server_url}")
            self.sio.connect(self.server_url, namespaces=[self.namespace])

            # Wait a moment for connection to establish
            time.sleep(0.5)

            return self.connected

        except Exception as e:
            logger.error(f"Failed to connect to SocketIO server: {e}")
            return False

    def disconnect(self):
        """Disconnect from the SocketIO server."""
        if self.sio and self.connected:
            logger.info("Disconnecting from SocketIO server")
            self.sio.disconnect()

    def _setup_event_handlers(self):
        """Setup SocketIO event handlers."""

        @self.sio.event
        def connect():
            """Handle successful connection."""
            self.connected = True
            logger.info("Connected to SocketIO server")

            # Announce ourselves as the print manager
            logger.info("Sending client_register event to server...")
            result = self.emit('client_register', {
                'client_type': 'print_manager',
                'capabilities': ['print_control', 'mmu_control', 'status_monitoring'],
                'timestamp': datetime.now().isoformat()
            })
            logger.info(f"client_register event sent: {result}")

            if self.on_connection_changed:
                self.on_connection_changed(True)

        @self.sio.event
        def disconnect():
            """Handle disconnection."""
            self.connected = False
            logger.warning("Disconnected from SocketIO server")

            if self.on_connection_changed:
                self.on_connection_changed(False)

        @self.sio.event
        def connect_error(data):
            """Handle connection error."""
            logger.error(f"Connection error: {data}")
            self.connected = False

        @self.sio.event
        def command(data):
            """Handle incoming commands from web app."""
            try:
                logger.debug(f"Received command: {data}")

                # Add command to queue for processing
                command_data = {
                    'command_id': data.get('command_id'),
                    'command_type': data.get('type'),
                    'parameters': data.get('parameters', {}),
                    'timestamp': data.get('timestamp', datetime.now().isoformat())
                }

                self.command_queue.put(command_data)

                # Call callback if registered
                if self.on_command_received:
                    self.on_command_received(command_data)

            except Exception as e:
                logger.error(f"Error processing command: {e}")

        @self.sio.event
        def status_request(data):
            """Handle status request from web app."""
            try:
                # Send current cached status
                self.emit('status_response', {
                    'request_id': data.get('request_id'),
                    'status': self.status_cache,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error handling status request: {e}")

    def emit(self, event: str, data: Dict[str, Any]) -> bool:
        """
        Emit an event to the server.

        Args:
            event: Event name
            data: Event data

        Returns:
            bool: True if emission successful
        """
        try:
            if self.sio and self.connected:
                self.sio.emit(event, data, namespace=self.namespace)
                return True
            else:
                logger.warning(f"Cannot emit {event}: not connected")
                return False
        except Exception as e:
            logger.error(f"Error emitting {event}: {e}")
            return False

    def send_status_update(self, component: str, status: str, data: Dict[str, Any] = None, level: str = "info"):
        """
        Send status update to web app.

        Args:
            component: Component name (PRINTER, PUMP, SEQUENCE, etc.)
            status: Status message
            data: Additional status data
            level: Log level (info, warning, error)
        """
        update_data = {
            'component': component,
            'status': status,
            'level': level,
            'timestamp': datetime.now().isoformat(),
            'data': data or {}
        }

        # Cache the status
        self.status_cache[component.lower()] = update_data

        # Send to web app
        self.emit('status_update', update_data)

    def send_log_message(self, level: str, message: str, component: str = "SYSTEM"):
        """
        Send log message to web app.

        Args:
            level: Log level (info, warning, error, debug)
            message: Log message
            component: Component that generated the log
        """
        log_data = {
            'level': level,
            'message': message,
            'component': component,
            'timestamp': datetime.now().isoformat()
        }

        self.emit('log_message', log_data)

    def get_next_command(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        Get the next command from the queue.

        Args:
            timeout: Timeout in seconds

        Returns:
            Command data or None if timeout
        """
        try:
            return self.command_queue.get(timeout=timeout)
        except Empty:
            return None

    def mark_command_processed(self, command_id: str, success: bool = True, result: str = ""):
        """
        Mark a command as processed.

        Args:
            command_id: ID of the processed command
            success: Whether the command succeeded
            result: Result message
        """
        self.emit('command_result', {
            'command_id': command_id,
            'success': success,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })

    def is_connected(self) -> bool:
        """Check if connected to server."""
        return self.connected

    def start_background_connection(self):
        """Start connection in background thread with auto-reconnect."""
        if self.connection_thread and self.connection_thread.is_alive():
            return

        def connection_worker():
            while self.auto_reconnect:
                if not self.connected:
                    try:
                        self.connect()
                    except Exception as e:
                        logger.error(f"Background connection failed: {e}")

                time.sleep(self.reconnect_delay)

        self.connection_thread = threading.Thread(target=connection_worker, daemon=True)
        self.connection_thread.start()


class WebSocketIPCManager:
    """
    Manager class that provides a similar interface to the old SharedStatusManager
    but uses WebSocket communication instead of files.

    This is a drop-in replacement for shared_status.py usage.
    """

    def __init__(self, server_url: str = "http://localhost:5000"):
        """Initialize WebSocket IPC manager."""
        self.client = WebSocketIPCClient(server_url)
        self.command_id_counter = 0
        self._lock = threading.Lock()

    def connect(self) -> bool:
        """Connect to the server."""
        return self.client.connect()

    def disconnect(self):
        """Disconnect from the server."""
        self.client.disconnect()

    def add_command(self, command_type: str, parameters: Dict[str, Any] = None) -> str:
        """
        Add a command for processing (for web app compatibility).

        This method maintains compatibility with the old shared_status interface
        but immediately sends the command via WebSocket instead of writing to file.

        Args:
            command_type: Type of command
            parameters: Command parameters

        Returns:
            Command ID
        """
        with self._lock:
            self.command_id_counter += 1
            command_id = f"cmd_{self.command_id_counter}_{int(time.time())}"

        command_data = {
            'command_id': command_id,
            'type': command_type,
            'parameters': parameters or {},
            'timestamp': datetime.now().isoformat()
        }

        # Send command immediately via WebSocket
        if self.client.emit('command', command_data):
            logger.debug(f"Sent command {command_id}: {command_type}")
            return command_id
        else:
            logger.error(f"Failed to send command {command_id}: {command_type}")
            return ""

    def update_status(self, component: str, status_data: Dict[str, Any]):
        """
        Update status (for compatibility with old interface).

        Args:
            component: Component name
            status_data: Status data
        """
        self.client.send_status_update(
            component=component,
            status=status_data.get('status', ''),
            data=status_data
        )

    def is_connected(self) -> bool:
        """Check if connected to server."""
        return self.client.is_connected()


# Compatibility functions for drop-in replacement
def get_shared_status_manager(server_url: str = "http://localhost:5000") -> WebSocketIPCManager:
    """Get a WebSocket IPC manager (replaces file-based shared status)."""
    return WebSocketIPCManager(server_url)


# Global instance for backward compatibility
_global_manager = None

def get_manager() -> WebSocketIPCManager:
    """Get global WebSocket IPC manager instance."""
    global _global_manager
    if _global_manager is None:
        _global_manager = WebSocketIPCManager()
    return _global_manager