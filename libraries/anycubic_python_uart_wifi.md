### **`anycubic-python` (`uart-wifi`) Library: Capabilities Summary**

The `anycubic-python` repository provides the **`uart-wifi` library**, a specialized tool for communicating with Anycubic Mono X (and similar) printers over Wi-Fi. Its primary purpose is to abstract the low-level network protocol, allowing you to work with clean Python objects instead of raw text strings.

#### **Key Features & Benefits for Your Project:**

*   **Structured Data:** Converts cryptic printer responses (e.g., `"getstatus,print,file.pwmb/1,..."`) into easy-to-use Python objects with named attributes (e.g., `status.current_layer`).
*   **Simplified Network Management:** Handles all socket creation, connection, timeouts, and error handling for you.
*   **Built-in Printer Simulator:** Includes a `fake_printer.py` script, allowing you to develop and test your GUI application without needing a physical printer connected.

---

### **Core Usage Pattern**

All interactions with the library follow a simple three-step process:

```python
# 1. Import the main class and instantiate it
from uart_wifi.communication import UartWifi
uart = UartWifi("YOUR_PRINTER_IP", 6000)

# 2. Send a command string
# The library returns a list of one or more response objects
responses = uart.send_request("getstatus")

# 3. Process the response object(s)
if responses:
    status_object = responses[0]
    print(f"Printer is currently: {status_object.status}")
    if status_object.status == "print":
        print(f"Printing layer: {status_object.current_layer}")
```

---

### **Capabilities Reference Guide**

Here is a reference table of the library's main capabilities, the exact command to use, the Python object you get back, and a practical code example.

| Capability | Command String | Returned Object(s) | Example Usage & Key Attributes |
| :--- | :--- | :--- | :--- |
| **Get Printer Status** | `"getstatus"` | `MonoXStatus` | The most important command for monitoring. <br> ```python<br>responses = uart.send_request("getstatus")<br>if responses:<br>  status = responses[0]<br>  print(f"State: {status.status}") # 'print', 'paused', 'stop' <br>  print(f"Layer: {status.current_layer}")<br>  print(f"Progress: {status.percent_complete}%")<br>``` |
| **List Printable Files** | `"getfile"` | `FileList`, which contains a list of `MonoXFileEntry` objects | Used to populate a file list in your GUI. <br> ```python<br>responses = uart.send_request("getfile")<br>if responses:<br>  file_list = responses[0]<br>  for file in file_list.files:<br>    print(f"Filename: {file.external}")<br>    print(f"  Internal ID: {file.internal}")<br>``` |
| **Start a Print** | `"goprint,<internal_name>,end"` | `InvalidResponse` | Takes the **internal name** from the `getfile` command. <br> ```python<br># Example: Start printing the file with internal ID '0.pwmb'<br>internal_id = "0.pwmb"<br>cmd = f"goprint,{internal_id},end"<br>responses = uart.send_request(cmd)<br>if responses and responses[0].status == "OK":<br>  print("Print started successfully!")<br>``` |
| **Pause a Print** | `"gopause"` | `InvalidResponse` | Pauses the currently active print job. <br> ```python<br>responses = uart.send_request("gopause")<br>if responses and responses[0].status == "OK":<br>  print("Print paused.")<br>``` |
| **Resume a Print** | `"goresume"` | `InvalidResponse` | Resumes a previously paused print job. <br> ```python<br>responses = uart.send_request("goresume")<br>if responses and responses[0].status == "OK":<br>  print("Print resumed.")<br>``` |
| **Stop a Print** | `"gostop,end"` | `InvalidResponse` | Immediately terminates the active print job. <br> ```python<br>responses = uart.send_request("gostop,end")<br>if responses and responses[0].status == "OK":<br>  print("Print stopped.")<br>``` |
| **Get System Info** | `"sysinfo"` | `MonoXSysInfo` | Retrieves identifying information from the printer. <br> ```python<br>responses = uart.send_request("sysinfo")<br>if responses:<br>  info = responses[0]<br>  print(f"Model: {info.model}")<br>  print(f"Firmware: {info.firmware}")<br>  print(f"Serial: {info.serial}")<br>``` |

---

### **Special Capability: The Printer Simulator**

The repository includes a powerful tool for development and testing that runs from the command line.

