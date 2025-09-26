"""
Print Manager - Automated multi-material printing orchestration

Central coordinator for multi-material printing operations. Monitors printer status
via uart-wifi library and triggers material changes at specified layers.

Key Features:
- Real-time printer monitoring and layer detection
- Recipe-based material changes (format: "A,50:B,120:C,200")  
- Coordinated pause/resume operations during material swaps
- Integration with printer_comms and mmu_control modules

Usage:
    manager = PrintManager()
    manager.load_recipe('recipe.txt')
    manager.start_monitoring()

Requires: printer_comms (uart-wifi), mmu_control, configuration files
"""

import socket
import time
import argparse
import json
import configparser
import os
import sys
from pathlib import Path

# Import other controller modules with robust error handling
mmu_control = None
printer_comms = None

print("DEBUG: Attempting to import controller modules...")
print(f"DEBUG: Current working directory: {os.getcwd()}")
print(f"DEBUG: Script location: {__file__}")
print(f"DEBUG: Python path: {sys.path}")

try:
    # Try relative imports first (package mode)
    from . import mmu_control
    from . import printer_comms
    print("DEBUG: ✓ Relative imports successful")
except ImportError as e:
    print(f"DEBUG: Relative import failed: {e}")
    try:
        # Try absolute imports (direct execution mode)
        import mmu_control
        import printer_comms
        print("DEBUG: ✓ Absolute imports successful")
    except ImportError as e2:
        print(f"DEBUG: Absolute import failed: {e2}")
        try:
            # Try adding current directory to path
            script_dir = Path(__file__).parent
            sys.path.insert(0, str(script_dir))
            import mmu_control
            import printer_comms
            print("DEBUG: ✓ Path-adjusted imports successful")
        except ImportError as e3:
            print(f"FATAL: All import methods failed!")
            print(f"  Relative import error: {e}")
            print(f"  Absolute import error: {e2}")
            print(f"  Path-adjusted import error: {e3}")
            print(f"  Current working directory: {os.getcwd()}")
            print(f"  Script directory: {Path(__file__).parent}")
            print(f"  Python path: {sys.path}")

            # Force flush output before exiting
            sys.stdout.flush()
            sys.stderr.flush()
            raise ImportError("Could not import required controller modules") from e3

print("DEBUG: Import section completed successfully")
sys.stdout.flush()

