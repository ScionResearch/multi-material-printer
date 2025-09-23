"""
Printer Communications - Anycubic printer control via uart-wifi library

Interface for Anycubic Mono X printers using uart-wifi library. Converts raw printer
responses into structured data and handles network communication automatically.

Key Features:
- uart-wifi integration for structured printer responses
- Configuration-based setup via INI files
- Automatic connection recovery and error handling
- Print control: pause/resume/stop operations
- File management and status monitoring

Usage:
    comm = PrinterCommunicator()
    status = comm.get_status()
    comm.pause_print()
    files = comm.get_files()

Requires: uart-wifi>=0.2.1, network_settings.ini configuration
"""

import configparser
from pathlib import Path
import logging

# Import uart-wifi library for printer communication
try:
    from uart_wifi.communication import UartWifi
    from uart_wifi.errors import ConnectionException
    from uart_wifi.response import MonoXResponseType
    UART_WIFI_AVAILABLE = True
except ImportError:
    UART_WIFI_AVAILABLE = False
    # Define placeholder exception classes when library is not available
    class ConnectionException(Exception):
        pass
    class MonoXResponseType:
        pass
    logging.warning("uart-wifi library not available. Install with: pip install uart-wifi>=0.2.1")


class PrinterCommunicator:
    """
    Anycubic printer interface using uart-wifi library.
    
    Provides methods for status monitoring, print control, and file management.
    Uses uart-wifi library for structured communication with Anycubic printers.
    
    Attributes:
        printer_ip (str): Target printer IP address  
        printer_port (int): Communication port (default: 6000)
        timeout (int): Command timeout (default: 10)
    """
    
    def __init__(self, config_path=None):
        """
        Initialize printer communicator with configuration.
        
        Args:
            config_path (str, optional): Path to config file (default: auto-detect)
        """
        self.config_path = config_path or self._find_config_path()
        self.config = self._load_config()
        self.printer_ip = self.config.get('printer', 'ip_address', fallback='192.168.4.2')
        self.printer_port = self.config.getint('printer', 'port', fallback=6000)
        self.timeout = self.config.getint('printer', 'timeout', fallback=10)
        self._uart_wifi = None
        
    def _find_config_path(self):
        """Find network configuration file path."""
        script_dir = Path(__file__).parent
        config_dir = script_dir.parent.parent / 'config'
        return config_dir / 'network_settings.ini'
        
    def _load_config(self):
        """Load configuration from INI file with fallback defaults."""
        config = configparser.ConfigParser()
        try:
            config.read(self.config_path)
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
        return config
    
    def _get_uart_connection(self):
        """Get or create uart-wifi connection instance."""
        if self._uart_wifi is None:
            self._uart_wifi = UartWifi(self.printer_ip, self.printer_port)
        return self._uart_wifi
        
    def _run_printer_command(self, command):
        """
        Execute printer command via uart-wifi library.
        Based on newmonox.py implementation with retry logic.

        Args:
            command (str): Command to send ('getstatus', 'gopause', etc.)

        Returns:
            str: Response data or error message
        """
        import time
        from typing import Iterable

        # Try 3 times to get the data (matching newmonox.py behavior)
        for attempt in range(3):
            try:
                uart = UartWifi(self.printer_ip, self.printer_port)
                responses = uart.send_request(command)

                # Process responses like newmonox.py does
                output_lines = []
                if responses is not None and isinstance(responses, Iterable):
                    for response in responses:
                        if isinstance(response, MonoXResponseType):
                            if response is not None and str(response).strip():
                                output_lines.append(str(response))
                        elif response is not None and str(response).strip():
                            output_lines.append(str(response))
                        else:
                            output_lines.append(str(response))
                else:
                    output_lines.append(str(responses))

                return '\n'.join(output_lines)

            except ConnectionException:
                time.sleep(1)  # Wait before retry
                continue

        # If all 3 attempts failed
        raise ConnectionException(f"Failed to send command after 3 attempts.")
    
    def get_status(self):
        """
        Get current printer status via uart-wifi.
        
        Returns:
            str: Status response with state, layer, progress info
        """
        return self._run_printer_command('getstatus')
    
    def pause_print(self):
        """
        Pause current print job.
        
        Returns:
            bool: True if successful
        """
        response = self._run_printer_command('gopause')
        return response is not None
    
    def resume_print(self):
        """
        Resume paused print job.
        
        Returns:
            bool: True if successful
        """
        response = self._run_printer_command('goresume')
        return response is not None
    
    def stop_print(self):
        """
        Stop current print job permanently.
        
        Returns:
            bool: True if successful
        """
        response = self._run_printer_command('gostop,end')
        return response is not None
    
    def get_files(self):
        """
        Get list of printable files on printer.
        
        Returns:
            list: Available filenames or empty list if error
        """
        response = self._run_printer_command('getfiles')
        if response:
            return response.split('\n')
        return []
    
    def start_print(self, filename):
        """
        Start printing specified file.
        
        Args:
            filename (str): File to print (use internal name from get_files)
            
        Returns:
            bool: True if successful
        """
        command = f'goprint,{filename},end'
        response = self._run_printer_command(command)
        return response is not None
    
    def get_mode(self):
        """
        Get printer operating mode.
        
        Returns:
            str: Mode response or None if error
        """
        return self._run_printer_command('getmode')
    
    def is_connected(self):
        """
        Test printer connectivity.
        
        Returns:
            bool: True if printer responds
        """
        status = self.get_status()
        return status is not None and len(status) > 0


