#!/usr/bin/env python3
"""
Shared Status Communication System
=================================

This module provides a file-based communication system that allows both
the Qt C++ GUI and the web app to communicate with the print manager.

Status files are stored in a shared directory and updated in real-time.
Both interfaces can read status and send commands through these files.
"""

import json
import os
import time
import threading
import platform
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Platform-specific imports for file locking
if platform.system() != 'Windows':
    import fcntl
else:
    import msvcrt

class SharedStatusManager:
    """
    Manages shared status files for communication between GUIs and print manager.
    """

    def __init__(self, status_dir: str = None):
        """Initialize shared status manager with status directory."""
        if status_dir is None:
            # Default to project root shared status directory
            project_root = Path(__file__).parent.parent.parent
            status_dir = project_root / "shared_status"

        self.status_dir = Path(status_dir)
        self.status_dir.mkdir(exist_ok=True)

        # Define status file paths
        self.status_file = self.status_dir / "printer_status.json"
        self.command_file = self.status_dir / "pending_commands.json"
        self.recipe_file = self.status_dir / "recipe_progress.json"
        self.pump_file = self.status_dir / "pump_status.json"
        self.log_file = self.status_dir / "activity_log.json"

        # Initialize empty files if they don't exist
        self._initialize_status_files()

        # Lock for thread safety
        self._lock = threading.Lock()

    def _initialize_status_files(self):
        """Initialize status files with default values if they don't exist."""
        default_files = {
            self.status_file: {
                "printer_connected": False,
                "printer_status": "Unknown",
                "current_layer": 0,
                "total_layers": 0,
                "progress_percent": 0.0,
                "print_time_elapsed": 0,
                "print_time_remaining": 0,
                "last_update": datetime.now().isoformat()
            },
            self.command_file: {
                "pending_commands": [],
                "last_command_id": 0,
                "last_processed": datetime.now().isoformat()
            },
            self.recipe_file: {
                "recipe_active": False,
                "current_step": 0,
                "total_steps": 0,
                "recipe_items": [],
                "next_change_layer": 0,
                "next_material": "None",
                "operation_start_time": None,
                "operation_duration": 0,
                "last_update": datetime.now().isoformat()
            },
            self.pump_file: {
                "pump_a": {"status": "idle", "last_operation": None, "duration": 0},
                "pump_b": {"status": "idle", "last_operation": None, "duration": 0},
                "pump_c": {"status": "idle", "last_operation": None, "duration": 0},
                "drain_pump": {"status": "idle", "last_operation": None, "duration": 0},
                "current_operation": "idle",
                "operation_step": "",
                "step_progress": 0,
                "last_update": datetime.now().isoformat()
            },
            self.log_file: {
                "activity_log": [
                    {
                        "timestamp": datetime.now().isoformat(),
                        "level": "INFO",
                        "message": "Shared status system initialized",
                        "component": "shared_status"
                    }
                ],
                "max_entries": 1000
            }
        }

        for file_path, default_data in default_files.items():
            if not file_path.exists():
                self._write_json_file(file_path, default_data)

    def _read_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Safely read JSON file with file locking."""
        try:
            with open(file_path, 'r') as f:
                if platform.system() != 'Windows':
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared read lock
                else:
                    # Windows file locking using msvcrt
                    msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)

                data = json.load(f)

                if platform.system() != 'Windows':
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Unlock
                else:
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)

                return data
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading {file_path}: {e}")
            return {}

    def _write_json_file(self, file_path: Path, data: Dict[str, Any]):
        """Safely write JSON file with file locking."""
        try:
            with open(file_path, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive write lock
                json.dump(data, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Unlock
        except Exception as e:
            print(f"Error writing {file_path}: {e}")

    def update_printer_status(self, **kwargs):
        """Update printer status with provided parameters."""
        with self._lock:
            current_status = self._read_json_file(self.status_file)
            current_status.update(kwargs)
            current_status["last_update"] = datetime.now().isoformat()
            self._write_json_file(self.status_file, current_status)

    def get_printer_status(self) -> Dict[str, Any]:
        """Get current printer status."""
        return self._read_json_file(self.status_file)

    def update_pump_status(self, pump_name: str = None, **kwargs):
        """Update pump status for specific pump or general pump info."""
        with self._lock:
            current_status = self._read_json_file(self.pump_file)

            if pump_name and pump_name in current_status:
                current_status[pump_name].update(kwargs)
            else:
                # Update general pump operation info
                for key, value in kwargs.items():
                    if key in current_status:
                        current_status[key] = value

            current_status["last_update"] = datetime.now().isoformat()
            self._write_json_file(self.pump_file, current_status)

    def get_pump_status(self) -> Dict[str, Any]:
        """Get current pump status."""
        return self._read_json_file(self.pump_file)

    def update_recipe_progress(self, **kwargs):
        """Update recipe progress information."""
        with self._lock:
            current_progress = self._read_json_file(self.recipe_file)
            current_progress.update(kwargs)
            current_progress["last_update"] = datetime.now().isoformat()
            self._write_json_file(self.recipe_file, current_progress)

    def get_recipe_progress(self) -> Dict[str, Any]:
        """Get current recipe progress."""
        return self._read_json_file(self.recipe_file)

    def add_command(self, command_type: str, parameters: Dict[str, Any] = None) -> int:
        """Add a command to the pending commands queue."""
        with self._lock:
            command_data = self._read_json_file(self.command_file)
            command_id = command_data["last_command_id"] + 1

            new_command = {
                "id": command_id,
                "command": command_type,
                "parameters": parameters or {},
                "timestamp": datetime.now().isoformat(),
                "status": "pending"
            }

            command_data["pending_commands"].append(new_command)
            command_data["last_command_id"] = command_id
            self._write_json_file(self.command_file, command_data)

            return command_id

    def get_pending_commands(self) -> list:
        """Get list of pending commands."""
        command_data = self._read_json_file(self.command_file)
        return command_data.get("pending_commands", [])

    def mark_command_processed(self, command_id: int, status: str = "completed"):
        """Mark a command as processed and remove from pending list."""
        with self._lock:
            command_data = self._read_json_file(self.command_file)
            command_data["pending_commands"] = [
                cmd for cmd in command_data["pending_commands"]
                if cmd["id"] != command_id
            ]
            command_data["last_processed"] = datetime.now().isoformat()
            self._write_json_file(self.command_file, command_data)

    def log_activity(self, level: str, message: str, component: str = "system"):
        """Add entry to activity log."""
        with self._lock:
            log_data = self._read_json_file(self.log_file)

            new_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": level.upper(),
                "message": message,
                "component": component
            }

            log_data["activity_log"].append(new_entry)

            # Keep only the last max_entries
            max_entries = log_data.get("max_entries", 1000)
            if len(log_data["activity_log"]) > max_entries:
                log_data["activity_log"] = log_data["activity_log"][-max_entries:]

            self._write_json_file(self.log_file, log_data)

    def get_activity_log(self, count: int = 50) -> list:
        """Get recent activity log entries."""
        log_data = self._read_json_file(self.log_file)
        activity_log = log_data.get("activity_log", [])
        return activity_log[-count:] if count else activity_log

    def get_all_status(self) -> Dict[str, Any]:
        """Get combined status from all files."""
        return {
            "printer": self.get_printer_status(),
            "pumps": self.get_pump_status(),
            "recipe": self.get_recipe_progress(),
            "activity_log": self.get_activity_log(20),
            "last_update": datetime.now().isoformat()
        }

    def cleanup_old_logs(self, days: int = 7):
        """Remove log entries older than specified days."""
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)

        with self._lock:
            log_data = self._read_json_file(self.log_file)
            activity_log = log_data.get("activity_log", [])

            filtered_log = []
            for entry in activity_log:
                try:
                    entry_time = datetime.fromisoformat(entry["timestamp"]).timestamp()
                    if entry_time >= cutoff_time:
                        filtered_log.append(entry)
                except (ValueError, KeyError):
                    # Keep entries with invalid timestamps
                    filtered_log.append(entry)

            log_data["activity_log"] = filtered_log
            self._write_json_file(self.log_file, log_data)


# Global instance for easy access
_shared_status = None

def get_shared_status() -> SharedStatusManager:
    """Get global shared status manager instance."""
    global _shared_status
    if _shared_status is None:
        _shared_status = SharedStatusManager()
    return _shared_status


if __name__ == "__main__":
    # Test the shared status system
    status_mgr = SharedStatusManager()

    # Test printer status update
    status_mgr.update_printer_status(
        printer_connected=True,
        printer_status="Ready",
        current_layer=5,
        total_layers=100
    )

    # Test pump status update
    status_mgr.update_pump_status("pump_a", status="running", duration=15.5)

    # Test recipe progress
    status_mgr.update_recipe_progress(
        recipe_active=True,
        current_step=2,
        total_steps=5,
        next_change_layer=10,
        next_material="Material B"
    )

    # Test command
    cmd_id = status_mgr.add_command("start_print", {"file": "test.gcode"})
    print(f"Added command with ID: {cmd_id}")

    # Test activity log
    status_mgr.log_activity("INFO", "System test completed", "test")

    # Get all status
    all_status = status_mgr.get_all_status()
    print("Current status:")
    print(json.dumps(all_status, indent=2, default=str))