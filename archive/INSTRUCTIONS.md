# Instructions and Capabilities

## How to Use the System

This guide walks you through setting up the network, using the GUI, and running a multi-material print.

### Step 1: Network Setup

You have two options for connecting the control unit (Raspberry Pi) and the printer.

**Option A: Access Point (AP) Mode (Recommended for initial setup)**

In this mode, the Raspberry Pi creates its own Wi-Fi network. The printer connects to this network. This is useful when you don't have an existing Wi-Fi network available.

1.  Run the AP script on the Raspberry Pi:
    ```bash
    sudo ./startAP.sh
    ```
2.  The Pi will reboot.
3.  On your Anycubic printer's Wi-Fi settings, connect to the network created by the Pi.
4.  The printer's IP address will be **`192.168.4.2`**. The control software is pre-configured for this IP.

**Option B: Wi-Fi Client Mode**

In this mode, both the Raspberry Pi and the printer connect to your existing home/lab Wi-Fi network.

1.  Edit the Wi-Fi configuration file with your network details:
    ```bash
    nano wpa_supplicant.conf
    ```
    Update the `ssid` and `psk` fields.
2.  Run the script to switch out of AP mode:
    ```bash
    sudo ./stopAP.sh
    ```
3.  The Pi will reboot and connect to your Wi-Fi.
4.  **Important:** You must ensure your printer is also connected to this network and update the hardcoded IP address in the control scripts if it is not `192.168.4.2`.

### Step 2: Using the GUI

1.  **Launch the Application:**
    Navigate to the build directory and run the executable:
    ```bash
    ./build-untitled6-LinuxKit-Release/untitled6
    ```
2.  **Check Connection:**
    Click the **"Check Status"** button. The output window should show status details from the printer, and the status label should change to "Connected...". If not, troubleshoot your network connection.

3.  **Prepare a Multi-Material Print:**
    *   In the "Enter Line with Material and Line Number" field, enter your material swap recipe.
    *   The format is `MATERIAL,LAYER:MATERIAL,LAYER:...`
    *   `MATERIAL` is the pump identifier (e.g., A, B, C).
    *   `LAYER` is the layer number at which the material change should occur.
    *   **Example:** `A,50:B,120:C,200` means:
        *   The print starts with the material already in the vat.
        *   At layer 50, the system will pause and switch to material A.
        *   At layer 120, it will pause and switch to material B.
        *   At layer 200, it will pause and switch to material C.
    *   Click the **"Set"** button to save this recipe.

4.  **Start a Print:**
    *   First, start a normal print job from the printer's own interface or by using the "Get Files" button in the GUI and selecting a file to print.
    *   Once the print has started, click the **"Begin MM"** button in the GUI.
    *   A file dialog will appear. Select the main polling script: `scionresearch-multi-material-printer/scripts/pollphoton.py`.
    *   The system will now monitor the print and perform the material swaps automatically at the layers you defined. The output window will show the progress.

### Step 3: Other Controls

*   **Motor Control:**
    *   Use this for priming or testing pumps.
    *   **Format:** `PUMP,DIRECTION,TIME_IN_SECONDS` (e.g., `A,F,30`)
    *   `PUMP`: A, B, C, or D.
    *   `DIRECTION`: `F` for Forward, `R` for Reverse.
    *   `TIME_IN_SECONDS`: How long to run the pump.
    *   Click **"Motor Run"** to start and **"Motor Stop"** to interrupt.
*   **Printer Controls:**
    *   **Pause/Resume/Stop Printer:** These buttons send direct commands to the printer.
    *   **Stop MM:** This button stops the multi-material polling script (`pollphoton.py`) but does **not** stop the printer itself. Use this to cancel the automated swapping process.

## System Capabilities

*   **Network Management:** Switch the control unit between a self-contained Access Point and a standard Wi-Fi client.
*   **File Management:** List printable files stored on the printer's internal memory.
*   **Standard Print Operations:** Start, pause, resume, and stop prints directly from the interface.
*   **Multi-Material Recipe:** Define a sequence of material changes based on specific 3D print layer numbers.
*   **Automated Print Execution:** The system automatically executes the multi-material recipe by:
    1.  Continuously polling the printer for its current layer number.
    2.  Pausing the print job when a target layer is reached.
    3.  Activating the correct pumps to perform the material swap.
    4.  Resuming the print job automatically.
*   **Manual Pump Control:** Run any pump forwards or backwards for a specified duration for maintenance and setup.
*   **Live Operation Logging:** A text-based output provides real-time feedback on commands sent, printer status, and script actions.

