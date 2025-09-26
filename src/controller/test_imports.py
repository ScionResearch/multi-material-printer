#!/usr/bin/env python3
"""
Minimal test script to verify controller module imports work correctly.
This will help diagnose why print_manager.py is still not producing output.
"""

import sys
import os
from pathlib import Path

print("=== IMPORT TEST SCRIPT ===")
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")
print(f"Script location: {__file__}")
print(f"Python path: {sys.path}")

print("\n--- Testing controller module imports ---")

try:
    print("Attempting to import mmu_control...")
    import mmu_control
    print("✅ mmu_control imported successfully")
    print(f"mmu_control location: {mmu_control.__file__}")
except Exception as e:
    print(f"❌ Failed to import mmu_control: {e}")

try:
    print("Attempting to import printer_comms...")
    import printer_comms
    print("✅ printer_comms imported successfully")
    print(f"printer_comms location: {printer_comms.__file__}")
except Exception as e:
    print(f"❌ Failed to import printer_comms: {e}")

print("\n--- Import test complete ---")
print("If both modules imported successfully, print_manager.py should work.")