**What it is:** A Python script (`fake_printer.py`) that listens on a network port and responds to commands exactly like a real printer.

**How to Use It:**
1.  Run the simulator in a separate terminal:
    ```bash
    # You can find this script inside the installed uart-wifi package
    # or run it from the cloned anycubic-python repository.
    python3 src/uart_wifi/scripts/fake_printer.py --port 6000
    ```
2.  In your C++ GUI's configuration, set the printer's IP address to `127.0.0.1`.

**Why this is valuable for you:**
*   You can fully develop and test your GUI's logic (parsing status, sending commands, reacting to state changes) on your development machine without needing a physical Raspberry Pi or printer.
*   You can simulate different states. For example, you can modify the fake printer to respond with a specific layer number to test if your material-change logic triggers correctly.





Directory structure:
└── adamoutler-anycubic-python/
    ├── README.md
    └── src/
        └── uart_wifi/
            ├── __init__.py
            ├── __main__.py
            ├── communication.py
            ├── errors.py
            ├── response.py
            ├── simulate_printer.py
            └── scripts/
                ├── __init__.py
                ├── fake_printer
                ├── monox
                ├── fake_printer.py -> fake_printer
                └── monox.py -> monox


Files Content:

================================================
FILE: README.md
================================================
# About
This is a library to provide support for Mono X Printers.

