#!/usr/bin/env python3
"""
Fake Printer Setup Script - Helper for uart-wifi library simulator

This script helps set up and run the fake_printer.py simulator from the uart-wifi
library for testing the multi-material printer system without physical hardware.

Usage:
    python setup_fake_printer.py [--port 6000] [--ip 127.0.0.1]

The fake printer allows testing of:
- Printer communication protocols
- Status monitoring and parsing
- File management operations  
- Material change timing logic
- GUI integration without hardware

Requires: uart-wifi library installed (pip install uart-wifi>=0.2.1)
"""

import argparse
import subprocess
import sys
import os

def find_fake_printer_script():
    """
    Try to locate the fake_printer.py script from uart-wifi library.
    
    Returns:
        str: Path to fake_printer.py or None if not found
    """
    # Common locations for the fake printer script
    possible_paths = [
        'fake_printer.py',  # If in current directory
        'src/uart_wifi/scripts/fake_printer.py',  # If in repo
        # Could add more paths based on installation
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # Try to import and find the module path
    try:
        import uart_wifi
        uart_wifi_path = os.path.dirname(uart_wifi.__file__)
        fake_printer_path = os.path.join(uart_wifi_path, 'scripts', 'fake_printer.py')
        if os.path.exists(fake_printer_path):
            return fake_printer_path
    except ImportError:
        pass
    
    return None

def run_fake_printer(port=6000, ip='127.0.0.1'):
    """
    Run the fake printer simulator.
    
    Args:
        port (int): Port to listen on (default: 6000)
        ip (str): IP address to bind to (default: 127.0.0.1)
    """
    fake_printer_script = find_fake_printer_script()
    
    if not fake_printer_script:
        print("Error: Could not find fake_printer.py script")
        print("Make sure uart-wifi library is installed: pip install uart-wifi>=0.2.1")
        print("Or download the script from the anycubic-python repository")
        return False
    
    print(f"Starting fake printer simulator...")
    print(f"Script: {fake_printer_script}")
    print(f"Listening on: {ip}:{port}")
    print(f"Configure your printer IP to: {ip}")
    print("Press Ctrl+C to stop")
    print("-" * 50)
    
    try:
        # Run the fake printer script
        cmd = [sys.executable, fake_printer_script, '--port', str(port)]
        if ip != '127.0.0.1':
            cmd.extend(['--ip', ip])
            
        subprocess.run(cmd)
        return True
        
    except KeyboardInterrupt:
        print("\nFake printer stopped by user")
        return True
    except FileNotFoundError:
        print(f"Error: Could not execute {fake_printer_script}")
        return False
    except Exception as e:
        print(f"Error running fake printer: {e}")
        return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Setup and run uart-wifi fake printer simulator',
        epilog="""
Examples:
  python setup_fake_printer.py                    # Default port 6000, localhost
  python setup_fake_printer.py --port 8000        # Custom port
  python setup_fake_printer.py --ip 0.0.0.0       # Listen on all interfaces
        """
    )
    
    parser.add_argument('--port', '-p', type=int, default=6000,
                        help='Port to listen on (default: 6000)')
    parser.add_argument('--ip', '-i', default='127.0.0.1',
                        help='IP address to bind to (default: 127.0.0.1)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Multi-Material Printer - Fake Printer Simulator Setup")
    print("=" * 60)
    
    success = run_fake_printer(args.port, args.ip)
    
    if success:
        print("\nTo test the fake printer, run:")
        print(f"python src/controller/printer_comms.py -i {args.ip} -c getstatus")
        print(f"python src/controller/printer_comms.py -i {args.ip} -c detailed")
        print(f"python src/controller/printer_comms.py -i {args.ip} -c sysinfo")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())