class PrintManager:
    """
    Automated multi-material printing coordinator.
    
    Monitors printer progress via uart-wifi and triggers material changes at 
    specified layers. Integrates with printer_comms and mmu_control modules.
    
    Attributes:
        printer_ip (str): Target printer IP
        recipe (dict): Layer->material mapping
    """
    
    def __init__(self, config_path=None):
        """Initialize print manager with configuration."""
        self.config_path = config_path or self._find_config_path()
        self.config = self._load_config()
        self.printer_ip = self.config.get('printer', 'ip_address', fallback='192.168.4.2')
        self.printer_port = self.config.getint('printer', 'port', fallback=80)
        self.timeout = self.config.getint('printer', 'timeout', fallback=10)
        
        # Load recipe if provided
        self.recipe = {}
        
    def _find_config_path(self):
        """Find configuration file path."""
        script_dir = Path(__file__).parent
        config_dir = script_dir.parent.parent / 'config'
        return config_dir / 'network_settings.ini'
    
    def _load_config(self):
        """Load configuration from INI file."""
        config = configparser.ConfigParser()
        try:
            config.read(self.config_path)
            print(f"Loaded configuration from: {self.config_path}")
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
            # Use defaults
        return config
    
    def load_recipe(self, recipe_path):
        """
        Load material change recipe from file.

        Args:
            recipe_path (str): Path to recipe file

        Returns:
            bool: True if successful

        Format: "A,50:B,120:C,200" (material,layer pairs)
        """
        try:
            print(f"Loading recipe: {recipe_path}")

            # Check if file exists
            import os
            if not os.path.exists(recipe_path):
                print(f"ERROR: Recipe file does not exist: {recipe_path}")
                return False

            # Read file contents
            with open(recipe_path, 'r') as f:
                recipe_text = f.read().strip()

            if not recipe_text:
                print("WARNING: Recipe file is empty")
                self.recipe = {}
                return True

            # Parse recipe format: "A,50:B,120"
            self.recipe = {}
            valid_materials = ['A', 'B', 'C', 'D']
            pairs = recipe_text.split(':')

            for i, pair in enumerate(pairs):
                if ',' not in pair:
                    print(f"WARNING: Skipping invalid pair (no comma): '{pair}'")
                    continue

                try:
                    material, layer_str = pair.split(',', 1)  # Split only on first comma
                    material = material.strip().upper()
                    layer_str = layer_str.strip()

                    # Validate material
                    if material not in valid_materials:
                        print(f"ERROR: Invalid material '{material}'. Must be one of: {valid_materials}")
                        continue

                    # Validate layer number
                    try:
                        layer = int(layer_str)
                        if layer <= 0:
                            print(f"ERROR: Invalid layer number '{layer}'. Must be positive integer.")
                            continue
                    except ValueError:
                        print(f"ERROR: Invalid layer number '{layer_str}'. Must be integer.")
                        continue

                    # Check for duplicate layers
                    if layer in self.recipe:
                        print(f"WARNING: Duplicate layer {layer}. Overriding {self.recipe[layer]} with {material}")

                    self.recipe[layer] = material
                    # Added layer mapping

                except Exception as e:
                    print(f"ERROR: Failed to parse pair '{pair}': {e}")
                    continue

            if self.recipe:
                sorted_layers = sorted(self.recipe.keys())
                print(f"Successfully loaded {len(self.recipe)} material changes")
                print(f"Layer range: {min(sorted_layers)} to {max(sorted_layers)}")
            else:
                print("WARNING: No valid material changes found in recipe")
            return True

        except Exception as e:
            print(f"CRITICAL ERROR loading recipe: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start_monitoring(self, recipe_path=None):
        """
        Start automated printer monitoring and material changes.

        Args:
            recipe_path (str, optional): Recipe file to load

        Polls printer every 5 seconds, triggers material changes at target layers.
        """
        print("Multi-material print manager starting...")

        if recipe_path and not self.load_recipe(recipe_path):
            print("CRITICAL ERROR: Failed to load recipe, aborting.")
            return False

        if not self.recipe:
            print("WARNING: No recipe loaded - monitoring only")
        else:
            recipe_summary = dict(sorted(self.recipe.items()))
            print(f"Recipe loaded: {recipe_summary}")

        print(f"Monitoring printer {self.printer_ip} every 5 seconds...")

        try:
            loop_count = 0
            while True:
                loop_count += 1
                if loop_count % 10 == 1:  # Log every 10th cycle
                    print(f"\nMonitoring cycle #{loop_count} - {time.strftime('%H:%M:%S')}")

                # Get current printer status
                status = self._get_printer_status()
                if not status:
                    print("ERROR: Lost connection to printer - retrying in 5 seconds")
                    time.sleep(5)
                    continue

                # Extract current layer
                current_layer = self._extract_current_layer(status)
                if current_layer is None:
                    if loop_count % 20 == 1:  # Only show warning every 20 cycles
                        print("WARNING: Could not determine current layer")
                    time.sleep(2)
                    continue

                if loop_count % 5 == 1:  # Show layer every 5 cycles
                    print(f"Current layer: {current_layer}")

                # Check if we need to change material (only if not already processed this layer)
                print(f"DEBUG: Checking layer {current_layer} for material change. Recipe layers: {list(self.recipe.keys())}")
                if current_layer in self.recipe and (not hasattr(self, '_last_processed_layer') or current_layer != getattr(self, '_last_processed_layer', -1)):
                    material = self.recipe[current_layer]
                    print(f"\nMATERIAL CHANGE TRIGGERED: Layer {current_layer} → Material {material}")

                    if self._handle_material_change(material):
                        # Mark this layer as processed and remove from recipe
                        self._last_processed_layer = current_layer
                        del self.recipe[current_layer]
                        print(f"Material change completed. Remaining: {len(self.recipe)}")
                        if self.recipe:
                            next_layer = min(self.recipe.keys())
                            print(f"Next change at layer {next_layer}")
                    else:
                        print("ERROR: Material change failed!")
                        # Mark layer as processed even if failed to prevent repeated attempts
                        self._last_processed_layer = current_layer

                else:
                    # Show upcoming changes
                    if self.recipe and loop_count % 20 == 1:  # Show upcoming changes every 20 cycles
                        upcoming = [layer for layer in self.recipe.keys() if layer > current_layer]
                        if upcoming:
                            next_change = min(upcoming)
                            layers_until = next_change - current_layer
                            print(f"Next change in {layers_until} layers (layer {next_change})")

                # Check if print is complete
                if self._is_print_complete(status):
                    print("\nPRINT COMPLETED!")
                    break

                # Wait 5 seconds (no log spam)
                time.sleep(5)

        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
            return True  # Clean exit
        except Exception as e:
            print(f"\nCRITICAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False  # Error exit
            
    def _get_printer_status(self):
        """Get current printer status via uart-wifi."""
        try:
            # Use the printer_comms module
            return printer_comms.get_status(self.printer_ip)
        except Exception as e:
            print(f"Error getting printer status: {e}")
            return None
            
    def _extract_current_layer(self, status):
        """
        Extract current layer from status response.

        Args:
            status: MonoXStatus object or string

        Returns:
            int: Layer number or None if parsing fails
        """
        try:
            # Extract layer with minimal logging

            # Handle MonoXStatus object directly
            if hasattr(status, 'current_layer'):
                layer_num = status.current_layer
                # Found current_layer attribute

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
                # Check if print just started

                # If just started printing, assume layer 1
                if status.status in ['print', 'printing'] and str(getattr(status, 'percent_complete', '0')) == '0':
                    # Print just started - assume layer 1
                    return 1

            # Fallback to string parsing
            status_str = str(status)
            # Try string parsing as fallback

            # Look for current_layer field in the status string
            import re

            # Try multiple patterns to find current layer
            patterns = [
                r'current_layer:\s*(\d+)',        # current_layer: 123
                r'current_lay[er]*:\s*(\d+)',     # current_lay: 123 (truncated)
                r'layer:\s*(\d+)',                # layer: 123
                r'current_layer\s*=\s*(\d+)',     # current_layer = 123
                r'current_layer":\s*(\d+)',       # "current_layer": 123
            ]

            for pattern in patterns:
                match = re.search(pattern, status_str, re.IGNORECASE)
                if match:
                    layer_num = int(match.group(1))
                    # Found layer using pattern
                    if layer_num <= 0:
                        return None
                    return layer_num

            # If no pattern matches, try to find any number after "current" or "layer"
            current_match = re.search(r'current.*?(\d+)', status_str, re.IGNORECASE)
            if current_match:
                layer_num = int(current_match.group(1))
                # Found layer using fallback pattern
                if layer_num <= 0:
                    return None
                return layer_num

            # Could not extract layer number
            return None

        except Exception as e:
            print(f"💥 Error extracting layer: {e}")
            import traceback
            traceback.print_exc()
            return None
            
    def _handle_material_change(self, material):
        """
        Execute material change: pause -> change -> resume.

        Args:
            material (str): Target material (A, B, C, D)

        Returns:
            bool: True if successful
        """
        try:
            print(f"Starting material change to {material}...")

            # Step 1: Pause printer
            print("Step 1: Pausing printer...")
            if not self._pause_printer():
                print("ERROR: Could not pause printer")
                return False

            # Step 2: Wait for bed to rise after pause
            print("Step 2: Ensuring bed is in raised position...")
            self._wait_for_bed_raised()

            # Step 3: Execute material change pumps
            print("Step 3: Starting material change pumps...")
            success = mmu_control.change_material(material)

            if success:
                print("✓ Pump sequence completed successfully")
            else:
                print("ERROR: Pump sequence failed - NOT resuming printer")
                return False

            # Step 4: Resume printer
            print("Step 4: Resuming printer...")
            if self._resume_printer():
                print(f"✓ Material change to {material} completed successfully")
                return True
            else:
                print("ERROR: Could not resume printer - manual intervention required")
                return False

        except Exception as e:
            print(f"ERROR: Material change failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def _pause_printer(self):
        """Pause printer via uart-wifi."""
        try:
            return printer_comms.pause_print(self.printer_ip)
        except Exception as e:
            print(f"Error pausing printer: {e}")
            return False
            
    def _resume_printer(self):
        """Resume printer via uart-wifi."""
        try:
            return printer_comms.resume_print(self.printer_ip)
        except Exception as e:
            print(f"Error resuming printer: {e}")
            return False

    def _wait_for_bed_raised(self):
        """
        Wait for bed to reach raised position after pause.

        After pausing, the printer needs time to raise the bed to the top position
        before material change operations can begin. This method implements a
        robust wait with status verification.
        """
        print("  Waiting for bed to reach raised position...")

        # Initial wait for pause command to take effect
        time.sleep(2)

        # Extended wait for mechanical bed movement
        # SLA printers typically take 10-15 seconds to raise bed to top
        bed_raise_time = 15
        print(f"  Allowing {bed_raise_time} seconds for bed movement...")

        for i in range(bed_raise_time):
            time.sleep(1)
            if (i + 1) % 5 == 0:  # Progress update every 5 seconds
                print(f"  Bed positioning: {i + 1}/{bed_raise_time} seconds")

        # Verify printer is still paused
        try:
            status = self._get_printer_status()
            if status and hasattr(status, 'status'):
                if status.status.lower() == 'pause':
                    print("  ✓ Bed should now be in raised position, printer still paused")
                else:
                    print(f"  WARNING: Expected paused status but got: {status.status}")
            else:
                print("  WARNING: Could not verify pause status")
        except Exception as e:
            print(f"  WARNING: Error checking pause status: {e}")

        # Additional safety buffer
        print("  Adding 3-second safety buffer...")
        time.sleep(3)
        print("  ✓ Bed positioning complete - ready for material change")

    def _is_print_complete(self, status):
        """Check if print is complete based on status."""
        try:
            # Check if print is complete

            # Handle MonoXStatus object
            if hasattr(status, 'status'):
                printer_status = status.status
                percent = getattr(status, 'percent_complete', 0)
                current_layer = getattr(status, 'current_layer', 0)
                total_layers = getattr(status, 'total_layers', 0)

                # Status check

                # Print is complete if status is specifically "stop" or "complete" or "finished"
                # AND we're at 100% complete OR we've reached the final layer
                if printer_status.lower() in ['complete', 'finished', 'done']:
                    # Print complete
                    return True

                if printer_status.lower() == 'stop' and percent >= 100:
                    # Print complete
                    return True

                if total_layers > 0 and current_layer >= total_layers and percent >= 99:
                    # Print complete
                    return True

                # Print is NOT complete if actively printing
                if printer_status.lower() in ['print', 'printing']:
                    # Print in progress
                    return False

                # Print is NOT complete if stopped but not at end
                if printer_status.lower() == 'stop' and percent < 100:
                    # Print paused but not complete
                    return False

            # Fallback to string checking (but be more specific)
            status_str = str(status).lower()
            if 'status: complete' in status_str or 'status: finished' in status_str:
                # Print complete
                return True

            # Print not complete
            return False

        except Exception as e:
            print(f"Error checking print completion: {e}")
            return False


def main():
    """
    Command-line interface for automated multi-material printing.

    Usage: python print_manager.py [-r recipe.txt] [-c config.ini] [-i printer_ip]

    Monitors printer via uart-wifi and triggers material changes at specified layers.
    """
    import sys
    print("=== PRINT MANAGER STARTUP ===")
    print(f"Python path: {sys.path}")
    print(f"Working directory: {os.getcwd()}")

    try:
        print("Step 1: Parsing arguments...")
        parser = argparse.ArgumentParser(description='Multi-Material Print Manager')
        parser.add_argument('--recipe', '-r', help='Path to recipe file')
        parser.add_argument('--config', '-c', help='Path to config file')
        parser.add_argument('--printer-ip', '-i', help='Printer IP address override')

        args = parser.parse_args()
        print(f"Arguments: recipe={args.recipe}, config={args.config}, printer_ip={args.printer_ip}")

        print("Step 2: Creating print manager...")
        manager = PrintManager(args.config)
        print("✓ Print manager created successfully")

        print("Step 3: Setting printer IP...")
        if args.printer_ip:
            manager.printer_ip = args.printer_ip
            print(f"✓ Printer IP set to: {args.printer_ip}")
        else:
            print(f"✓ Using default printer IP: {manager.printer_ip}")

        print("Step 4: Resolving recipe path...")
        recipe_path = args.recipe or manager._find_config_path().parent / 'recipe.txt'
        print(f"✓ Recipe path: {recipe_path}")

        print("Step 5: Starting monitoring...")
        success = manager.start_monitoring(recipe_path)

        # Exit with appropriate code
        if success:
            print("Print manager completed successfully")
            sys.exit(0)
        else:
            print("Print manager exited with errors")
            sys.exit(1)

    except Exception as e:
        print(f"FATAL ERROR in print_manager main(): {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print("Traceback:")
        traceback.print_exc()
        sys.exit(15)


if __name__ == "__main__":
    main()