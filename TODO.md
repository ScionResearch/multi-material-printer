This list outlines potential improvements and bug fixes for the project.

### High Priority / Bug Fixes

-   [ ] **Fix Typo in `stopAP.sh`:** Correct `sydo` to `sudo` in the `stopAP.sh` script.
-   [ ] **Clean Project Structure:** Move build artifacts (`Makefile`, `moc_*`, etc.) out of the `/scripts` directory and into their respective `/build-*` directories.
-   [ ] **Remove Hardcoded IP Address:** The printer's IP (`192.168.4.2`) is hardcoded in `dialog.cpp` and multiple Python scripts. This should be a configurable setting in the GUI.
-   [ ] **Standardize Application Name:** Rename the Qt project from `untitled6` to a more descriptive name like `ScionMMUController`. This will change the executable and build directory names.

### GUI Improvements

-   [ ] **Integrated Network Manager:** Add a section in the GUI to manage Wi-Fi settings (scan/connect to networks, switch to AP mode) to eliminate the need for shell scripts and manual file editing.
-   [ ] **Display More Printer Status:** Instead of just a "Connected" label, display key information from the `getstatus` command directly in the GUI (e.g., Current Layer, % Complete, Time Remaining).
-   [ ] **Improved Recipe Editor:** Replace the free-text input for material recipes with a more robust UI, such as a table where users can add/edit/remove material change entries. This would reduce formatting errors.
-   [ ] **Simplify "Begin MM" Flow:** The "Begin MM" button should automatically know to run `pollphoton.py`. The current file dialog asking the user to select the script is unnecessary and confusing for an end-user.
-   [ ] **Asynchronous Operations:** GUI operations that call scripts (like "Check Status") can cause the UI to freeze momentarily. These should be moved to separate threads to keep the GUI responsive.

### Functionality Enhancements

-   [ ] **Pump Calibration Routine:** Add a feature to the GUI to help calibrate the pumps (e.g., a "Dispense 10ml" button for each pump) to ensure accurate material swaps.
-   [ ] **Error Handling & Recovery:** Implement more robust error handling. For example, what should the system do if it loses connection to the printer mid-print? Or if a sensor detects a pump has failed?
-   [ ] **Pre-Print Check:** Before starting the MMU process, the software could validate the recipe file and confirm a connection to the printer and MMU hardware.
-   [ ] **Create an Installation Script:** A `install.sh` script would simplify setup by automatically installing all dependencies (Qt libs, Python packages, system tools like `hostapd`).
-   [ ] **Code Documentation:** Add comments and docstrings to the C++ and Python code to make it easier for future developers to understand and maintain.