"""
Photon MMU Pump Control - Low-level stepper motor control for material pumps

Direct hardware control for stepper motor-driven pumps via Adafruit motor controllers.
Interfaces with two MotorKit boards (I2C addresses 0x60, 0x61) to control four pumps:
- STEPPER_A/B: Material pumps A/B (kit.stepper1/2)
- STEPPER_C/D: Material pump C/Drain pump (kit2.stepper1/2)

Key Functions:
- run_stepper(): Primary pump control with timing
- initialize_motors(): Release motors to safe state
- read_sensor(): Material level detection via GPIO 18

Requires: I2C enabled, Adafruit MotorKit boards, proper power supply
"""

import RPi.GPIO as GPIO
from adafruit_motorkit import MotorKit
from adafruit_motor import stepper
import time
import logging

# Set up logger for pump operations
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

# Sensor setup

# value of other resistor
SERIESRESISTOR = 560

# PIN OF SENSOR
SENSORPIN = 18

def read_sensor():
    """
    Read analog sensor for material level detection.
    
    Returns:
        float: Sensor resistance in ohms (higher = lower level)
    """
    GPIO.setmode(GPIO.BCM)
    # set up the GPIO pin as an analog input
    GPIO.setup(SENSORPIN, GPIO.IN)

    # read the analog value from the sensor
    reading = GPIO.input(SENSORPIN)

    # calculate the resistance of the sensor
    reading = (1023 / reading) - 1
    reading = SERIESRESISTOR / reading

    return reading
    

# Initialize the motor kit with I2C verification
try:
    logger.info("[I2C] Initializing MotorKit at default address 0x60...")
    kit = MotorKit()
    logger.info("[I2C] ✓ MotorKit 0x60 initialized successfully")

    # Verify I2C communication by reading PCA9685 registers
    try:
        freq = kit._pca.frequency
        prescale = kit._pca.prescale_reg
        logger.info(f"[I2C] Controller 0x60 - PWM freq: {freq}Hz, prescale: {prescale}")
    except Exception as e:
        logger.warning(f"[I2C] Could not read controller 0x60 registers: {e}")

except Exception as e:
    logger.error(f"[I2C] ✗ Failed to initialize MotorKit at 0x60: {e}")
    raise

try:
    logger.info("[I2C] Initializing MotorKit at address 0x61...")
    kit2 = MotorKit(address=0x61)
    logger.info("[I2C] ✓ MotorKit 0x61 initialized successfully")

    # Verify I2C communication by reading PCA9685 registers
    try:
        freq = kit2._pca.frequency
        prescale = kit2._pca.prescale_reg
        logger.info(f"[I2C] Controller 0x61 - PWM freq: {freq}Hz, prescale: {prescale}")
    except Exception as e:
        logger.warning(f"[I2C] Could not read controller 0x61 registers: {e}")

except Exception as e:
    logger.error(f"[I2C] ✗ Failed to initialize MotorKit at 0x61: {e}")
    raise

# Define the four possible stepper motors
STEPPER_A = kit.stepper1
STEPPER_B = kit.stepper2
STEPPER_C = kit2.stepper1
STEPPER_D = kit2.stepper2

logger.info("[I2C] All stepper motor objects created (A, B, C, D)")

def initialize_motors():
    """
    Release all stepper motors to safe state.
    Prevents overheating and reduces power consumption.
    """
    STEPPER_A.release()
    STEPPER_B.release()
    STEPPER_C.release()
    STEPPER_D.release()

