"""
Printer Communications Module - Handle communication with 3D printer

This module provides a clean interface for communicating with the printer.
Wraps the existing newmonox functionality with better error handling.
"""

import subprocess
import configparser
from pathlib import Path

# Import the existing communication functions if available
try:
    from .newmonox import *
except ImportError:
    # Fall back to subprocess calls if module import fails
    pass


class PrinterCommunicator:
    def __init__(self, config_path=None):
        """Initialize printer communicator with configuration."""
        self.config_path = config_path or self._find_config_path()
        self.config = self._load_config()
        self.printer_ip = self.config.get('printer', 'ip_address', fallback='192.168.4.2')
        self.printer_port = self.config.getint('printer', 'port', fallback=80)
        self.timeout = self.config.getint('printer', 'timeout', fallback=10)
        
    def _find_config_path(self):
        """Find the configuration file."""
        script_dir = Path(__file__).parent
        config_dir = script_dir.parent.parent / 'config'
        return config_dir / 'network_settings.ini'
        
    def _load_config(self):
        """Load configuration from INI file."""
        config = configparser.ConfigParser()
        try:
            config.read(self.config_path)
        except Exception as e:
            print(f"Warning: Could not load config: {e}")
        return config
        
    def _run_printer_command(self, command):
        """
        Run a printer command using the newmonox script.
        
        Args:
            command (str): Command to send to printer
            
        Returns:
            str: Response from printer, or None if error
        """
        try:
            script_path = Path(__file__).parent / 'newmonox.py'
            cmd = [
                'python3', str(script_path),
                '-i', self.printer_ip,
                '-c', command
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print(f"Printer command failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            print(f"Printer command timed out: {command}")
            return None
        except Exception as e:
            print(f"Error running printer command: {e}")
            return None
    
    def get_status(self):
        """
        Get printer status.
        
        Returns:
            str: Status response from printer
        """
        return self._run_printer_command('getstatus')
    
    def pause_print(self):
        """
        Pause the current print job.
        
        Returns:
            bool: True if successful
        """
        response = self._run_printer_command('gopause')
        return response is not None
    
    def resume_print(self):
        """
        Resume the current print job.
        
        Returns:
            bool: True if successful
        """
        response = self._run_printer_command('goresume')
        return response is not None
    
    def stop_print(self):
        """
        Stop the current print job.
        
        Returns:
            bool: True if successful
        """
        response = self._run_printer_command('gostop,end')
        return response is not None
    
    def get_files(self):
        """
        Get list of files on printer.
        
        Returns:
            list: List of file names, or empty list if error
        """
        response = self._run_printer_command('getfiles')
        if response:
            return response.split('\n')
        return []
    
    def start_print(self, filename):
        """
        Start printing a specific file.
        
        Args:
            filename (str): Name of file to print
            
        Returns:
            bool: True if successful
        """
        command = f'goprint,{filename},end'
        response = self._run_printer_command(command)
        return response is not None
    
    def get_mode(self):
        """
        Get printer mode.
        
        Returns:
            str: Printer mode response
        """
        return self._run_printer_command('getmode')
    
    def is_connected(self):
        """
        Check if printer is connected and responding.
        
        Returns:
            bool: True if connected
        """
        status = self.get_status()
        return status is not None and len(status) > 0


# Global instance for easy access
_printer_comm = None

def get_communicator():
    """Get the global printer communicator instance."""
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
    """Test the printer communicator."""
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