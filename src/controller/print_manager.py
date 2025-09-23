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

# Import other controller modules
try:
    from . import mmu_control
    from . import printer_comms
except ImportError:
    # Fallback for direct execution
    import mmu_control
    import printer_comms

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
            print(f"\n📖 LOADING RECIPE")
            print("=" * 40)
            print(f"📁 Recipe file: {recipe_path}")

            # Check if file exists
            import os
            if not os.path.exists(recipe_path):
                print(f"❌ ERROR: Recipe file does not exist: {recipe_path}")
                return False

            print(f"✅ Recipe file found")

            # Read file contents
            with open(recipe_path, 'r') as f:
                recipe_text = f.read().strip()

            print(f"📄 Raw recipe content: '{recipe_text}'")
            print(f"📏 Content length: {len(recipe_text)} characters")

            if not recipe_text:
                print("⚠️  WARNING: Recipe file is empty")
                self.recipe = {}
                return True

            # Parse recipe format: "A,50:B,120"
            print("🔍 Parsing recipe...")
            self.recipe = {}
            valid_materials = ['A', 'B', 'C', 'D']

            pairs = recipe_text.split(':')
            print(f"📋 Found {len(pairs)} recipe pairs: {pairs}")

            for i, pair in enumerate(pairs):
                pair_num = i + 1
                print(f"   🔸 Processing pair {pair_num}: '{pair}'")

                if ',' not in pair:
                    print(f"   ⚠️  WARNING: Skipping invalid pair {pair_num} (no comma): '{pair}'")
                    continue

                try:
                    material, layer_str = pair.split(',', 1)  # Split only on first comma
                    material = material.strip().upper()
                    layer_str = layer_str.strip()

                    # Validate material
                    if material not in valid_materials:
                        print(f"   ❌ ERROR: Invalid material '{material}' in pair {pair_num}. Must be one of: {valid_materials}")
                        continue

                    # Validate layer number
                    try:
                        layer = int(layer_str)
                        if layer <= 0:
                            print(f"   ❌ ERROR: Invalid layer number '{layer}' in pair {pair_num}. Must be positive integer.")
                            continue
                    except ValueError:
                        print(f"   ❌ ERROR: Invalid layer number '{layer_str}' in pair {pair_num}. Must be integer.")
                        continue

                    # Check for duplicate layers
                    if layer in self.recipe:
                        print(f"   ⚠️  WARNING: Duplicate layer {layer}. Overriding {self.recipe[layer]} with {material}")

                    self.recipe[layer] = material
                    print(f"   ✅ Added: Layer {layer} → Material {material}")

                except Exception as e:
                    print(f"   ❌ ERROR: Failed to parse pair {pair_num} '{pair}': {e}")
                    continue

            print("─" * 40)
            print(f"📊 RECIPE PARSING COMPLETE")
            print(f"✅ Successfully parsed {len(self.recipe)} material changes:")

            if self.recipe:
                for layer, material in sorted(self.recipe.items()):
                    print(f"   📍 Layer {layer:>3} → Material {material}")

                # Show sequence info
                sorted_layers = sorted(self.recipe.keys())
                print(f"🔢 Layer sequence: {sorted_layers}")
                print(f"📏 Layer range: {min(sorted_layers)} to {max(sorted_layers)}")
            else:
                print("⚠️  WARNING: No valid material changes found in recipe")

            print("=" * 40)
            return True

        except Exception as e:
            print(f"\n💥 CRITICAL ERROR loading recipe: {e}")
            import traceback
            print("📊 Full error traceback:")
            traceback.print_exc()
            print("❌ Recipe loading FAILED")
            return False
    
    def start_monitoring(self, recipe_path=None):
        """
        Start automated printer monitoring and material changes.

        Args:
            recipe_path (str, optional): Recipe file to load

        Polls printer every 5 seconds, triggers material changes at target layers.
        """
        print("=" * 60)
        print("MULTI-MATERIAL PRINT MANAGER STARTING")
        print("=" * 60)

        if recipe_path and not self.load_recipe(recipe_path):
            print("❌ CRITICAL ERROR: Failed to load recipe, aborting.")
            return False

        if not self.recipe:
            print("⚠️  WARNING: No recipe loaded, monitoring only (no material changes will occur).")
        else:
            print(f"✅ Recipe loaded successfully with {len(self.recipe)} material changes:")
            for layer, material in sorted(self.recipe.items()):
                print(f"   📍 Layer {layer} → Material {material}")

        print(f"🖨️  Target printer: {self.printer_ip}:{self.printer_port}")
        print(f"⏱️  Monitoring interval: 5 seconds")
        print(f"⏰ Timeout setting: {self.timeout} seconds")
        print("🔄 Starting continuous monitoring loop...")
        print("=" * 60)

        try:
            loop_count = 0
            while True:
                loop_count += 1
                print(f"\n🔍 Monitoring cycle #{loop_count} - {time.strftime('%H:%M:%S')}")

                # Get current printer status
                print("📡 Requesting printer status...")
                status = self._get_printer_status()
                if not status:
                    print("❌ ERROR: Lost connection to printer - retrying in 5 seconds")
                    time.sleep(5)
                    continue

                print("✅ Printer status received")

                # Extract current layer
                current_layer = self._extract_current_layer(status)
                if current_layer is None:
                    print("⚠️  WARNING: Could not determine current layer from status")
                    print(f"📄 Raw status: {str(status)[:100]}...")
                    time.sleep(2)
                    continue

                print(f"📐 Current layer: {current_layer}")

                # Check if we need to change material
                if current_layer in self.recipe:
                    material = self.recipe[current_layer]
                    print("\n" + "🚨" * 20)
                    print(f"🔄 MATERIAL CHANGE TRIGGERED!")
                    print(f"📍 Layer {current_layer}: Switching to material {material}")
                    print("🚨" * 20)

                    if self._handle_material_change(material):
                        # Remove this change from recipe so we don't repeat it
                        del self.recipe[current_layer]
                        print("✅ Material change completed successfully")
                        print(f"📋 Remaining changes: {len(self.recipe)}")
                        if self.recipe:
                            next_layer = min(self.recipe.keys())
                            print(f"📍 Next change at layer {next_layer}")
                    else:
                        print("❌ CRITICAL ERROR: Material change failed!")
                        print("🛑 Consider stopping the print to investigate")

                else:
                    # Show upcoming changes
                    if self.recipe:
                        upcoming = [layer for layer in self.recipe.keys() if layer > current_layer]
                        if upcoming:
                            next_change = min(upcoming)
                            layers_until = next_change - current_layer
                            print(f"⏳ Next material change in {layers_until} layers (layer {next_change})")

                # Check if print is complete
                if self._is_print_complete(status):
                    print("\n" + "🎉" * 20)
                    print("🏁 PRINT COMPLETED!")
                    print("🎉" * 20)
                    break

                print(f"⏸️  Waiting 5 seconds before next check...")
                time.sleep(5)  # Check every 5 seconds

        except KeyboardInterrupt:
            print("\n🛑 MONITORING STOPPED BY USER")
            print("👋 Print manager shutting down...")
        except Exception as e:
            print(f"\n💥 CRITICAL ERROR during monitoring: {e}")
            import traceback
            print("📊 Full error details:")
            traceback.print_exc()
            
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
            print(f"🔍 Extracting layer from status...")
            print(f"📄 Status type: {type(status)}")

            # Handle MonoXStatus object directly
            if hasattr(status, 'current_layer'):
                layer_num = status.current_layer
                print(f"✅ Found current_layer attribute: {layer_num}")

                # Convert to int if it's a string
                if isinstance(layer_num, str) and layer_num.isdigit():
                    layer_num = int(layer_num)
                elif isinstance(layer_num, (int, float)):
                    layer_num = int(layer_num)
                else:
                    print(f"⚠️ current_layer is not numeric: {layer_num} (type: {type(layer_num)})")
                    return None

                print(f"✅ Parsed current layer: {layer_num}")
                return layer_num

            # If no current_layer attribute, check other attributes
            if hasattr(status, 'percent_complete') and hasattr(status, 'status'):
                print(f"📊 Status: {status.status}, Progress: {getattr(status, 'percent_complete', 'unknown')}%")

                # If just started printing, assume layer 1
                if status.status in ['print', 'printing'] and str(getattr(status, 'percent_complete', '0')) == '0':
                    print("📍 Print just started (0% complete) - assuming layer 1")
                    return 1

            # Fallback to string parsing
            status_str = str(status)
            print(f"📄 Full status string: {status_str[:200]}{'...' if len(status_str) > 200 else ''}")

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
                    print(f"✅ Found current layer using pattern '{pattern}': {layer_num}")
                    return layer_num

            # If no pattern matches, try to find any number after "current" or "layer"
            current_match = re.search(r'current.*?(\d+)', status_str, re.IGNORECASE)
            if current_match:
                layer_num = int(current_match.group(1))
                print(f"✅ Found layer using 'current' pattern: {layer_num}")
                return layer_num

            print("❌ Could not extract layer number from status")
            print(f"📋 Available attributes: {[attr for attr in dir(status) if not attr.startswith('_')] if hasattr(status, '__dict__') else 'N/A'}")
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
            print(f"\n🔧 STARTING MATERIAL CHANGE SEQUENCE")
            print(f"🎯 Target material: {material}")
            print(f"⏰ Started at: {time.strftime('%H:%M:%S')}")
            print("─" * 50)

            # 1. Pause the printer
            print("🛑 Step 1/3: Pausing printer...")
            if not self._pause_printer():
                print("❌ FAILED: Could not pause printer")
                print("🚨 ABORTING material change sequence")
                return False
            print("✅ Printer paused successfully")

            # 2. Run material change pumps
            print(f"🔄 Step 2/3: Executing pump sequence for material {material}...")
            print("📡 Sending commands to MMU controller...")

            success = mmu_control.change_material(material)

            if success:
                print("✅ Pump sequence completed successfully")
            else:
                print("❌ FAILED: Pump sequence failed")
                print("🚨 Material change unsuccessful - check pump hardware")
                print("⚠️  NOT resuming printer due to failed material change")
                return False

            # 3. Resume the printer
            print("▶️  Step 3/3: Resuming printer...")
            if self._resume_printer():
                print("✅ Printer resumed successfully")
                print("🎉 MATERIAL CHANGE SEQUENCE COMPLETED")
                print(f"⏰ Finished at: {time.strftime('%H:%M:%S')}")
                print("─" * 50)
                return True
            else:
                print("❌ FAILED: Could not resume printer")
                print("🚨 CRITICAL: Printer is paused but material change completed")
                print("🛠️  Manual intervention required to resume printing")
                return False

        except Exception as e:
            print(f"\n💥 EXCEPTION during material change: {e}")
            import traceback
            print("📊 Full error traceback:")
            traceback.print_exc()
            print("🚨 Material change sequence FAILED due to exception")
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
            
    def _is_print_complete(self, status):
        """Check if print is complete based on status."""
        try:
            print(f"🔍 Checking if print is complete...")

            # Handle MonoXStatus object
            if hasattr(status, 'status'):
                printer_status = status.status
                percent = getattr(status, 'percent_complete', 0)
                current_layer = getattr(status, 'current_layer', 0)
                total_layers = getattr(status, 'total_layers', 0)

                print(f"📊 Printer status: '{printer_status}', Progress: {percent}%, Layer: {current_layer}/{total_layers}")

                # Print is complete if status is specifically "stop" or "complete" or "finished"
                # AND we're at 100% complete OR we've reached the final layer
                if printer_status.lower() in ['complete', 'finished', 'done']:
                    print("✅ Print complete: Status indicates finished")
                    return True

                if printer_status.lower() == 'stop' and percent >= 100:
                    print("✅ Print complete: Stopped at 100%")
                    return True

                if total_layers > 0 and current_layer >= total_layers and percent >= 99:
                    print("✅ Print complete: Reached final layer")
                    return True

                # Print is NOT complete if actively printing
                if printer_status.lower() in ['print', 'printing']:
                    print("🔄 Print in progress")
                    return False

                # Print is NOT complete if stopped but not at end
                if printer_status.lower() == 'stop' and percent < 100:
                    print("⏸️ Print paused/stopped but not complete")
                    return False

            # Fallback to string checking (but be more specific)
            status_str = str(status).lower()
            if 'status: complete' in status_str or 'status: finished' in status_str:
                print("✅ Print complete: Found completion status")
                return True

            print("🔄 Print not complete")
            return False

        except Exception as e:
            print(f"💥 Error checking print completion: {e}")
            return False


def main():
    """
    Command-line interface for automated multi-material printing.
    
    Usage: python print_manager.py [-r recipe.txt] [-c config.ini] [-i printer_ip]
    
    Monitors printer via uart-wifi and triggers material changes at specified layers.
    """
    parser = argparse.ArgumentParser(description='Multi-Material Print Manager')
    parser.add_argument('--recipe', '-r', help='Path to recipe file')
    parser.add_argument('--config', '-c', help='Path to config file')
    parser.add_argument('--printer-ip', '-i', help='Printer IP address override')
    
    args = parser.parse_args()
    
    # Create print manager
    manager = PrintManager(args.config)
    
    # Override printer IP if provided
    if args.printer_ip:
        manager.printer_ip = args.printer_ip
        
    # Start monitoring
    recipe_path = args.recipe or manager._find_config_path().parent / 'recipe.txt'
    manager.start_monitoring(recipe_path)


if __name__ == "__main__":
    main()