def run_stepper(pumpmat, direction, usr_time):
    """
    Control stepper motor for pump operations.

    Args:
        pumpmat (str): Pump identifier ('A', 'B', 'C', 'D')
        direction (str): Direction ('F' forward, 'R' reverse)
        usr_time (int): Duration in seconds

    Raises:
        ValueError: Invalid pump identifier
    """
    pump_name_map = {'A': 'Pump A', 'B': 'Pump B', 'C': 'Pump C', 'D': 'Drain Pump'}
    pump_display_name = pump_name_map.get(pumpmat, f'Pump {pumpmat}')
    direction_display = 'FORWARD' if direction == 'F' else 'REVERSE'

    logger.info(f"[PUMP] Starting {pump_display_name} - Direction: {direction_display}, Duration: {usr_time}s")

    # Choose the correct stepper motor based on the input variable
    try:
        if pumpmat == 'A':
            stpr = STEPPER_A
            controller_addr = "0x60"
            stepper_num = 1
            STEPPER_B.release()
            STEPPER_C.release()
            STEPPER_D.release()
        elif pumpmat == 'B':
            stpr = STEPPER_B
            controller_addr = "0x60"
            stepper_num = 2
            STEPPER_A.release()
            STEPPER_C.release()
            STEPPER_D.release()
        elif pumpmat == 'C':
            stpr = STEPPER_C
            controller_addr = "0x61"
            stepper_num = 1
            STEPPER_A.release()
            STEPPER_B.release()
            STEPPER_D.release()
        elif pumpmat == 'D':
            stpr = STEPPER_D
            controller_addr = "0x61"
            stepper_num = 2
            STEPPER_A.release()
            STEPPER_B.release()
            STEPPER_C.release()
        else:
            logger.error(f"[PUMP] ✗ Invalid pump identifier: {pumpmat}")
            raise ValueError("Invalid stepper number")

        logger.info(f"[I2C] {pump_display_name} mapped to controller {controller_addr}, stepper{stepper_num}")
        logger.info(f"[I2C] Released all other motors to prevent conflicts")

    except Exception as e:
        logger.error(f"[I2C] ✗ Failed to select motor: {e}")
        raise

    # Set the speed and number of steps for the stepper motor
    try:
        stpr.steps = 200
        stpr.setSpeed = 0.005
        logger.info(f"[PUMP] Motor configuration: 200 steps, 5ms step delay")
    except Exception as e:
        logger.error(f"[I2C] ✗ Failed to configure motor: {e}")
        raise

    # Run the stepper motor until the desired level is reached
    try:
        t_start = time.time()
        t_end = t_start + usr_time
        step_count = 0

        logger.info(f"[PUMP] Beginning motor movement...")

        while time.time() < t_end:
            if direction == 'F':
                stpr.onestep(direction=stepper.FORWARD)
                time.sleep(0.005)
            else:
                stpr.onestep(direction=stepper.BACKWARD)
                time.sleep(0.005)
            step_count += 1

        actual_duration = time.time() - t_start
        steps_per_second = step_count / actual_duration if actual_duration > 0 else 0

        logger.info(f"[PUMP] ✓ {pump_display_name} completed successfully")
        logger.info(f"[PUMP] Statistics: {step_count} steps in {actual_duration:.2f}s ({steps_per_second:.1f} steps/sec)")

    except Exception as e:
        logger.error(f"[I2C] ✗ Motor movement failed: {e}")
        raise
    finally:
        try:
            stpr.release()
            logger.info(f"[I2C] Motor released to safe state")
        except Exception as e:
            logger.error(f"[I2C] ✗ Failed to release motor: {e}")

def run_stepperrev(pumpmat, reqlevel):
    """Deprecated legacy reverse operation. Prefer run_stepper().

    Fixed undefined variables (STEPPER_1/2) to use STEPPER_A/B for safety,
    but function remains for backward compatibility and may be removed.
    """
    if pumpmat == 'A':
        stpr = STEPPER_A
    elif pumpmat == 'B':
        stpr = STEPPER_B
    else:
        raise ValueError("Invalid stepper number (expected 'A' or 'B')")

    stpr.release()
    stpr.steps = 200
    # Legacy speed attribute; using small delay loop below
    t_end = time.time() + 5  # shortened from 180s to 5s for safety if accidentally invoked
    while time.time() < t_end:
        stpr.onestep(direction=stepper.BACKWARD)
        time.sleep(0.005)
    stpr.release()

#run_stepper('D', 'F', 30000)
#run_stepperrev('B', 100)
 



