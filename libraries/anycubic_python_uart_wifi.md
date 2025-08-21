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