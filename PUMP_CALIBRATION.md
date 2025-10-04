# Pump Calibration Guide

A simple guide for calibrating the multi-material printer pumps to ensure accurate material dispensing.

---

## Why Calibrate?

Calibration measures how much resin each pump dispenses per second. This ensures:
- Accurate material changes during prints
- Consistent vat filling and draining
- Predictable material usage

**When to calibrate:**
- ✅ Initial setup (before first multi-material print)
- ✅ After replacing pump tubing or motors
- ✅ Every 6 months (routine maintenance)
- ✅ If material flow seems inconsistent

---

## What You'll Need

- Graduated cylinder or measuring cup (100-200ml)
- Resin (same type you'll be printing with)
- Pen and paper for notes
- 30-45 minutes per pump

---

## Calibration Steps

### 1. Prepare the Pumps

**Fill reservoirs:**
- Make sure each material reservoir is at least half full
- Use the actual resin you'll be printing with

**Prime the pumps (remove air bubbles):**
1. Open the web interface: `http://10.10.36.109:5000`
2. Go to **Manual Controls** page
3. For each pump (A, B, C, D):
   - Select the pump
   - Choose "Forward" direction
   - Set duration to 15 seconds
   - Click "Run Pump"
   - Watch for steady flow (no sputtering)

### 2. Run Calibration Tests

**For each pump you want to calibrate:**

1. **Start calibration:**
   - Go to **Configuration** → **Pump Settings**
   - Find the pump card (e.g., "Pump A")
   - Click **"Calibrate"** button
   - Confirm when prompted

2. **Place graduated cylinder under drain:**
   - Position it to catch all dispensed resin
   - Make sure it's empty and dry

3. **Watch the automatic sequence:**
   - The pump will run 3 times automatically:
     - 5 seconds → 2 second pause
     - 10 seconds → 2 second pause
     - 15 seconds → done
   - Total time: ~35 seconds

4. **Measure and record results:**

   After each test run, write down the volume:

   ```
   Pump A Calibration:
   - 5 second test:  _____ ml
   - 10 second test: _____ ml
   - 15 second test: _____ ml
   ```

### 3. Calculate Flow Rate

**For each test, calculate the flow rate:**

```
Flow Rate = Volume ÷ Time
```

**Example:**
- 5s test dispensed 26ml → 26 ÷ 5 = **5.2 ml/s**
- 10s test dispensed 51ml → 51 ÷ 10 = **5.1 ml/s**
- 15s test dispensed 75ml → 75 ÷ 15 = **5.0 ml/s**

**Average the three results:**
```
(5.2 + 5.1 + 5.0) ÷ 3 = 5.1 ml/s
```

✅ **Good:** Results within 10% of each other
⚠️ **Problem:** Results vary by more than 10% → Check for air bubbles and re-prime

### 4. Update Configuration

**Option A: Via Web Interface** (if available)
1. Configuration → Pump Settings
2. Find the pump you calibrated
3. Update "Flow Rate (ml/s)" field with your calculated value
4. Click "Save Pump Configuration"

**Option B: Via File Edit** (SSH required)

1. Connect to Raspberry Pi:
   ```bash
   ssh pidlp@10.10.36.109
   ```
   Password: `pidlp`

2. Open configuration file:
   ```bash
   cd /home/pidlp/pidlp/multi-material-printer
   nano config/pump_profiles.json
   ```

3. Find your pump and update the flow rate:
   ```json
   "pump_a": {
       "flow_rate_ml_per_second": 5.1,  ← Change this number
   ```

4. Save: Press `Ctrl+O`, then `Enter`, then `Ctrl+X`

### 5. Apply Changes

**Restart the system to use new calibration:**

1. Stop and restart services:
   ```bash
   cd /home/pidlp/pidlp/multi-material-printer
   ./stop_services.sh
   ./start_services.sh
   ```

2. Refresh your web browser:
   - Press `Ctrl+Shift+R` (force refresh)
   - Check that new flow rate appears in Configuration page

3. **Test it:** Run a quick 5-second test to verify accuracy

---

## Expected Values

| Pump | Normal Range | Typical Value |
|------|-------------|---------------|
| Pump A | 3-7 ml/s | 5 ml/s |
| Pump B | 3-7 ml/s | 5 ml/s |
| Pump C | 3-7 ml/s | 5 ml/s |
| Drain Pump D | 4-8 ml/s | 6 ml/s |

**Note:** Values outside this range might indicate:
- Clogged tubing
- Air in the lines
- Motor/hardware issues

---

## Troubleshooting

### Flow is Inconsistent (varies >10% between tests)

**Possible causes:**
1. **Air bubbles in tubing**
   - Solution: Prime pump for 30 seconds until flow is steady

2. **Low reservoir level**
   - Solution: Refill to at least 50%

3. **Clogged tubing**
   - Solution: Check for cured resin, clean or replace tubing

4. **Pump motor slipping**
   - Solution: Check motor coupling, contact technician

### Pump Doesn't Run During Calibration

1. Check that services are running:
   - Look for green "Backend Online" indicator in web UI
   - If red, restart services (see Step 5 above)

2. Check for error messages in the web interface

3. If still not working, contact support

### New Values Don't Apply

**Checklist:**
- [ ] Did you save the configuration file?
- [ ] Did you restart the services?
- [ ] Did you force-refresh the browser (Ctrl+Shift+R)?

---

## Quick Reference

### Calibration Checklist

**Before starting:**
- [ ] Reservoirs filled >50%
- [ ] Pumps primed (no air bubbles)
- [ ] Graduated cylinder ready
- [ ] Web interface open

**During calibration:**
- [ ] Run calibration (3 tests automatic)
- [ ] Measure volume after each test
- [ ] Calculate flow rate for each test
- [ ] Average the three results

**After calibration:**
- [ ] Update config file with new flow rate
- [ ] Restart services
- [ ] Force-refresh browser
- [ ] Verify new values loaded
- [ ] Run test to confirm

### Useful Commands

```bash
# Connect to Raspberry Pi
ssh pidlp@10.10.36.109

# Navigate to project folder
cd /home/pidlp/pidlp/multi-material-printer

# Edit pump config
nano config/pump_profiles.json

# Restart services
./stop_services.sh
./start_services.sh

# Check if services are running
pgrep -f "app.py|print_manager.py"
```

### Web Interface Locations

- **Configuration:** `http://10.10.36.109:5000` → Configuration tab
- **Manual Controls:** `http://10.10.36.109:5000` → Manual tab
- **Calibrate Button:** Configuration → Pump Settings → Click "Calibrate" on pump card

---

## Tips for Best Results

1. **Use the 15-second test** as your most accurate measurement
2. **Calibrate at room temperature** (20-25°C) for consistent results
3. **Write down all measurements** - you'll need them if you re-calibrate
4. **Do one pump at a time** - don't rush
5. **Empty the graduated cylinder** between tests

---

## Need Help?

**Check logs for errors:**
```bash
tail -f /home/pidlp/pidlp/multi-material-printer/print_manager.log
```

**Configuration file location:**
```
/home/pidlp/pidlp/multi-material-printer/config/pump_profiles.json
```

**For technical support, provide:**
- Which pump you're calibrating
- Your measured values (all 3 tests)
- Any error messages from the web interface
- Screenshots if possible
