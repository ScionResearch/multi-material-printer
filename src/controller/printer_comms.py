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
    from uart_wifi.errors import ConnectionException, TimeoutException
    UART_WIFI_AVAILABLE = True
except ImportError:
    UART_WIFI_AVAILABLE = False
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
        if not UART_WIFI_AVAILABLE:
            raise Exception("uart-wifi library not available. Install with: pip install uart-wifi>=0.2.1")
        
        if self._uart_wifi is None:
            self._uart_wifi = UartWifi(self.printer_ip, self.printer_port)
        return self._uart_wifi
        
    def _run_printer_command(self, command):
        """
        Execute printer command via uart-wifi library.
        
        Args:
            command (str): Command to send ('getstatus', 'gopause', etc.)
            
        Returns:
            str: Response data or None if error
        """
        try:
            uart = self._get_uart_connection()
            response = uart.send_request(command, timeout=self.timeout)
            
            if response and hasattr(response, 'data'):
                return response.data.strip()
            elif response:
                return str(response).strip()
            else:
                return None
                
        except ConnectionException as e:
            print(f"Printer connection failed: {e}")
            self._uart_wifi = None  # Reset connection for retry
            return None
        except TimeoutException as e:
            print(f"Printer command timed out: {command}")
            return None
        except Exception as e:
            print(f"Error running printer command: {e}")
            self._uart_wifi = None  # Reset connection for retry
            return None
    
    def get_status(self):
        """
        Get current printer status via uart-wifi.
        
        Returns:
            dict: Status info with state, layer, progress, or None if error
        """
        try:
            uart = self._get_uart_connection()
            responses = uart.send_request("getstatus")
            
            if responses:
                status_obj = responses[0]
                # Return structured data instead of raw string
                return {
                    'status': getattr(status_obj, 'status', 'unknown'),
                    'current_layer': getattr(status_obj, 'current_layer', 0),
                    'percent_complete': getattr(status_obj, 'percent_complete', 0),
                    'raw_response': str(status_obj)
                }
            return None
                
        except Exception as e:
            print(f"Error getting printer status: {e}")
            self._uart_wifi = None
            return None
    
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
        Get list of printable files on printer via uart-wifi 'getfile' command.
        
        Returns:
            list: List of file info dicts with external/internal names, or empty list if error
        """
        try:
            uart = self._get_uart_connection()
            responses = uart.send_request("getfile")
            
            if responses:
                file_list_obj = responses[0]
                files = []
                # Handle FileList object with MonoXFileEntry objects
                if hasattr(file_list_obj, 'files'):
                    for file_entry in file_list_obj.files:
                        files.append({
                            'external': getattr(file_entry, 'external', 'unknown'),
                            'internal': getattr(file_entry, 'internal', 'unknown'),
                            'display_name': getattr(file_entry, 'external', 'unknown')
                        })
                return files
            return []
                
        except Exception as e:
            print(f"Error getting file list: {e}")
            self._uart_wifi = None
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
    
    def get_system_info(self):
        """
        Get printer system information via uart-wifi 'sysinfo' command.
        
        Returns:
            dict: System info with model, firmware, serial, or None if error
        """
        try:
            uart = self._get_uart_connection()
            responses = uart.send_request("sysinfo")
            
            if responses:
                info_obj = responses[0]
                return {
                    'model': getattr(info_obj, 'model', 'unknown'),
                    'firmware': getattr(info_obj, 'firmware', 'unknown'), 
                    'serial': getattr(info_obj, 'serial', 'unknown'),
                    'raw_response': str(info_obj)
                }
            return None
                
        except Exception as e:
            print(f"Error getting system info: {e}")
            self._uart_wifi = None
            return None
    
    def is_connected(self):
        """
        Test printer connectivity.
        
        Returns:
            bool: True if printer responds
        """
        status = self.get_status()
        return status is not None
    
    def get_detailed_status(self):
        """
        Get comprehensive printer status including progress and system info.
        
        Returns:
            dict: Combined status and system information
        """
        status = self.get_status()
        if status:
            # Add system info if available
            sys_info = self.get_system_info()
            if sys_info:
                status['system_info'] = sys_info
            return status
        return None


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

def get_system_info(printer_ip=None):
    """Get system info (convenience function)."""
    comm = get_communicator()
    if printer_ip:
        comm.printer_ip = printer_ip
    return comm.get_system_info()

def get_detailed_status(printer_ip=None):
    """Get detailed status with progress and system info (convenience function)."""
    comm = get_communicator()
    if printer_ip:
        comm.printer_ip = printer_ip
    return comm.get_detailed_status()


if __name__ == "__main__":
    """
    Command-line interface for printer communication testing.
    
    Usage: python printer_comms.py -i <printer_ip> -c <command>
    
    Commands: getstatus, gopause, goresume, gostop,end, getfile, getmode, sysinfo, detailed
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
                
                # Handle special commands that return structured data
                if command == 'sysinfo':
                    response = comm.get_system_info()
                    if response:
                        print(f"Model: {response['model']}")
                        print(f"Firmware: {response['firmware']}")
                        print(f"Serial: {response['serial']}")
                    else:
                        print("Failed to get system info")
                elif command == 'detailed':
                    response = comm.get_detailed_status()
                    if response:
                        print(f"Status: {response['status']}")
                        print(f"Layer: {response['current_layer']}")
                        print(f"Progress: {response['percent_complete']}%")
                        if 'system_info' in response:
                            print(f"Model: {response['system_info']['model']}")
                    else:
                        print("Failed to get detailed status")
                elif command == 'getfile' or command == 'getfiles':
                    # For GUI compatibility, output simple filenames on separate lines
                    files = comm.get_files()
                    if files:
                        for file_info in files:
                            print(file_info['display_name'])
                    else:
                        print("No files found")
                elif command == 'getstatus':
                    # For GUI compatibility, output raw status string
                    response = comm._run_printer_command(command)
                    if response:
                        print(response)
                    else:
                        print("Command failed")
                else:
                    # Standard commands
                    response = comm._run_printer_command(command)
                    if response:
                        print(response)
                    else:
                        print("Command failed")
    else:
        print("Usage: python printer_comms.py -i <ip> -c <command>")
        print("Example: python printer_comms.py -i 192.168.4.2 -c getstatus")