#!/usr/bin/env python3
"""
Comprehensive test script to verify print file retrieval functionality.
This should be run on the Raspberry Pi to test the fixed get_files() implementation.

Tests:
1. Direct PrinterCommunicator.get_files() functionality
2. Web API endpoint functionality
3. Comparison with Qt GUI approach

Usage: python3 test_print_files.py [--verbose]
"""

import sys
import os
import json
import requests
from pathlib import Path

# Add src/controller to path for imports
controller_path = Path(__file__).parent / "src" / "controller"
sys.path.insert(0, str(controller_path))

verbose = '--verbose' in sys.argv

def print_verbose(message):
    if verbose:
        print(message)

print("Comprehensive Print File Functionality Test")
print("=" * 60)

# Test 1: Direct printer communication
print("\n1. Testing direct PrinterCommunicator functionality...")
try:
    from printer_comms import PrinterCommunicator

    # Create communicator instance
    comm = PrinterCommunicator()
    print(f"   Printer IP: {comm.printer_ip}")

    # Test connection first
    print("   Testing connection...")
    try:
        status = comm.get_status()
        if status:
            print(f"   ✓ Connection successful. Status: {status[:100]}...")
        else:
            print("   ✗ No status response - printer may be disconnected")
            sys.exit(1)
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        sys.exit(1)

    # Test get_files functionality
    print("   Testing get_files() method...")
    try:
        files = comm.get_files()

        if files:
            print(f"   ✓ Found {len(files)} print files:")
            for i, file in enumerate(files, 1):
                print(f"     {i}. '{file['name']}' (internal: '{file['internal_name']}')")
                if verbose:
                    print(f"        Size: {file['size']}, Type: {file['type']}, Date: {file['date']}")
        else:
            print("   ✗ No print files found or get_files() returned empty list")

            # Debug: Test raw command output
            print("\n   Debugging raw command output...")
            try:
                raw_response = comm._run_printer_command('getfileinfo')
                print(f"   Raw response length: {len(raw_response) if raw_response else 0} chars")
                print(f"   Raw response: {repr(raw_response)}")
                if raw_response:
                    print("   Raw response lines:")
                    for line in raw_response.split('\n'):
                        print(f"     '{line.strip()}'")
            except Exception as debug_e:
                print(f"   Debug error: {debug_e}")

    except Exception as e:
        print(f"   ✗ get_files() failed: {e}")
        import traceback
        traceback.print_exc()

except ImportError as e:
    print(f"   Import error: {e}")
    print("   This test should be run on the Raspberry Pi with uart-wifi library installed.")
    sys.exit(1)

# Test 2: Web API endpoint (if web app is running)
print("\n2. Testing web app API endpoint...")
try:
    # Test if web app is running on default port
    response = requests.get('http://localhost:5000/api/printer/files', timeout=5)

    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            files = data.get('files', [])
            print(f"   ✓ Web API returned {len(files)} files:")
            for i, file in enumerate(files, 1):
                name = file.get('name', 'Unknown')
                internal = file.get('internal_name', '')
                print(f"     {i}. '{name}' (internal: '{internal}')")
        else:
            print(f"   ✗ Web API failed: {data.get('message', 'Unknown error')}")
    else:
        print(f"   ✗ Web API HTTP error: {response.status_code}")

except requests.exceptions.ConnectionError:
    print("   ⚠ Web app not running on localhost:5000 - skipping web API test")
except Exception as e:
    print(f"   ✗ Web API test failed: {e}")

# Test 3: Shared status integration
print("\n3. Testing shared status integration...")
try:
    shared_status_path = controller_path / "shared_status.py"
    if shared_status_path.exists():
        from shared_status import get_shared_status

        status_mgr = get_shared_status()
        print("   ✓ Shared status manager available")

        # Test logging a print file retrieval event
        status_mgr.log_activity("INFO", f"Print file test completed - found {len(files) if 'files' in locals() else 0} files", "test")
        print("   ✓ Logged test activity to shared status")

    else:
        print("   ⚠ Shared status module not found")

except Exception as e:
    print(f"   ✗ Shared status test failed: {e}")

print("\n" + "=" * 60)
print("Test Summary:")
print("- Direct printer communication: Tested")
print("- Web API endpoint: Tested (if app running)")
print("- Shared status integration: Tested")
print("\nIf all tests show ✓, the print file functionality should work correctly!")
print("If there are ✗ errors, check:")
print("1. Printer is connected and responding")
print("2. uart-wifi library is properly installed")
print("3. Network configuration is correct")
print("4. Web app is running (for API test)")