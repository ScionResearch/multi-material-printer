"""
Print Manager Module - Main orchestration for multi-material printing

This module handles the coordination between printer communication and 
material changes during a print job.

Refactored from pollphoton.py to be more modular and configurable.
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
    def __init__(self, config_path=None):
        """Initialize the print manager with configuration."""
        self.config_path = config_path or self._find_config_path()
        self.config = self._load_config()
        self.printer_ip = self.config.get('printer', 'ip_address', fallback='192.168.4.2')
        self.printer_port = self.config.getint('printer', 'port', fallback=80)
        self.timeout = self.config.getint('printer', 'timeout', fallback=10)
        
        # Load recipe if provided
        self.recipe = {}
        
    def _find_config_path(self):
        """Find the configuration file relative to this script."""
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
        """Load material change recipe from file."""
        try:
            with open(recipe_path, 'r') as f:
                recipe_text = f.read().strip()
                
            # Parse recipe format: "A,50:B,120"
            self.recipe = {}
            if recipe_text:
                pairs = recipe_text.split(':')
                for pair in pairs:
                    if ',' in pair:
                        material, layer = pair.split(',')
                        self.recipe[int(layer)] = material.strip()
                        
            print(f"Loaded recipe: {self.recipe}")
            return True
        except Exception as e:
            print(f"Error loading recipe: {e}")
            return False
    
    def start_monitoring(self, recipe_path=None):
        """Start monitoring the printer and handling material changes."""
        if recipe_path and not self.load_recipe(recipe_path):
            print("Failed to load recipe, aborting.")
            return False
            
        if not self.recipe:
            print("No recipe loaded, monitoring only.")
            
        print(f"Starting print monitoring for printer at {self.printer_ip}")
        print(f"Recipe: {self.recipe}")
        
        try:
            while True:
                # Get current printer status
                status = self._get_printer_status()
                if not status:
                    print("Lost connection to printer")
                    time.sleep(5)
                    continue
                    
                current_layer = self._extract_current_layer(status)
                if current_layer is None:
                    print("Could not determine current layer")
                    time.sleep(2)
                    continue
                    
                print(f"Current layer: {current_layer}")
                
                # Check if we need to change material
                if current_layer in self.recipe:
                    material = self.recipe[current_layer]
                    print(f"Material change needed at layer {current_layer}: {material}")
                    
                    if self._handle_material_change(material):
                        # Remove this change from recipe so we don't repeat it
                        del self.recipe[current_layer]
                        print("Material change completed successfully")
                    else:
                        print("Material change failed!")
                        
                # Check if print is complete
                if self._is_print_complete(status):
                    print("Print completed!")
                    break
                    
                time.sleep(5)  # Check every 5 seconds
                
        except KeyboardInterrupt:
            print("Monitoring stopped by user")
        except Exception as e:
            print(f"Error during monitoring: {e}")
            
    def _get_printer_status(self):
        """Get current printer status."""
        try:
            # Use the printer_comms module
            return printer_comms.get_status(self.printer_ip)
        except Exception as e:
            print(f"Error getting printer status: {e}")
            return None
            
    def _extract_current_layer(self, status):
        """Extract current layer number from status response."""
        try:
            # This needs to be implemented based on your printer's response format
            # For now, return a placeholder
            if "layer" in status.lower():
                # Extract layer number from status string
                # Implementation depends on your printer's status format
                pass
            return None
        except Exception as e:
            print(f"Error extracting layer: {e}")
            return None
            
    def _handle_material_change(self, material):
        """Handle material change process."""
        try:
            print(f"Starting material change to: {material}")
            
            # 1. Pause the printer
            if not self._pause_printer():
                return False
                
            # 2. Run material change pumps
            success = mmu_control.change_material(material)
            
            # 3. Resume the printer
            if success:
                return self._resume_printer()
            else:
                print("Material change failed, not resuming")
                return False
                
        except Exception as e:
            print(f"Error during material change: {e}")
            return False
            
    def _pause_printer(self):
        """Pause the printer."""
        try:
            return printer_comms.pause_print(self.printer_ip)
        except Exception as e:
            print(f"Error pausing printer: {e}")
            return False
            
    def _resume_printer(self):
        """Resume the printer."""
        try:
            return printer_comms.resume_print(self.printer_ip)
        except Exception as e:
            print(f"Error resuming printer: {e}")
            return False
            
    def _is_print_complete(self, status):
        """Check if print is complete."""
        # Implementation depends on your printer's status format
        return "complete" in status.lower() if status else False


def main():
    """Main entry point when script is run directly."""
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