# Global instance for easy access
_printer_comm = None

def get_communicator():
    """Get global PrinterCommunicator instance (singleton pattern)."""
    global _printer_comm
    if _printer_comm is None:
        _printer_comm = PrinterCommunicator()
    return _printer_comm

# Convenience functions that match expected interface
def get_status(printer_ip=None):
    """Get printer status (convenience function)."""
    comm = get_communicator()
    if printer_ip:
        comm.printer_ip = printer_ip
    return comm.get_status()

def pause_print(printer_ip=None):
    """Pause print (convenience function)."""
    comm = get_communicator()
    if printer_ip:
        comm.printer_ip = printer_ip
    return comm.pause_print()

def resume_print(printer_ip=None):
    """Resume print (convenience function)."""
    comm = get_communicator()
    if printer_ip:
        comm.printer_ip = printer_ip
    return comm.resume_print()

def stop_print(printer_ip=None):
    """Stop print (convenience function)."""
    comm = get_communicator()
    if printer_ip:
        comm.printer_ip = printer_ip
    return comm.stop_print()

def get_files(printer_ip=None):
    """Get files (convenience function)."""
    comm = get_communicator()
    if printer_ip:
        comm.printer_ip = printer_ip
    return comm.get_files()

def start_print(filename, printer_ip=None):
    """Start print (convenience function)."""
    comm = get_communicator()
    if printer_ip:
        comm.printer_ip = printer_ip
    return comm.start_print(filename)


if __name__ == "__main__":
    """
    Command-line interface for printer communication testing.
    
    Usage: python printer_comms.py -i <printer_ip> -c <command>
    
    Commands: getstatus, gopause, goresume, gostop,end, getfile, getmode
    """
    import sys
    
    if len(sys.argv) >= 3:
        # python printer_comms.py -i 192.168.4.2 -c getstatus
        if '-i' in sys.argv:
            ip_index = sys.argv.index('-i') + 1
            if ip_index < len(sys.argv):
                printer_ip = sys.argv[ip_index]
        
        if '-c' in sys.argv:
            cmd_index = sys.argv.index('-c') + 1
            if cmd_index < len(sys.argv):
                command = sys.argv[cmd_index]
                
                comm = PrinterCommunicator()
                comm.printer_ip = printer_ip
                response = comm._run_printer_command(command)
                if response:
                    print(response)
                else:
                    print("Command failed")
    else:
        print("Usage: python printer_comms.py -i <ip> -c <command>")
        print("Example: python printer_comms.py -i 192.168.4.2 -c getstatus")