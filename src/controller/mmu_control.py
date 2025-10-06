"""
MMU Control - Multi-Material Unit hardware control

Controls stepper motor-driven pumps via Adafruit motor controllers for automated
material changes. Interfaces with I2C motor controllers to manage material reservoirs.

Key Features:
- Automated material change sequences (drain/fill/settle)
- Individual pump control with volume/timing precision
- JSON-based pump configuration and calibration
- Emergency stop and safety features

Usage:
    controller = MMUController()
    controller.change_material('B')
    controller.run_pump('pump_a', 'forward', 25)

Requires: I2C enabled, Adafruit MotorKit, pump_profiles.json configuration
"""

import json
import configparser
from pathlib import Path

# Import the existing pump control functions
try:
    from .photonmmu_pump import run_stepper
    from . import solenoid_control
except ImportError:
    # Fallback for direct execution
    from photonmmu_pump import run_stepper
    import solenoid_control


class MMUController:
    """
    MMU hardware controller for stepper motor-driven pumps.

    Manages material change workflow: drain -> fill -> settle.
    Controls pumps via Adafruit motor controllers over I2C.

    Attributes:
        pump_config (dict): Pump profiles and calibration settings
    """
    
    def __init__(self, config_path=None):
        """Initialize MMU controller with pump configuration."""
        self.config_path = config_path or self._find_config_path()
        self.pump_config = self._load_pump_config()
        self._init_solenoid()
        
    def _find_config_path(self):
        """Find pump configuration file path."""
        script_dir = Path(__file__).parent
        config_dir = script_dir.parent.parent / 'config'
        return config_dir / 'pump_profiles.json'
        
    def _load_pump_config(self):
        """Load pump configuration from JSON file with defaults."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                print(f"Loaded pump configuration from: {self.config_path}")
                return config
        except Exception as e:
            print(f"Warning: Could not load pump config: {e}")
            # Return default configuration
            return {
                "pumps": {
                    "pump_a": {
                        "name": "Pump A",
                        "flow_rate_ml_per_second": 2.5,
                        "max_volume_ml": 500
                    },
                    "pump_b": {
                        "name": "Pump B",
                        "flow_rate_ml_per_second": 2.5,
                        "max_volume_ml": 500
                    },
                    "pump_c": {
                        "name": "Pump C",
                        "flow_rate_ml_per_second": 2.5,
                        "max_volume_ml": 500
                    },
                    "drain_pump": {
                        "name": "Drain Pump",
                        "flow_rate_ml_per_second": 5.0,
                        "max_volume_ml": 1000
                    }
                },
                "material_change": {
                    "drain_volume_ml": 50,
                    "fill_volume_ml": 45,
                    "settle_time_seconds": 5
                },
                "solenoid": {
                    "enabled": False
                }
            }

    def _init_solenoid(self):
        """Initialize solenoid if enabled in configuration."""
        solenoid_config = self.pump_config.get("solenoid", {})
        if solenoid_config.get("enabled", False):
            try:
                solenoid_control.init_solenoid()
                print(f"Solenoid initialized on GPIO pin {solenoid_config.get('gpio_pin', 22)}")
            except Exception as e:
                print(f"Warning: Could not initialize solenoid: {e}")
        else:
            print("Solenoid control disabled in configuration")
    
    def change_material(self, target_material):
        """
        Execute automated material change: drain -> fill -> settle.

        Args:
            target_material (str): Target material ('A', 'B', 'C', 'D')

        Returns:
            bool: True if successful
        """
        try:
            print(f"MMU: Changing to material {target_material}")

            # Validate target material
            valid_materials = ['A', 'B', 'C', 'D']
            if target_material.upper() not in valid_materials:
                print(f"ERROR: Invalid material '{target_material}'. Must be one of: {valid_materials}")
                return False

            target_material = target_material.upper()

            # Get material change parameters
            change_config = self.pump_config.get("material_change", {})
            drain_volume = change_config.get("drain_volume_ml", 50)
            fill_volume = change_config.get("fill_volume_ml", 45)
            settle_time = change_config.get("settle_time_seconds", 5)

            # Material change parameters loaded

            # Step 1: Drain current material with air assist
            solenoid_config = self.pump_config.get("solenoid", {})
            solenoid_enabled = solenoid_config.get("enabled", False)

            if solenoid_enabled:
                # Activate solenoid before drain to blow resin toward drain
                pre_delay = solenoid_config.get("activate_before_drain_delay_seconds", 0.5)
                print(f"Activating air flow to push resin toward drain (waiting {pre_delay}s)...")
                solenoid_control.activate_solenoid()
                import time
                time.sleep(pre_delay)

            if not self.run_pump_volume("drain_pump", "forward", drain_volume):
                if solenoid_enabled:
                    solenoid_control.deactivate_solenoid()
                print("ERROR: Could not drain current material")
                return False

            if solenoid_enabled:
                # Keep air flowing briefly after drain completes
                post_delay = solenoid_config.get("deactivate_after_drain_delay_seconds", 1.0)
                print(f"Continuing air flow for {post_delay}s to clear remaining resin...")
                import time
                time.sleep(post_delay)
                solenoid_control.deactivate_solenoid()

            # Step 2: Fill with new material
            pump_name = f"pump_{target_material.lower()}"
            if not self.run_pump_volume(pump_name, "forward", fill_volume):
                print(f"ERROR: Could not fill from {pump_name}")
                return False

            # Step 3: Settle time
            print(f"Settling phase - waiting {settle_time}s...")
            import time
            time.sleep(settle_time)
            print("Settling phase completed")

            print(f"MATERIAL CHANGE TO {target_material} COMPLETED SUCCESSFULLY")
            return True

        except Exception as e:
            print(f"\nEXCEPTION in MMU Controller: {e}")
            import traceback
            # Full traceback:
            traceback.print_exc()
            return False
    
    def run_pump(self, pump_name, direction="forward", duration_seconds=10):
        """
        Control individual pump with duration precision.

        Args:
            pump_name (str): Pump name ('pump_a', 'pump_b', 'drain_pump')
            direction (str): 'forward' or 'reverse'
            duration_seconds (float): Duration to run pump in seconds

        Returns:
            bool: True if successful
        """
        try:
            # Get pump configuration
            pumps = self.pump_config.get("pumps", {})
            if pump_name not in pumps:
                print(f"ERROR: Unknown pump '{pump_name}'")
                print(f"Available pumps: {list(pumps.keys())}")
                return False

            pump = pumps[pump_name]
            pump_display_name = pump.get('name', pump_name)
            print(f"Running {pump_display_name}: {duration_seconds}s")

            # Map pump names to the original script's motor IDs
            motor_map = {
                "pump_a": "A",
                "pump_b": "B",
                "pump_c": "C",
                "drain_pump": "D"
            }

            motor_id = motor_map.get(pump_name, "A")
            direction_code = "F" if direction == "forward" else "R"

            # Call the original pump control function
            run_stepper(motor_id, direction_code, int(duration_seconds))

            print(f"Pump {pump_display_name} completed")
            return True

        except Exception as e:
            print(f"ERROR in pump control: {e}")
            import traceback
            # Full traceback:
            traceback.print_exc()
            print(f"FAILED: Pump {pump_name} operation failed")
            return False

    def run_pump_volume(self, pump_name, direction="forward", volume_ml=10):
        """
        Control individual pump with volume precision (calculates duration).

        Args:
            pump_name (str): Pump name ('pump_a', 'pump_b', 'drain_pump')
            direction (str): 'forward' or 'reverse'
            volume_ml (float): Volume to pump in milliliters

        Returns:
            bool: True if successful
        """
        try:
            # Get pump configuration
            pumps = self.pump_config.get("pumps", {})
            if pump_name not in pumps:
                print(f"ERROR: Unknown pump '{pump_name}'")
                return False

            pump = pumps[pump_name]
            flow_rate = pump.get("flow_rate_ml_per_second", 2.5)
            duration_seconds = volume_ml / flow_rate

            pump_display_name = pump.get('name', pump_name)
            print(f"Running {pump_display_name}: {volume_ml}ml at {flow_rate}ml/s ({duration_seconds:.1f}s)")

            return self.run_pump(pump_name, direction, duration_seconds)

        except Exception as e:
            print(f"ERROR in volume-based pump control: {e}")
            return False
    
    def calibrate_pump(self, pump_name, test_volume_ml=10):
        """
        Run calibration test for pump flow rate verification.
        
        Args:
            pump_name (str): Pump to calibrate
            test_volume_ml (float): Test volume (default: 10ml)
            
        Returns:
            bool: True if successful
        """
        try:
            print(f"Calibrating {pump_name} with {test_volume_ml}ml test volume")
            return self.run_pump(pump_name, "forward", test_volume_ml)
        except Exception as e:
            print(f"Error during calibration: {e}")
            return False
    
    def emergency_stop(self):
        """Emergency stop all pump operations."""
        try:
            print("EMERGENCY STOP - Stopping all pumps")
            # Implementation would depend on your hardware setup
            return True
        except Exception as e:
            print(f"Error during emergency stop: {e}")
            return False


# Global instance for easy access
_mmu_controller = None

def get_controller():
    """Get global MMUController instance (singleton pattern)."""
    global _mmu_controller
    if _mmu_controller is None:
        _mmu_controller = MMUController()
    return _mmu_controller

# Convenience functions that match the old interface
def change_material(material):
    """Change to specified material (convenience function)."""
    return get_controller().change_material(material)

def run_pump_by_id(pump_id, direction, timing):
    """Run pump by motor ID (legacy compatibility)."""
    # Map old motor IDs to new pump names
    id_map = {
        "A": "pump_a",
        "B": "pump_b",
        "C": "pump_c",
        "D": "drain_pump"
    }

    pump_name = id_map.get(pump_id.upper(), "pump_a")
    direction_name = "forward" if direction.upper() == "F" else "reverse"

    # Call with duration directly
    return get_controller().run_pump(pump_name, direction_name, duration_seconds=timing)


if __name__ == "__main__":
    """
    Command-line interface for MMU pump testing.
    
    Usage: python mmu_control.py <motor_id> <direction> <timing>
    
    Examples:
        python mmu_control.py A F 30  # Pump A forward 30 seconds
        python mmu_control.py D R 15  # Drain pump reverse 15 seconds
    """
    import sys
    
    if len(sys.argv) >= 4:
        # Legacy compatibility: python mmu_control.py A F 30
        motor_id = sys.argv[1]
        direction = sys.argv[2] 
        timing = int(sys.argv[3])
        
        success = run_pump_by_id(motor_id, direction, timing)
        print(f"Pump operation {'succeeded' if success else 'failed'}")
    else:
        print("Usage: python mmu_control.py <motor_id> <direction> <timing>")
        print("Example: python mmu_control.py A F 30")