# uart-wifi
the [uart-wifi](https://pypi.org/project/uart-wifi/) library can be downloaded from PyPI.  It contains required python tools for communicating with MonoX Printers. To install, simply install Python, then type `pip install uart-wifi`. After which, you can create fake printers and communicate with them.
![](img/fakeprinter.png)

## monox.py
A command line script to gather information from the Mono X printer.  This is tested working on the Anycubic Mono X 6k and should work on any Mono X or Mono SE printer.

    Usage: monox.py -i <ip address> -c <command>
    args:
     -i [--ipaddress=] - The IP address which your Anycubic Mono X can be reached

     -c [--command=] - The command to send.

    Commands may be used one-at-a-time. Only one command may be sent and it is expected to be in the format below.

    Command: getstatus - Returns a list of printer statuses.

    Command: getfile - returns a list of files in format <internal name>: <file name>.  When referring to the file via command, use the <internal name>.

    Command: sysinfo - returns Model, Firmware version, Serial Number, and wifi network.

    Command: getwifi - displays the current wifi network name.

    Command: gopause - pauses the current print.

    Command: goresume - ends the current print.

    Command: gostop,end - stops the current print.

    Command: delfile,<internal name>,end - deletes a file.

    Command: gethistory,end - gets the history and print settings
    of previous prints.

    Command: delhistory,end - deletes printing history.

    Command: goprint,<internal name>,end - Starts a print of the
    requested file

    Command: getPreview1,<internal name>,end - returns a list of dimensions used for the print.

## fake_printer.py
A command line script to simulate a MonoX 3D printer for testing purposes. You can simulate a fleet of Mono X 3D printers!

    Usage: fake_printer.py -i <ip address> -c <command>
    args:
     [-i, [--ipaddress=]] - The IP address which to acknowledge requests. This defaults to any or 0.0.0.0.

     [-p [--port=]] - The port to listen on. This defaults to 6000.



================================================
FILE: src/uart_wifi/__init__.py
================================================
[Empty file]


================================================
FILE: src/uart_wifi/__main__.py
================================================
"""Main executable. Imports the monox script and causes execution."""
from uart_wifi.scripts import monox

print(f'this should be executed from "{monox.__file__}".')



================================================
FILE: src/uart_wifi/communication.py
================================================
"""Communications with MonoX devices. -Adam Outler -
email: adamoutler(a)hackedyour.info
The development environment is Visual Studio Code.
See launch.json for auto-config.
"""

import logging
import os
import select
import sys
from queue import Empty

from socket import AF_INET, SOCK_STREAM, socket
import tempfile
import time
from typing import Iterable

from uart_wifi.errors import ConnectionException

from .response import (
    FileList,
    InvalidResponse,
    MonoXPreviewImage,
    MonoXResponseType,
    MonoXStatus,
    MonoXSysInfo,
)

# Port to listen on

HOST = "192.168.1.254"
COMMAND = "getstatus"
endRequired = ["goprint", "gostop", "gopause", "delfile"]
END = ",end"
ENCODING = "gbk"
_LOGGER = logging.getLogger(__name__)
Any = object()
MAX_REQUEST_TIME = 10  # seconds
Response = Iterable[MonoXResponseType]


class UartWifi:
    """Mono X Class"""

    max_request_time = MAX_REQUEST_TIME

    def __init__(self, ip_address: str, port: int) -> None:
        """Create a communications UartWifi class.
        :ip_address: The IP to initiate communications with.
        :port: The port to use.
        """
        self.server_address = (ip_address, port)
        self.raw = False
        self.telnet_socket = socket(AF_INET, SOCK_STREAM)

    def set_maximum_request_time(self, max_request_time: int) -> None:
        """Set the maximum time to wait for a response.
        :max_request_time: The maximum time to wait for a response.
        """
        self.max_request_time = max_request_time

    def set_raw(self, raw: bool = True) -> None:
        """Set raw mode.
        :raw: Set to true if we are outputting raw data instead of processed
            classes.
        """
        self.raw = raw

    def send_request(
        self, message_to_be_sent: str
    ) -> Iterable[MonoXResponseType]:
        """sends the Mono X request.
        :message_to_be_sent: The properly-formatted uart-wifi message as it is
        to be sent.
        :returns: an object from Response class.
        """

        return_value = self._send_request(message_to_be_sent)
        return return_value

    def _send_request(self, message: str) -> Iterable[MonoXResponseType]:
        """sends the Mono X request.
        :message_to_be_sent: The properly-formatted uart-wifi message as it is
        to be sent.
        :returns: an object from Response class.
        """
        return_value = self._async_send_request(message)
        return return_value

    def _async_send_request(
        self, message_to_be_sent: str
    ) -> Iterable[MonoXResponseType]:
        """sends the Mono X request.
        :message_to_be_sent: The properly-formatted uart-wifi message as it is
        to be sent.
        :returns: an object from Response class.
        """
        request = bytes(message_to_be_sent, "utf-8")
        received: str = _do_request(
            self.telnet_socket,
            self.server_address,
            request,
            self.max_request_time,
        )
        if self.raw:
            return received
        processed = _do_handle(received)
        return processed


def _do_request(
    sock: socket,
    socket_address: tuple,
    to_be_sent: bytes,
    max_request_time: int,
) -> str:
    """Perform the request

    :param sock: the socket to use for the request
    :param request: the request to send
    :return: a MonoX object"""
    text_received = ""
    try:
        sock = _setup_socket(socket_address)
        sock.sendall(to_be_sent)
        sent_string = to_be_sent.decode()
        if sent_string.endswith("shutdown"):
            return "shutdown,end"
        if sent_string.startswith("b'getPreview2"):
            text_received = bytearray()
            print(text_received)
            end_time = current_milli_time() + (max_request_time * 1000)
            while (
                not str(text_received).endswith(END)
                and current_milli_time() < end_time
            ):
                text_received.extend(sock.recv(1))
        else:

            read_list = [sock]
            port_read_delay = current_milli_time()
            end_time = current_milli_time() + (max_request_time * 1000)
            text_received = handle_request(
                sock,
                text_received,
                end_time,
                read_list,
                port_read_delay,
                max_request_time,
            )

    except (
        OSError,
        ConnectionRefusedError,
        ConnectionResetError,
    ) as exception:
        raise ConnectionException(
            "Could not connect to AnyCubic printer at " + socket_address[0]
        ) from exception
    finally:
        sock.close()
    return text_received


def handle_request(
    sock, text_received, end_time, read_list, port_read_delay, max_request_time
) -> str:
    """performs the request handling"""
    while True:
        current_time = current_milli_time()
        if end_time > current_time or port_read_delay > current_time:
            readable, [], [] = select.select(
                read_list, [], [], max_request_time
            )
            for read_port in readable:
                if read_port is sock:
                    port_read_delay = current_milli_time() + 8000
                    text_received += str(read_port.recv(1).decode())
        if end_time < current_milli_time() or text_received.endswith(",end"):
            break
    return text_received


def _setup_socket(socket_address):
    """Setup the socket for communication
    socket_address: the tupple consisting of (ip_address, port).
    """
    _LOGGER.debug("connecting to %s", socket_address)
    sock = socket(AF_INET, SOCK_STREAM)
    sock.settimeout(2)
    sock.connect(socket_address)
    sock.settimeout(MAX_REQUEST_TIME)
    return sock


def __do_preview2(received_message: bytearray()):
    """Handles preview by writing to file.
    :received_message: The message, as received from UART wifi
    protocol, to be converted to an image.
    """

    filename = received_message.decode("utf_8").split(",", 3)[1]
    file = tempfile.gettempdir() + os.path.sep + filename + ".bmp"
    print(file)

    output_file = open(file=file, mode="rb")

    width = 240
    height = 168

    file_size = os.path.getsize(file)
    pos_in_image = 0
    max_line_length = width * 2
    slices = []
    for row in range(0, height):
        current_slice = bytearray()
        for current_byte in range(0, max_line_length):
            current_byte = (row * max_line_length) + current_byte
            if file_size >= current_byte:
                current_slice.append(output_file.read(2))
            current_byte += 2
            slices.append(current_slice)

    my_slice = [[]]
    for byte in slices:
        print(type(byte))
        my_slice[pos_in_image] = byte[0]
        pos_in_image += 1
        if pos_in_image > (240 * 2):
            pos_in_image = 0
            current_slice = bytearray
            my_slice.append(current_slice)

    # image = Image.new("RGB", (width, height))
    # file_format = "bmp"  # The file extension of the sourced data
    print(len(my_slice))

    print(my_slice)

    # bytes(byte_array)
    # image.write(output_file,file_format)

    # output_file.close()

    return MonoXPreviewImage("")


def _do_handle(message: str) -> Iterable[MonoXResponseType]:
    """Perform handling of the message received by the request"""
    if message is None:
        return "no response"

    lines = message.split(",end")
    recognized_response: Iterable = list()
    for line in lines:
        fields: list(str) = line.split(",")
        message_type = fields[0]
        if len(fields) is Empty or len(fields) < 2:
            continue
        if message_type == "getstatus":
            recognized_response.append(__do_status(fields))
        elif message_type == "getfile":
            recognized_response.append(__do_files(fields))
        elif message_type == "sysinfo":
            recognized_response.append(__do_sys_info(fields))
        elif message_type == "gethistory":
            recognized_response.append(__do_get_history(fields))
        elif message_type == "doPreview2":
            recognized_response.append(__do_preview2(fields))
        # goprint,49.pwmb,end
        elif message_type in [
            "goprint",
            "gostop",
            "gopause",
            "getmode",
            "getwifi",
        ]:
            recognized_response.append(InvalidResponse(fields[1]))
        else:
            print("unrecognized command: " + message_type, file=sys.stderr)
            print(line, file=sys.stderr)
            if recognized_response is not None:
                recognized_response.append(InvalidResponse(fields[1]))

    return recognized_response


def __do_get_history(fields: Iterable):
    """Handles history processing."""
    items = []
    for field in fields:
        if field in fields[0] or fields[-1]:
            continue
        items.append(field)
    return items


def __do_sys_info(fields: Iterable):
    """Handles system info processing."""
    sys_info = MonoXSysInfo()
    if len(fields) > 2:
        sys_info.model = fields[1]
    if len(fields) > 3:
        sys_info.firmware = fields[2]
    if len(fields) > 4:
        sys_info.serial = fields[3]
    if len(fields) > 5:
        sys_info.wifi = fields[4]
    return sys_info


def __do_files(fields: Iterable):
    """Handles file processing."""
    files = FileList(fields)
    return files


def __do_status(fields: Iterable):
    """Handles status processing."""
    status = MonoXStatus(fields)
    return status


def current_milli_time():
    return round(time.time() * 1000)



================================================
FILE: src/uart_wifi/errors.py
================================================
"""Exceptions"""


class AnycubicException(Exception):
    """Base class for Anycubic exceptions."""


class ConnectionException(AnycubicException):
    """Problem when connecting"""



================================================
FILE: src/uart_wifi/response.py
================================================
"""Mono X Objects."""


# pylint: disable=too-few-public-methods
class MonoXResponseType:
    """The baseline MonoX Response class.
    Use this to create other MonoX Responses."""

    status: str = "error/offline"

    def print(self):
        """Print the MonoXResponse. Should be overridden
        by anything which implements this class."""
        return "Status: " + self.status


class MonoXFileEntry(MonoXResponseType):
    """A file entry consisting of an internal and external listing"""

    def __init__(self, internal_name: str, external_name: str) -> None:
        """Create a MonoXFileEntry
        :internal_name: the name the printer calls the file. eg "1.pwmb"
        :external_name: The name the user calls the file.
        eg "My (Super) Cool.pwmb"
        """
        self.external = internal_name
        self.internal = external_name
        self.status = "file"

    def print(self):
        """Provide a human-readable response"""
        print(self.internal + ": " + self.external)


class FileList(MonoXResponseType):
    """handles lists of files.
    eg.
    getfile,
    2-phone-stands.pwmb/0.pwmb,
    SLA print puller supported.pwmb/1.pwmb,
    2 phone stands on side.pwmb/2.pwmb,
    5x USB_Cable_Holder_7w_Screws_hollow.pwmb/3.pwmb,
    end
    """

    def __init__(self, data: MonoXFileEntry) -> None:
        """Create a FileList object.
        :data: a list of internal/external files.
        """
        self.files = []
        self.status = "getfile"

        for field in data:
            if field in data[0] or data[-1]:
                continue  # not interested in packet open/close portion.
            split = field.split("/")
            self.files.append(MonoXFileEntry(split[0], split[1]))

    files = [MonoXFileEntry]

    def print(self):
        """Provide a human-readable response."""
        for file in self.files:
            file.print()


class InvalidResponse(MonoXResponseType):
    """Used when no response is provided."""

    def __init__(self, message) -> None:
        """Construct the InvalidResponse type.
        :message: anything goes
        """
        self.status = message

    def print(self):
        """Provide a human-readable response."""
        print("Invalid Response: " + self.status)


class SimpleResponse(MonoXResponseType):
    """Used when no response is provided."""

    def __init__(self, message) -> None:
        """Construct a SimpleResponse.
        :message: anything goes."""
        self.status = message

    def print(self):
        """Provide a human-readable response."""
        print("Response: " + self.status)


class MonoXSysInfo(MonoXResponseType):
    """The sysinfo handler. Handles sysinfo messages.
    eg message.
        sysinfo,Photon Mono X 6K,V0.2.2,0000170300020034,SkyNet,end
    """

    def __init__(self, model="", firmware="", serial="", wifi="") -> None:
        """Construct the MonoXSysInfo response type"""
        self.model = model
        self.firmware = firmware
        self.serial = serial
        self.wifi = wifi
        self.status = "updated"

    def print(self):
        """Provide a human-readable response"""
        print("model: " + self.model)
        print("firmware: " + self.firmware)
        print("serial: " + self.serial)
        print("wifi: " + self.wifi)


# pylint: disable=too-many-instance-attributes
class MonoXStatus(MonoXResponseType):
    """Status object for MonoX.

    eg message.
       getstatus,print,Widget.pwmb/46.pwmb,2338,88,2062,51744,6844,~178mL,UV,39.38,0.05,0,end
    """

    def __init__(self, message) -> None:
        """Construct the Status response.
        :message: a properly formated message of either length 3 or >12."""

        self.status = message[1]
        if len(message) > 2:
            self.file = message[2]
        if len(message) > 3:
            self.total_layers = message[3]
        if len(message) > 4:
            self.percent_complete = message[4]
        if len(message) > 5:
            self.current_layer = message[5]
        if len(message) > 6:
            if str(message[6]).isnumeric():
                self.seconds_elapse = int(message[6]) * 60
            else:
                self.seconds_elapse = message[6]
        if len(message) > 7:
            self.seconds_remaining = message[7]
        if len(message) > 8:
            self.total_volume = message[8]
        if len(message) > 9:
            self.mode = message[9]
        if len(message) > 10:
            self.unknown1 = message[10]
        if len(message) > 11:
            self.layer_height = message[11]
        if len(message) > 12:
            self.unknown2 = message[12]

    def print(self):
        """Provide a human-readable response."""
        print("status: " + self.status)
        if hasattr(self, "file"):
            print("file: " + self.file)
            print("total_layers: " + str(self.total_layers))
            print("percent_complete: " + str(self.percent_complete))
            print("current_layer: " + str(self.current_layer))
            print("seconds_remaining: " + str(self.seconds_remaining))
            print("total_volume: " + str(self.total_volume))
            print("mode: " + self.mode)
            print("unknown1: " + str(self.unknown1))
            print("layer_height: " + str(self.layer_height))
            print("unknown2: " + str(self.unknown2))


class MonoXPreviewImage(MonoXResponseType):
    """A file entry consisting of an internal and external listing."""

    def __init__(self, file_path: str) -> None:
        """Construct the MonoXPreviewImage.
        :file_path: the path to the preview image.
        """
        super().__init__()
        self.file_path = file_path
        self.status = "preview image"

    def print(self):
        """Provide a human-readable response."""
        print(f"preview located at {self.file_path}")



================================================
FILE: src/uart_wifi/simulate_printer.py
================================================
""""Class to handle printer simulation"""
import select
import socket
import threading
import time


class AnycubicSimulator:
    """ "Simulator for Anycubic Printer."""

    port = "6000"
    printing = False
    serial = "0000170300020034"
    shutdown_signal = False

    def __init__(self, the_ip: str, the_port: int) -> None:
        """Construct the Anycubic Simulator
        :the_ip: The IP address to use internally for opening the port.
            eg. 127.0.0.1, or 0.0.0.0
        :the_port: The port to monitor for responses.
        """
        self.host = the_ip
        self.port = the_port
        self.printing = False
        self.serial = "234234234"

    def sysinfo(self) -> str:
        """return sysinfo type"""
        return "sysinfo,Photon Mono X 6K,V0.2.2," + self.serial + ",SkyNet,end"

    def getfile(self) -> str:
        """return getfile type"""
        return "getfile,Widget.pwmb/0.pwmb,end"

    def getstatus(self) -> str:
        """return getstatus type"""
        if self.printing:
            return (
                "getstatus,print,Widget.pwmb"
                "/46.pwmb,2338,88,2062,51744,6844,~178mL,UV,39.38,0.05,0,end"
            )
        return "getstatus,stop\r\n,end"

    def goprint(self) -> str:
        """Do printing"""
        if self.printing:
            return "goprint,ERROR1,end"
        self.printing = True
        return "goprint,OK,end"

    def gostop(self) -> str:
        """Do Stop printing"""
        if not self.printing:
            return "gostop,ERROR1,end"
        self.printing = False
        return "gostop,OK,end"

    def start_server(self):
        """Start the uart_wifi simualtor server"""
        my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        my_socket.bind((self.host, self.port))
        self.port = my_socket.getsockname()[1]
        print(f"Starting printer on {self.host}:{self.port}")
        my_socket.listen(1)
        my_socket.setblocking(False)
        read_list = [my_socket]
        while not AnycubicSimulator.shutdown_signal:
            readable, [], [] = select.select(read_list, [], [])
            for the_socket in readable:
                if the_socket is my_socket:
                    try:
                        conn, addr = the_socket.accept()
                        thread = threading.Thread(
                            target=self.response_selector,
                            args=(conn, addr),
                        )
                        thread.daemon = True
                        thread.start()
                    except Exception:  # pylint: disable=broad-except
                        pass
                    finally:
                        time.sleep(1)

    def response_selector(self, conn: socket.socket, addr) -> None:
        """The connection handler
        :conn: The connection to use
        :addr: address tuple for ip and port
        """
        print(f"Simulator: accepted connection to {addr}")
        decoded_data = ""
        with conn:
            while (
                "," not in decoded_data
                and "\n" not in decoded_data
                and not AnycubicSimulator.shutdown_signal
            ):
                data = conn.recv(1)
                decoded_data += data.decode()
                if "111\n" in decoded_data:
                    decoded_data = ""
                    continue
            try:
                print("Hex:")
                print(" ".join(f"{hex:02x}" for hex in decoded_data.encode()))
                print("Data:")
                print(decoded_data)
            except UnicodeDecodeError:
                pass
            self.send_response(conn, decoded_data)
            decoded_data = ""

    def send_response(self, conn: socket.socket, decoded_data: str) -> None:
        """Send a response

        :conn: The connection to use
        :addr: address tuple for ip and port
        """
        split_data = decoded_data.split(",")
        for split in split_data:
            if split == "":
                continue
            if "getstatus" in split:
                return_value = self.getstatus()
                conn.sendall(return_value.encode())
            if "sysinfo" in split:
                conn.sendall(self.sysinfo().encode())
            if "getfile" in split:
                conn.sendall(self.getfile().encode())
            if "goprint" in split:
                conn.sendall(self.goprint().encode())
                decoded_data = ""
            if "gostop" in split:
                value = self.gostop()
                print("sent:" + value)
                conn.sendall(value.encode())
            if "getmode" in split:
                value = "getmode,0,end"
                print("sent:" + value)
                conn.sendall(value.encode())
                decoded_data = ""
            if "incomplete" in split:
                value = "getmode,0,"
                print("sent:" + value)
                conn.sendall(value.encode())
                decoded_data = ""
            if "timeout" in split:
                time.sleep(99999)

            if "multi" in split:
                value = self.getstatus() + self.sysinfo() + "getmode,0,end"
                print("sent:" + value)
                conn.sendall(value.encode())
                decoded_data = ""
            if decoded_data.endswith("shutdown,"):
                value = "shutdown,end"
                print("sent:" + value)
                conn.sendall(value.encode())
                AnycubicSimulator.shutdown_signal = True



================================================
FILE: src/uart_wifi/scripts/__init__.py
================================================
[Empty file]


================================================
FILE: src/uart_wifi/scripts/fake_printer
================================================
#! python3
"""Fake Anycubic Printer for tests"""
import getopt

import sys
from uart_wifi.simulate_printer import AnycubicSimulator


def start_server(the_ip: str, port: int) -> None:
    """Starts the server
    :the_ip: The IP address to use internally for opening the port.
        eg. 127.0.0.1, or 0.0.0.0
    :the_port: The port to monitor for responses.
    """
    AnycubicSimulator(the_ip, int(port)).start_server()


opts, args = getopt.gnu_getopt(sys.argv, "i:p:", ["ipaddress=", "port="])

IP_ADDRESS = "0.0.0.0"
PORT = 6000
for opt, arg in opts:
    if opt in ("-i", "--ipaddress"):
        IP_ADDRESS = arg
    elif opt in ("-p", "--port"):
        PORT = arg
        print("Opening printer on port " + arg)


start_server(IP_ADDRESS, PORT)



================================================
FILE: src/uart_wifi/scripts/monox
================================================
#! python3
"""Uart wifi"""

import getopt
import sys
import time
from typing import Iterable

from uart_wifi.communication import UartWifi
from uart_wifi.errors import ConnectionException
from uart_wifi.response import MonoXResponseType


PORT = 6000
HELP = (
    __file__
    + """ | Adam Outler (monox@hackedyour.info) | GPLv3

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
)


try:
    opts, args = getopt.gnu_getopt(
        sys.argv, "drhi:c:p:", ["raw", "ipaddress=", "command=", "port="]
    )
# pylint: disable=broad-except
except Exception:
    print(HELP)
    sys.exit(0)

USE_RAW = False
for opt, arg in opts:
    if opt == "-h":
        print(HELP)
        sys.exit()
    elif opt in "-d":
        time.sleep(1)
    elif opt in ("-r", "--raw"):
        USE_RAW = True
    elif opt in ("-i", "--ipaddress"):
        ip_address = arg
    elif opt in ("-p", "--port"):
        PORT = int(arg)
    elif opt in ("-c", "--command"):
        command = arg
        print(arg)

if "ip_address" not in locals():
    print("You must specify the host ip address (-i xxx.xxx.xxx.xxx)")
    sys.exit(1)

if ip_address == "127.0.0.1":
    time.sleep(1)
responses = None  # pylint: disable=invalid-name
# Try 3 times to get the data.
attempts: int = 0
while attempts < 3:
    try:
        uart = UartWifi(ip_address, PORT)
        if USE_RAW:
            uart.raw = True
        responses: Iterable[MonoXResponseType] = uart.send_request(command)

        break
    except ConnectionException:
        attempts += 1


if responses is not None and isinstance(responses, Iterable):
    for response in responses:
        if isinstance(response, MonoXResponseType):
            response.print()
        else:
            print(response)
else:
    print(responses)



================================================
SYMLINK: src/uart_wifi/scripts/fake_printer.py -> fake_printer
================================================



================================================
SYMLINK: src/uart_wifi/scripts/monox.py -> monox
================================================


