#! python3
"""Uart wifi"""

import argparse
import sys
import time
from typing import Iterable

from uart_wifi.communication import UartWifi
from uart_wifi.errors import ConnectionException
from uart_wifi.response import MonoXResponseType

"""
Usage: monox.py -i <ip address> -c <command>
args:
 -i [--ipaddress=] - The IP address which your Anycubic Mono X can be reached

 -c [--command=] - The command to send.
   Commands may be used one-at-a-time. Only one command may be sent and it is
        expected to be in the format below.
    Command: getstatus - Returns a list of printer statuses.
    Command: getfile - returns a list of files in format <internal name>:
        <file name>.
        When referring to the file via command, use the <internal name>.
    Command: sysinfo - returns Model, Firmware version, Serial Number,
        and wifi network.
    Command: getwifi - displays the current wifi network name.
    Command: gopause - pauses the current print.
    Command: goresume - ends the current print.
    Command: gostop,end - stops the current print.
    Command: delfile,<internal name>,end - deletes a file.
    command: gethistory,end - gets the history and print settings of previous
        prints.
    Command: delhistory,end - deletes printing history.
    Command: goprint,<internal name>,end - Starts a print of the requested file
    Command: getPreview1,<internal name>,end - returns a list of dimensions
        used for the print.

   Not Supported Commands may return unusable results.
    Command (Not Supported): getPreview2,<internal name>,end
     - returns a binary preview image of the print.

   Unknown Commands are at your own risk and experimentation.
   No attempt is made to process or stop execution of these commands.
    Command: detect
    Command: stopUV - unknown
    Command: getpara - unknown
    Command: getmode - unknown
    Command: setname - unknown
    Command: getname - unknown
    Command: setwifi - unknown
    Command: setZero - unknown
    Command: setZhome - unknown
    Command: setZmove - unknown
    Command: setZstop - unknown
    """


PORT = 6000

def send_command(ip_address: str, port: int, command: str, use_raw: bool) -> Iterable[MonoXResponseType]:
    # Try 3 times to get the data.
    for attempt in range(3):
        try:
            uart = UartWifi(ip_address, port)
            if use_raw:
                uart.raw = True
            return uart.send_request(command)
        except ConnectionException:
            time.sleep(1) # You may want to adjust the sleep time based on your requirements.
            continue
    raise ConnectionException(f"Failed to send command after 3 attempts.")

def parse_args():
    parser = argparse.ArgumentParser(description='Mono X control')
    parser.add_argument('-i', '--ipaddress', required=True, help='The IP address which your Anycubic Mono X can be reached')
    parser.add_argument('-c', '--command', required=True, help='The command to send.')
    parser.add_argument('-p', '--port', default=PORT, type=int, help='Port to connect to. Default is 6000.')
    parser.add_argument('-r', '--raw', action='store_true', help='Use raw command.')
    return parser.parse_args()

def main():
    args = parse_args()
    responses = send_command(args.ipaddress, args.port, args.command, args.raw)
    if responses is not None and isinstance(responses, Iterable):
        for response in responses:
            if isinstance(response, MonoXResponseType):
                if response is not None and str(response).strip():
                    response.print()
            elif response is not None and str(response).strip():
                print(response)
            else:
                print(response)
    else:
        print(responses)

if __name__ == "__main__":
    main()
