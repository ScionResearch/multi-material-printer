# Scion Multi-Material 3D Printer - Operating Manual

**Version:** 1.0
**Last Updated:** October 2025
**For Operators and Technicians**

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Safety Information](#safety-information)
3. [Getting Started](#getting-started)
4. [Daily Operations](#daily-operations)
5. [Multi-Material Printing](#multi-material-printing)
6. [Manual Controls](#manual-controls)
7. [Troubleshooting](#troubleshooting)
8. [Maintenance](#maintenance)
9. [Emergency Procedures](#emergency-procedures)

---

## System Overview

The Scion Multi-Material 3D Printer system automates resin material changes during 3D printing. It combines:

- **Anycubic Photon Mono X** resin printer
- **Raspberry Pi controller** running control software
- **Four stepper-driven pumps** (A, B, C, Drain)
- **Air solenoid valve** for drain assist
- **Web-based control interface**

### Key Features

- ✅ Automated material changes based on layer number
- ✅ Real-time printer status monitoring
- ✅ Manual pump and printer controls
- ✅ Recipe-based material scheduling
- ✅ Air-assist drainage system
- ✅ Live status updates via web interface

---

## Safety Information

### ⚠️ IMPORTANT WARNINGS

**CHEMICAL HAZARDS:**
- UV resin is a skin and eye irritant
- Always wear nitrile gloves when handling resin
- Wear safety glasses when working near the printer
- Work in well-ventilated area
- Follow resin manufacturer's safety data sheet (SDS)

**ELECTRICAL HAZARDS:**
- Do not touch electrical connections while powered
- Keep liquids away from electronics
- Ensure proper grounding of all equipment

**MECHANICAL HAZARDS:**
- Keep hands clear of moving parts
- Do not reach into printer during operation
- Wait for bed to stop moving before opening printer

**UV LIGHT HAZARD:**
- Do not look directly at UV light source
- Ensure printer lid is closed during operation

### Emergency Stop Procedures

**Immediate Stop Required:**
1. Click **EMERGENCY STOP** button in web interface
2. If web interface unavailable: Power off Raspberry Pi at wall outlet
3. If resin spill: Turn off printer, contain spill with absorbent material

---

## Getting Started

### System Requirements

- **Network:** Printer and Raspberry Pi must be on same network
- **Access:** Computer/tablet with web browser
- **Network Addresses:**
  - Raspberry Pi: `10.10.36.109`
  - Printer: `192.168.4.2` (via Pi's WiFi)

### First-Time Setup

1. **Power On Sequence:**
   ```
   1. Turn on main power to printer
   2. Turn on Raspberry Pi
   3. Wait 2 minutes for services to start
   ```

2. **Access Web Interface:**
   - Open web browser
   - Navigate to: `http://10.10.36.109:5000`
   - Bookmark this page for easy access

3. **Verify System Status:**
   - Dashboard should show "Backend: Online" (green)
   - Printer status should appear (e.g., "Stop", "Print", "Pause")
   - All pump statuses should show "Idle"

### Dashboard Overview

The main dashboard displays:

**Printer Status Panel:**
- Current printer state (Stop/Print/Pause)
- Current layer number
- Print progress percentage
- Elapsed time

**Material Change Status:**
- Multi-material mode (Active/Inactive)
- Current layer
- Next scheduled material change
- Material change history

**Pump Status:**
- Individual pump states (A, B, C, D)
- Running/Idle indicators
- Last operation details

**System Health:**
- Backend connection status
- Service uptime
- Error notifications

---

## Daily Operations

### Pre-Operation Checklist

Before starting a print:

- [ ] Check resin levels in all material reservoirs
- [ ] Verify drain container has capacity
- [ ] Ensure printer vat is clean and FEP film intact
- [ ] Confirm all pump tubes properly connected
- [ ] Check air valve tubing secure
- [ ] Verify no error messages on dashboard

### Starting a Standard Print

**For single-material prints (no material changes):**

1. Prepare print file (.pwmb) on USB drive
2. Insert USB into printer
3. Use printer touchscreen to select file
4. Click **Start Print** on printer
5. Monitor via web dashboard (optional)

**System will automatically:**
- Monitor printer status
- Update dashboard in real-time
- Log print progress

### Monitoring Active Prints

**Via Web Dashboard:**
- Check layer progress
- View estimated completion time
- Monitor printer temperature
- Check for error messages

**Visual Inspection:**
- Every 30 minutes: Check resin levels
- Every hour: Verify print quality through window
- Monitor for unusual sounds or smells

### Stopping a Print

**Normal Stop:**
1. Click **Stop Print** button in Manual Controls page
2. Wait for printer to complete current layer
3. Printer will halt and display "Stop" status

**Emergency Stop:**
1. Click **EMERGENCY STOP** in Manual Controls
2. All pumps immediately halt
3. Printer control returns to printer touchscreen
4. Manually drain vat if needed

---

## Multi-Material Printing

### Overview

Multi-material mode allows automatic resin changes at specific layer numbers during a print.

### Recipe Creation

1. **Navigate to Recipe Builder:**
   - Click "Recipe" in top navigation
   - Current recipe displayed (if any)

2. **Add Material Changes:**

   **Format:** `MATERIAL,LAYER:MATERIAL,LAYER:...`

   **Example Recipe:**
   ```
   A,50:B,120:C,200
   ```
   Meaning:
   - Layer 1-49: Current vat material
   - Layer 50: Change to Material A
   - Layer 120: Change to Material B
   - Layer 200: Change to Material C

3. **Material Identifiers:**
   - `A` = Pump A (Material reservoir A)
   - `B` = Pump B (Material reservoir B)
   - `C` = Pump C (Material reservoir C)
   - `D` = Drain pump (do not use in recipes)

4. **Save Recipe:**
   - Enter recipe in text box
   - Click **Save Recipe**
   - Confirmation message appears

### Starting Multi-Material Print

1. **Prepare Recipe:**
   - Create and save recipe (see above)
   - Verify materials loaded in correct pumps

2. **Start Print Job:**
   - Load print file on printer via touchscreen
   - Start print on printer
   - **Wait for printer to begin** (layer 1 starts)

3. **Activate Multi-Material Mode:**
   - Go to Dashboard
   - Click **Begin MM** button
   - "Multi-Material Mode: Active" appears
   - System monitors layers for material changes

4. **Monitor Material Changes:**
   - Dashboard shows "Next change: Layer X"
   - When layer reached, automatic sequence begins
   - Progress shown in Material Change Status panel

### Material Change Sequence

**Automatic Process (do not interrupt):**

```
1. PAUSE (10s)
   └─ Printer pauses
   └─ Quiescent wait for firmware to process

2. BED RAISE (2s delay + 15s movement + 3s buffer)
   └─ Bed moves to raised position
   └─ Safety verification

3. DRAIN (variable time, ~10-15s)
   └─ Air valve opens (blows resin toward drain)
   └─ Drain pump removes old resin from vat
   └─ Air valve closes

4. FILL (variable time, ~9-12s)
   └─ New material pump fills vat
   └─ Controlled flow rate

5. SETTLE (5s)
   └─ Material stabilizes
   └─ Bubbles dissipate

6. RESUME
   └─ Printer continues printing
   └─ Layer monitoring resumes
```

**Total Duration:** ~55-60 seconds per material change

**What You'll See:**
- Printer pauses
- Air hiss sound (solenoid valve opening)
- Pump motor sounds (drain, then fill)
- Brief quiet period (settle)
- Printer resumes (UV light and bed movement)

### Stopping Multi-Material Mode

1. Click **Stop MM** button on Dashboard
2. System stops monitoring for material changes
3. Print continues without further material changes
4. Current layer completed normally

---

## Manual Controls

Access via **Manual Controls** page in navigation.

### Individual Pump Control

**Purpose:** Test pumps, prime lines, calibrate flow

1. **Select Pump:**
   - Choose A, B, C, or D from dropdown

2. **Select Direction:**
   - Forward: Pumps from reservoir into vat
   - Reverse: Pumps from vat to reservoir (cleaning)

3. **Set Duration:**
   - Enter time in seconds (1-300)
   - Start with 5s for testing

4. **Run Pump:**
   - Click **Run Pump** button
   - Motor sound indicates operation
   - Status updates in Process Monitor

**Typical Uses:**
- **Prime pump line:** Forward, 10-15 seconds
- **Test pump operation:** Forward, 5 seconds
- **Clean line:** Reverse, 30 seconds

### Air Valve Control

**Purpose:** Test air valve, clear vat manually, dry vat

**Controls:**
- **Activate Air Flow:** Opens valve, air blows across vat
- **Deactivate Air Flow:** Closes valve, air stops
- **Test (2s pulse):** Quick test cycle

**Safety:** Do not leave air flowing continuously for more than 30 seconds

**Typical Uses:**
- **Test valve:** Click "Test" button
- **Manual drain assist:** Activate before running drain pump manually
- **Dry vat after cleaning:** Activate for 10-15 seconds

### Printer Controls

**Available Commands:**
- **Pause Print:** Pauses current print job
- **Resume Print:** Resumes paused print
- **Stop Print:** Ends print job
- **Check Status:** Queries printer for current status

**Note:** These commands send instructions to printer; printer may take 1-2 seconds to respond.

### Material Change Test Sequence

**Purpose:** Test full material change without active print

1. Navigate to Manual Controls
2. Set timing parameters:
   - Drain Time: 30s (default)
   - Fill Material: Select A, B, or C
   - Fill Time: 25s (default)
   - Settle Time: 5s (default)

3. Click **Run Full Sequence**
4. Monitor Process Monitor log
5. Sequence completes in ~60 seconds

**Use for:**
- System testing
- Training operators
- Verifying material change timing
- Troubleshooting pump issues

---

## Troubleshooting

### Common Issues

#### Dashboard Shows "Backend: Offline"

**Symptoms:**
- Red "Offline" indicator
- No status updates
- Buttons disabled

**Solutions:**
1. Refresh browser page (Ctrl+Shift+R)
2. Check Raspberry Pi is powered on
3. Verify network connection to Pi
4. SSH into Pi and restart services:
   ```bash
   ssh pidlp@10.10.36.109
   cd /home/pidlp/pidlp/multi-material-printer
   ./stop_services.sh
   ./start_services.sh
   ```

#### Printer Status Shows "Disconnected"

**Symptoms:**
- Printer status: "Disconnected"
- Cannot control printer from web interface

**Solutions:**
1. Check printer is powered on
2. Verify printer WiFi network active (SSID: "PHOTON-WIFI")
3. Check Pi connected to printer network
4. Restart printer:
   - Power off printer
   - Wait 30 seconds
   - Power on printer
   - Wait 2 minutes for network to establish

#### Material Change Doesn't Trigger

**Symptoms:**
- Layer number reached but no material change
- "Next change: Layer X" but printer keeps printing

**Solutions:**
1. Verify Multi-Material Mode is **Active** (Dashboard shows "Active")
2. Check recipe saved correctly:
   - Go to Recipe page
   - Verify recipe format
   - Re-save if needed
3. Restart Multi-Material Mode:
   - Click **Stop MM**
   - Click **Begin MM**

#### Pump Not Running

**Symptoms:**
- No motor sound when command sent
- Process log shows "failed"
- Pump status stuck on "Running"

**Solutions:**
1. Check pump power connections
2. Verify I2C motor controller connections
3. Test individual pump from Manual Controls
4. Check logs for I2C errors:
   - SSH into Pi
   - `tail -f print_manager.log`
   - Look for "I2C" or "MotorKit" errors
5. Run I2C detection test:
   ```bash
   ssh pidlp@10.10.36.109
   i2cdetect -y 1
   ```
   Should show devices at 0x60 and 0x61

#### Air Valve Not Working

**Symptoms:**
- No air sound when activated
- Status shows "Error"

**Solutions:**
1. Test valve from Manual Controls:
   - Click "Test (2s pulse)"
   - Listen for air hiss
2. Check GPIO connections
3. Verify solenoid power supply
4. Test GPIO directly:
   ```bash
   ssh pidlp@10.10.36.109
   cd /home/pidlp/pidlp/multi-material-printer/src/controller
   python3 solenoid_control.py 3
   ```

#### Print Fails After Material Change

**Symptoms:**
- Print quality degrades after material change
- Layer adhesion issues
- Print detaches from build plate

**Possible Causes:**
1. **Insufficient settling time:**
   - Increase settle_time in config to 10-15s
2. **Air bubbles in resin:**
   - Increase settle_time to allow bubbles to dissipate
3. **Incomplete material change:**
   - Increase drain volume in config
   - Increase fill volume to ensure vat full
4. **Material incompatibility:**
   - Verify materials can be mixed/layered
   - Check manufacturer recommendations

---

## Maintenance

### Daily Maintenance

**End of Each Print Session:**

1. **Clean Printer Vat:**
   - Remove build plate
   - Strain resin back into bottle
   - Wipe vat with isopropyl alcohol
   - Check FEP film for damage

2. **Check Pump Tubing:**
   - Inspect for kinks or damage
   - Verify connections tight
   - Wipe exterior of tubes clean

3. **Empty Drain Container:**
   - Dispose of waste resin properly
   - Clean container with IPA
   - Replace in position

4. **Wipe Down Equipment:**
   - Clean any resin drips immediately
   - Wipe printer exterior
   - Clean work surface

### Weekly Maintenance

**Once per week or every 40 hours of operation:**

1. **Pump Line Flush:**
   - For each material pump (A, B, C):
     ```
     1. Empty reservoir
     2. Fill with isopropyl alcohol (IPA)
     3. Run pump forward 30s
     4. Let IPA sit in line 5 minutes
     5. Run pump forward 30s
     6. Empty IPA from vat
     7. Refill reservoir with resin
     8. Prime line (forward 10s)
     ```

2. **Drain Pump Clean:**
   - Run drain pump with IPA for 60s
   - Flush drain container
   - Ensure drain line clear

3. **Air Valve Test:**
   - Run valve test 5 times
   - Listen for consistent operation
   - Check air tubing connections

4. **System Check:**
   - Review error logs (if any)
   - Test all pumps individually
   - Test full material change sequence
   - Verify printer communication

### Monthly Maintenance

**Once per month:**

1. **Calibrate Pumps:**
   - Measure actual pump output:
     ```
     1. Place graduated cylinder under pump output
     2. Run pump forward for 60s
     3. Measure volume dispensed
     4. Compare to expected (flow_rate × 60s)
     5. Record results
     ```
   - If deviation >10%, contact technical support

2. **Check Electrical Connections:**
   - Power off system
   - Inspect all wire connections
   - Tighten any loose terminals
   - Check for wire damage

3. **Clean Air Filter (if equipped):**
   - Remove air filter from solenoid line
   - Rinse with compressed air
   - Replace if damaged

4. **Update Software:**
   - Check for updates from Scion
   - Follow update procedure in Programming Manual
   - Test system after update

### Maintenance Log

Keep a maintenance log recording:
- Date and time
- Maintenance performed
- Issues found
- Parts replaced
- Operator initials

---

## Emergency Procedures

### Resin Spill

1. **Immediate Actions:**
   - Click **EMERGENCY STOP** if printer operating
   - Do not touch resin with bare skin
   - Evacuate non-essential personnel

2. **Containment:**
   - Don nitrile gloves and safety glasses
   - Use absorbent pads to contain spill
   - Do not wash resin down drain

3. **Cleanup:**
   - Collect contaminated materials in waste bag
   - Wipe area with isopropyl alcohol
   - Dispose of waste per local regulations

4. **Restart:**
   - Verify area clean and dry
   - Check equipment for damage
   - Restart system using normal procedures

### Fire

1. **Evacuate immediately**
2. **Activate building fire alarm**
3. **Call emergency services**
4. **Do not attempt to fight electrical fires with water**
5. **Use CO2 or dry chemical extinguisher if trained and safe to do so**

### Electrical Shock

1. **Do not touch victim if still in contact with electricity**
2. **Shut off power at breaker**
3. **Call emergency services**
4. **Administer first aid if trained**
5. **Report incident to supervisor**

### Chemical Exposure

**Skin Contact:**
1. Remove contaminated clothing
2. Wash skin with soap and water for 15 minutes
3. Seek medical attention if irritation persists

**Eye Contact:**
1. Flush eyes with water for 15 minutes
2. Remove contact lenses if present
3. Seek immediate medical attention

**Inhalation:**
1. Move to fresh air immediately
2. Seek medical attention if symptoms persist
3. Provide SDS to medical personnel

### System Malfunction

**If system behaves unexpectedly:**

1. **Stop Operation:**
   - Click **EMERGENCY STOP**
   - Do not attempt to continue print

2. **Document Issue:**
   - Note symptoms
   - Screenshot error messages
   - Record what actions preceded malfunction

3. **Contact Support:**
   - Email: support@scionresearch.com
   - Provide documentation from step 2
   - Do not attempt repairs without authorization

---

## Appendix A: Technical Specifications

**Printer:**
- Model: Anycubic Photon Mono X
- Build Volume: 192 × 120 × 245 mm
- Layer Height: 0.01-0.15 mm
- Light Source: UV LED (405 nm)

**Controller:**
- Model: Raspberry Pi 4B
- RAM: 4GB
- Storage: 32GB microSD
- Network: WiFi + Ethernet

**Pumps:**
- Type: Stepper motor peristaltic
- Flow Rate: ~5 mL/s (configurable)
- Controllers: Adafruit MotorKit (I2C)
- Addresses: 0x60, 0x61

**Air Valve:**
- Type: Solenoid, normally closed
- Control: GPIO pin 22 (BCM)
- Operating Voltage: 12V DC

**Network:**
- Pi Address: 10.10.36.109
- Printer Address: 192.168.4.2
- Web Interface Port: 5000

---

## Appendix B: Material Compatibility

Consult resin manufacturer for material mixing compatibility. General guidelines:

**Compatible (typically safe to layer):**
- Same brand, different colors
- Same resin type (e.g., standard → standard)

**Check Before Use:**
- Different brands, same type
- Similar properties (e.g., standard → tough)

**Incompatible (do not mix):**
- Flexible with rigid resins
- Water-washable with IPA-washable
- Significantly different cure times

**Best Practice:**
- Always test material combination on small print first
- Clean vat thoroughly between incompatible materials
- Document successful material combinations

---

## Appendix C: Quick Reference

### Common Commands

**Start Multi-Material Print:**
1. Create recipe → Save
2. Start print on printer
3. Click "Begin MM" on Dashboard

**Manual Pump Test:**
1. Manual Controls page
2. Select pump, direction, duration
3. Click "Run Pump"

**Emergency Stop:**
1. Manual Controls page
2. Click "EMERGENCY STOP" button

### Status Indicators

| Indicator | Meaning | Action |
|-----------|---------|--------|
| Backend: Online (Green) | System operational | Normal operation |
| Backend: Offline (Red) | Connection lost | Refresh page, restart services |
| Printer: Print | Printer actively printing | Monitor normally |
| Printer: Pause | Printer paused | Resume or stop as needed |
| Printer: Stop | Printer idle | Safe to start new print |
| Printer: Disconnected | Cannot reach printer | Check printer power/network |
| Pump: Running | Pump operating | Wait for completion |
| Pump: Idle | Pump ready | Safe to run commands |

### Contact Information

**Technical Support:**
- Email: support@scionresearch.com
- Phone: [Insert phone number]
- Hours: Monday-Friday, 8am-5pm NZST

**Emergency (after hours):**
- Contact: [Insert emergency contact]
- For safety emergencies only

---

**Document End**

*For programming and technical details, see [PROGRAMMING_MANUAL.md](PROGRAMMING_MANUAL.md)*
