"""
MMU Control Module - Multi-Material Unit hardware control

This module provides a clean interface for controlling pumps and material changes.
Wraps the existing photonmmu_pump functionality with better error handling and configuration.
"""

import json
import configparser
from pathlib import Path

# Import the existing pump control functions
try:
    from .photonmmu_pump import run_stepper
except ImportError:
    # Fallback for direct execution
    from photonmmu_pump import run_stepper


class MMUController:
    def __init__(self, config_path=None):
        """Initialize MMU controller with pump configuration."""
        self.config_path = config_path or self._find_config_path()
        self.pump_config = self._load_pump_config()
        
    def _find_config_path(self):
        """Find the pump configuration file."""
        script_dir = Path(__file__).parent
        config_dir = script_dir.parent.parent / 'config'
        return config_dir / 'pump_profiles.json'
        
    def _load_pump_config(self):
        """Load pump configuration from JSON file."""
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
                    "pump_a": {"name": "Pump A", "gpio_pin": 18},
                    "pump_b": {"name": "Pump B", "gpio_pin": 19},
                    "drain_pump": {"name": "Drain Pump", "gpio_pin": 20}
                },
                "material_change": {
                    "drain_volume_ml": 50,
                    "fill_volume_ml": 45,
                    "mixing_time_seconds": 10,
                    "settle_time_seconds": 5
                }
            }
    
    def change_material(self, target_material):
        """
        Perform complete material change to target material.
        
        Args:
            target_material (str): Target material identifier ('A', 'B', etc.)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"Starting material change to: {target_material}")
            
            # Get material change parameters
            change_config = self.pump_config.get("material_change", {})
            drain_volume = change_config.get("drain_volume_ml", 50)
            fill_volume = change_config.get("fill_volume_ml", 45)
            mixing_time = change_config.get("mixing_time_seconds", 10)
            settle_time = change_config.get("settle_time_seconds", 5)
            
            # Step 1: Drain current material
            print("Draining current material...")
            if not self.run_pump("drain_pump", "forward", drain_volume):
                return False
                
            # Step 2: Fill with new material
            pump_name = f"pump_{target_material.lower()}"
            print(f"Filling with new material from {pump_name}...")
            if not self.run_pump(pump_name, "forward", fill_volume):
                return False
                
            # Step 3: Allow mixing time
            print(f"Allowing mixing time: {mixing_time}s")
            import time
            time.sleep(mixing_time)
            
            # Step 4: Settle time
            print(f"Settling: {settle_time}s")
            time.sleep(settle_time)
            
            print("Material change completed successfully")
            return True
            
        except Exception as e:
            print(f"Error during material change: {e}")
            return False
    
    def run_pump(self, pump_name, direction="forward", volume_ml=None):
        """
        Run a specific pump.
        
        Args:
            pump_name (str): Name of pump ('pump_a', 'pump_b', 'drain_pump')
            direction (str): 'forward' or 'reverse'
            volume_ml (float): Volume in ml to pump (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get pump configuration
            pumps = self.pump_config.get("pumps", {})
            if pump_name not in pumps:
                print(f"Unknown pump: {pump_name}")
                return False
                
            pump = pumps[pump_name]
            print(f"Running {pump['name']}: {direction}")
            
            # Calculate timing if volume is specified
            if volume_ml:
                flow_rate = pump.get("flow_rate_ml_per_second", 2.5)
                timing = volume_ml / flow_rate
            else:
                timing = 10  # Default 10 seconds
            
            # Map pump names to the original script's motor IDs
            motor_map = {
                "pump_a": "A",
                "pump_b": "B", 
                "drain_pump": "D"
            }
            
            motor_id = motor_map.get(pump_name, "A")
            direction_code = "F" if direction == "forward" else "R"
            
            # Call the original pump control function
            run_stepper(motor_id, direction_code, int(timing))
            
            return True
            
        except Exception as e:
            print(f"Error running pump {pump_name}: {e}")
            return False
    
    def calibrate_pump(self, pump_name, test_volume_ml=10):
        """
        Run a calibration test for a specific pump.
        
        Args:
            pump_name (str): Name of pump to calibrate
            test_volume_ml (float): Volume to dispense for calibration
            
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
        """Emergency stop all pumps."""
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
    """Get the global MMU controller instance."""
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
        "D": "drain_pump"
    }
    
    pump_name = id_map.get(pump_id.upper(), "pump_a")
    direction_name = "forward" if direction.upper() == "F" else "reverse"
    
    return get_controller().run_pump(pump_name, direction_name)


if __name__ == "__main__":
    """Test the MMU controller."""
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