# Multi-Material Printer Controller - Critical Issues TODO

*Created: September 25, 2025*


## 🚨 CRITICAL BUGS - IMMEDIATE ACTION REQUIRED

### Pause/Resume Sequence Logic (HIGH PRIORITY)
- [ ] **Fix bed positioning during material changes**
  - Issue: Bed remains down during pump operations, should rise first
  - Current: Pause → Run pumps → Bed rises → Wait → Continue
  - Required: Pause → Bed rises → Wait → Run drain pump → Run material pump → Continue
  - Location: Likely in `print_manager.py` material change logic

### Command Recognition Errors (HIGH PRIORITY)
- [ ] **Fix "goresume" command error**
  - Issue: Repeated "ERROR: unrecognized command: goresume" messages
  - Impact: May be causing print manager to exit with error code 15
  - Investigation needed: Check command syntax and printer firmware compatibility
  - Location: `printer_comms.py` command handling

### GUI Issues (MEDIUM PRIORITY)
- [ ] **Fix stop printer popup display**
  - Issue: Stop printer popup shows no content/message
  - Location: GUI stop printer button handler
  - Test: Verify popup displays proper confirmation dialog

### Print Manager Exit Error (MEDIUM PRIORITY)
- [ ] **Investigate print manager error exit code 15**
  - Issue: Print manager exits with error instead of clean shutdown
  - May be related to "goresume" command errors
  - Location: `print_manager.py` exit handling

## 🔍 INVESTIGATION TASKS

### Error Analysis
- [ ] **Analyze print manager logs for error patterns**
  - Review complete log output for error sequence
  - Identify root cause of exit code 15
  - Check for any unhandled exceptions

### Command Protocol Review
- [ ] **Verify printer communication protocol**
  - Check if "goresume" vs "resume" command syntax
  - Review printer firmware documentation
  - Test alternate resume commands

## 🧪 TESTING REQUIREMENTS

### Workflow Testing
- [ ] **Test complete print workflow end-to-end**
  1. Connect to printer status
  2. Get files list
  3. Start MMU controller
  4. Begin print with material changes
  5. Verify proper pause/resume sequence
  6. Test stop functionality

### Material Change Testing
- [ ] **Validate material change sequence**
  - Monitor bed position during material changes
  - Verify pump operation timing
  - Confirm proper resume after material change

---

## 📋 COMPLETION CRITERIA

- [ ] Material changes execute with proper bed positioning
- [ ] No "unrecognized command" errors in logs
- [ ] Stop printer popup displays correctly
- [ ] Print manager exits cleanly (exit code 0)
- [ ] Complete print workflow functions without errors

## 🔧 TECHNICAL NOTES

**From NOTES.md Analysis:**
- Printer IP: 192.168.4.4
- Test file: "1.pwmb: 16mm base - Part 1.pwmb"
- Print manager script: `src/controller/print_manager.py`
- Recipe config: `config/recipe.txt`

**Error Pattern:**
```
ERROR: unrecognized command: goresume
goresume,OK
(repeated 3 times)
```

**Exit Status:**
```
=== PRINT MANAGER FINISHED ===
Exit code: 15
Print manager exited with error
```