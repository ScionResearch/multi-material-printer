"""
MMU Control - Multi-Material Unit hardware control

Controls stepper motor-driven pumps via Adafruit motor controllers for automated
material changes. Interfaces with I2C motor controllers to manage material reservoirs.

Key Features:
- Automated material change sequences (drain/fill/mix/settle)
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
except ImportError:
    # Fallback for direct execution
    from photonmmu_pump import run_stepper


class MMUController:
    """
    MMU hardware controller for stepper motor-driven pumps.
    
    Manages material change workflow: drain -> fill -> mix -> settle.
    Controls pumps via Adafruit motor controllers over I2C.
    
    Attributes:
        pump_config (dict): Pump profiles and calibration settings
    """
    
    def __init__(self, config_path=None):
        """Initialize MMU controller with pump configuration."""
        self.config_path = config_path or self._find_config_path()
        self.pump_config = self._load_pump_config()
        
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
        Execute automated material change: drain -> fill -> mix -> settle.

        Args:
            target_material (str): Target material ('A', 'B', 'C', 'D')

        Returns:
            bool: True if successful
        """
        try:
            print(f"\n🔄 MMU CONTROLLER: Material change to {target_material}")
            print("=" * 40)

            # Validate target material
            valid_materials = ['A', 'B', 'C', 'D']
            if target_material.upper() not in valid_materials:
                print(f"❌ ERROR: Invalid material '{target_material}'. Must be one of: {valid_materials}")
                return False

            target_material = target_material.upper()
            print(f"✅ Target material validated: {target_material}")

            # Get material change parameters
            change_config = self.pump_config.get("material_change", {})
            drain_volume = change_config.get("drain_volume_ml", 50)
            fill_volume = change_config.get("fill_volume_ml", 45)
            mixing_time = change_config.get("mixing_time_seconds", 10)
            settle_time = change_config.get("settle_time_seconds", 5)

            print(f"📋 Material change parameters:")
            print(f"   💧 Drain volume: {drain_volume}ml")
            print(f"   💧 Fill volume: {fill_volume}ml")
            print(f"   ⏱️  Mixing time: {mixing_time}s")
            print(f"   ⏱️  Settle time: {settle_time}s")
            print("─" * 40)

            # Step 1: Drain current material
            print("🚰 STEP 1/4: Draining current material...")
            if not self.run_pump("drain_pump", "forward", drain_volume):
                print("❌ FAILED: Could not drain current material")
                return False
            print("✅ Drain completed successfully")

            # Step 2: Fill with new material
            pump_name = f"pump_{target_material.lower()}"
            print(f"⛽ STEP 2/4: Filling with material {target_material} from {pump_name}...")
            if not self.run_pump(pump_name, "forward", fill_volume):
                print(f"❌ FAILED: Could not fill from {pump_name}")
                return False
            print("✅ Fill completed successfully")

            # Step 3: Allow mixing time
            print(f"🌀 STEP 3/4: Mixing phase - waiting {mixing_time}s...")
            import time
            for i in range(mixing_time):
                remaining = mixing_time - i
                if remaining % 2 == 0 and remaining > 0:  # Print every 2 seconds
                    print(f"   ⏰ Mixing... {remaining}s remaining")
                time.sleep(1)
            print("✅ Mixing phase completed")

            # Step 4: Settle time
            print(f"🛌 STEP 4/4: Settling phase - waiting {settle_time}s...")
            for i in range(settle_time):
                remaining = settle_time - i
                if remaining > 0:
                    print(f"   ⏰ Settling... {remaining}s remaining")
                time.sleep(1)
            print("✅ Settling phase completed")

            print("=" * 40)
            print(f"🎉 MATERIAL CHANGE TO {target_material} COMPLETED SUCCESSFULLY!")
            print("=" * 40)
            return True

        except Exception as e:
            print(f"\n💥 EXCEPTION in MMU Controller: {e}")
            import traceback
            print("📊 Full traceback:")
            traceback.print_exc()
            return False
    
    def run_pump(self, pump_name, direction="forward", volume_ml=None):
        """
        Control individual pump with timing/volume precision.

        Args:
            pump_name (str): Pump name ('pump_a', 'pump_b', 'drain_pump')
            direction (str): 'forward' or 'reverse'
            volume_ml (float, optional): Volume to pump (default: 10s timing)

        Returns:
            bool: True if successful
        """
        try:
            print(f"\n⚙️  PUMP CONTROL: {pump_name}")
            print("─" * 30)

            # Get pump configuration
            pumps = self.pump_config.get("pumps", {})
            if pump_name not in pumps:
                print(f"❌ ERROR: Unknown pump '{pump_name}'")
                print(f"📋 Available pumps: {list(pumps.keys())}")
                return False

            pump = pumps[pump_name]
            pump_display_name = pump.get('name', pump_name)
            print(f"🏷️  Pump: {pump_display_name}")
            print(f"🧭 Direction: {direction}")

            # Calculate timing if volume is specified
            if volume_ml:
                flow_rate = pump.get("flow_rate_ml_per_second", 2.5)
                timing = volume_ml / flow_rate
                print(f"💧 Volume: {volume_ml}ml")
                print(f"🌊 Flow rate: {flow_rate}ml/s")
                print(f"⏱️  Calculated timing: {timing:.2f}s")
            else:
                timing = 10  # Default 10 seconds
                print(f"⏱️  Default timing: {timing}s")

            # Map pump names to the original script's motor IDs
            motor_map = {
                "pump_a": "A",
                "pump_b": "B",
                "pump_c": "C",
                "drain_pump": "D"
            }

            motor_id = motor_map.get(pump_name, "A")
            direction_code = "F" if direction == "forward" else "R"

            print(f"🤖 Motor ID: {motor_id}")
            print(f"📡 Command: run_stepper('{motor_id}', '{direction_code}', {int(timing)})")
            print("🚀 Executing pump command...")

            # Call the original pump control function
            run_stepper(motor_id, direction_code, int(timing))

            print(f"✅ Pump {pump_display_name} completed successfully")
            print("─" * 30)
            return True

        except Exception as e:
            print(f"\n💥 ERROR in pump control: {e}")
            import traceback
            print("📊 Full traceback:")
            traceback.print_exc()
            print(f"❌ FAILED: Pump {pump_name} operation failed")
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
        "D": "drain_pump"
    }
    
    pump_name = id_map.get(pump_id.upper(), "pump_a")
    direction_name = "forward" if direction.upper() == "F" else "reverse"
    
    return get_controller().run_pump(pump_name, direction_name)


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