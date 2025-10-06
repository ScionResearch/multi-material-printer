"""
Solenoid Control - Air valve control for material drainage assist

Controls GPIO-connected air solenoid valve that directs air flow across the vat
to push resin toward the drain during material changes. The air stream helps
move viscous resin from one side of the vat to the drain location.

Key Functions:
- init_solenoid(): Initialize GPIO pin for solenoid control
- activate_solenoid(): Open air valve (HIGH signal) - starts air flow
- deactivate_solenoid(): Close air valve (LOW signal) - stops air flow
- get_state(): Read current solenoid state

Hardware:
- GPIO Pin 22 (BCM mode)
- Active HIGH (valve opens when GPIO HIGH, allowing air to blow across vat)
- Used during drain operations to push resin toward drain location

Usage:
    from solenoid_control import init_solenoid, activate_solenoid, deactivate_solenoid

    init_solenoid()
    activate_solenoid()  # Start air flow to push resin toward drain
    # ... run drain pump ...
    deactivate_solenoid()  # Stop air flow after drain completes
"""

import RPi.GPIO as GPIO
import logging
import time

# Set up logger
logger = logging.getLogger(__name__)

# Solenoid GPIO configuration
SOLENOID_PIN = 22  # BCM pin 22
_initialized = False
_current_state = False  # Track current state (False = closed, True = open)

def init_solenoid():
    """
    Initialize GPIO pin for solenoid control.
    Sets pin 22 to output mode and ensures valve is closed.

    Returns:
        bool: True if successful
    """
    global _initialized

    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(SOLENOID_PIN, GPIO.OUT)
        GPIO.output(SOLENOID_PIN, GPIO.LOW)  # Start with valve closed

        _initialized = True
        logger.info(f"[SOLENOID] ✓ Initialized on GPIO pin {SOLENOID_PIN} (valve closed)")
        return True

    except Exception as e:
        logger.error(f"[SOLENOID] ✗ Failed to initialize: {e}")
        _initialized = False
        return False

def activate_solenoid():
    """
    Activate solenoid valve (open air valve).
    Sets GPIO 22 to HIGH.

    Returns:
        bool: True if successful
    """
    global _current_state

    try:
        if not _initialized:
            logger.warning("[SOLENOID] Not initialized, attempting to initialize...")
            if not init_solenoid():
                return False

        GPIO.output(SOLENOID_PIN, GPIO.HIGH)
        _current_state = True
        logger.info("[SOLENOID] ✓ Air valve OPENED - blowing air across vat to push resin toward drain")
        return True

    except Exception as e:
        logger.error(f"[SOLENOID] ✗ Failed to activate: {e}")
        return False

def deactivate_solenoid():
    """
    Deactivate solenoid valve (close air valve).
    Sets GPIO 22 to LOW.

    Returns:
        bool: True if successful
    """
    global _current_state

    try:
        if not _initialized:
            logger.warning("[SOLENOID] Not initialized, attempting to initialize...")
            if not init_solenoid():
                return False

        GPIO.output(SOLENOID_PIN, GPIO.LOW)
        _current_state = False
        logger.info("[SOLENOID] ✓ Air valve CLOSED - air flow stopped")
        return True

    except Exception as e:
        logger.error(f"[SOLENOID] ✗ Failed to deactivate: {e}")
        return False

def get_state():
    """
    Get current solenoid state.

    Returns:
        bool: True if valve is open, False if closed
    """
    return _current_state

def cleanup():
    """
    Clean up GPIO resources and ensure valve is closed.
    Should be called on program exit.
    """
    global _initialized

    try:
        if _initialized:
            GPIO.output(SOLENOID_PIN, GPIO.LOW)  # Ensure valve closed
            GPIO.cleanup(SOLENOID_PIN)
            _initialized = False
            logger.info("[SOLENOID] ✓ GPIO cleanup complete (valve closed)")
            return True
    except Exception as e:
        logger.error(f"[SOLENOID] ✗ Cleanup failed: {e}")
        return False

def test_solenoid(duration=2):
    """
    Test solenoid operation (open for duration, then close).

    Args:
        duration (float): Duration to keep valve open in seconds

    Returns:
        bool: True if test successful
    """
    try:
        logger.info(f"[SOLENOID] Starting test - will open valve for {duration}s")

        if not init_solenoid():
            return False

        # Open valve
        if not activate_solenoid():
            return False

        # Wait
        time.sleep(duration)

        # Close valve
        if not deactivate_solenoid():
            return False

        logger.info("[SOLENOID] ✓ Test completed successfully")
        return True

    except Exception as e:
        logger.error(f"[SOLENOID] ✗ Test failed: {e}")
        return False

if __name__ == "__main__":
    """
    Command-line interface for solenoid testing.

    Usage:
        python3 solenoid_control.py          # Run 2-second test
        python3 solenoid_control.py 5        # Run 5-second test
    """
    import sys

    # Set up console logging
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

    duration = 2
    if len(sys.argv) > 1:
        try:
            duration = float(sys.argv[1])
        except ValueError:
            print("Usage: python3 solenoid_control.py [duration_seconds]")
            sys.exit(1)

    try:
        success = test_solenoid(duration)
        sys.exit(0 if success else 1)
    finally:
        cleanup()
