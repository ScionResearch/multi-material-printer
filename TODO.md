
# UI issues
- ✅ **FIXED** - after printer stopped current layer and active material should update to cleared (based on the status messages sent by the printer) multi material recipe should also stop when the print is stopped.
  - Frontend: app.js:289-299 - State reset when printer status is STOPPRN/stopped/idle/ready
  - Backend: print_manager.py:643-647 - Auto-deactivate recipe when printer stops

- ✅ **FIXED** - check the layer and progress increments correctly in the dashboard during a print. the printer can provide more information from the file (total layer height etc) and the status should show increments of the current layer as a percentage of the total layer height for the file.
  - Backend: print_manager.py:658-659 - Now sends total_layers and percent_complete
  - Frontend: app.js:14,224-228,313-318,462-473 - Displays "Layer X / Y (Z%)" format

- ✅ **FIXED** - Check that pump status is updating in the UI (pumps turning green when pump is running)
  - Frontend: app.js:954,969 - Changed running pumps from bg-warning/text-warning to bg-success/text-success
  - Backend already sends pump_status updates via OPERATION_STATUS events

- check that hardware diagnostics works correctly

- check the logging in system configuration is wired up and functional 







### Material Change Testing
- [] **Validate material change sequence**
  - Monitor bed position during material changes
  - Verify pump operation timing
  - Confirm proper resume after material change

### Log Analysis Issues (from 2025-10-04 test) - INVESTIGATED

#### 🔴 Critical Priority

##### **Resume Command Issue** - printer_comms.py
**Root Cause:** The `goresume` command IS valid, but uart-wifi library doesn't recognize it
- Line 452 in uart_wifi/communication.py prints "unrecognized command" to stderr when command not in recognized list
- However, printer DOES process it (returns "goresume,OK" on second line)
- Library still wraps it as InvalidResponse and returns it
**Files:**
- src/controller/printer_comms.py:146 (sends goresume)
- uart_wifi library communication.py:452 (unrecognized command handler)
**Impact:** Cosmetic error in logs, command actually works
**Evidence:** All 3 material changes completed successfully despite "unrecognized" message

##### **Printer Disconnections After Resume** - print_manager.py
**Root Cause:** NOT related to invalid command (see above - command works)
- Disconnection pattern: 15s after each resume (1759544881→1759544896, 1759544955→1759544970)
- Likely printer firmware behavior after receiving certain commands
- System recovers automatically within 5s
**Files:** src/controller/print_manager.py (monitoring loop)
**Impact:** Temporary loss of visibility, no functional impact
**Evidence:** Print continues normally, status resumes after reconnect

#### 🟡 Medium Priority

##### **Duplicate Command Processing** - websocket_ipc.py + print_manager.py
**Root Cause:** Commands processed TWICE - via callback AND queue
- websocket_ipc.py:165: Adds command to queue
- websocket_ipc.py:169: Calls on_command_received callback (processes command #1)
- print_manager.py:190: Registers callback = _handle_websocket_command
- print_manager.py:533: Also calls get_next_command() from queue (processes command #2)
**Files:**
- src/controller/websocket_ipc.py:165-169 (dual processing)
- src/controller/print_manager.py:190, 533 (both handlers active)
**Impact:** Doubles log entries (1210→605 lines), potential race conditions
**Evidence:** Every command shows twice in logs 0.3s apart with identical timestamps

##### **Quiescent Window Not Enforced** - print_manager.py:_pause_printer() + _handle_material_change()
**Root Cause:** Window DECLARED but not WAITED before bed positioning
- print_manager.py:763: Sets `_quiescent_until = time.time() + 10`
- print_manager.py:764: Logs "Quiescent window started..."
- print_manager.py:709: Immediately calls `_wait_for_bed_raised()` (NO WAIT!)
- _wait_for_bed_raised():796: First actual sleep is 2s (for pause command propagation)
**Files:**
- src/controller/print_manager.py:753-768 (_pause_printer)
- src/controller/print_manager.py:708-709 (_handle_material_change)
- src/controller/print_manager.py:790-823 (_wait_for_bed_raised)
**Impact:** Quiescent window never prevents printer polling as intended
**Evidence:** Logs show all three events at same timestamp (1759544828.0)

##### **Excessive SocketIO Logging** - websocket_ipc.py + app.py
**Root Cause:** SocketIO library logger enabled on BOTH client and server
- websocket_ipc.py:92: Client has `logger=True` (hardcoded)
- app.py:70-71: Server has `logger=_debug_socket` (conditional on MMU_SOCKET_DEBUG)
- Each emit/receive logs twice (once from client, once from server)
**Files:**
- src/controller/websocket_ipc.py:92 (client logger=True)
- web-app/app.py:70-71 (server logger config)
**Impact:** 67% of log lines are SocketIO emissions
**Evidence:** Every status update shows:
  ```
  Emitting event "status_update" [/]
  [INFO] Emitting event "status_update" [/]
  ```

#### 🟢 Low Priority

##### **Pump Config Reload Logging** - mmu_control.py
**Observation:** Config logged once at first material change, silent thereafter
- Could be single load (cached) or reloaded silently
**Files:** src/controller/mmu_control.py (change_material function)
**Impact:** None - pump operations consistent across all changes
**Evidence:** Step counts vary <1.5%, suggesting config is stable

