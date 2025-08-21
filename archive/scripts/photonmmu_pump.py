import RPi.GPIO as GPIO
from adafruit_motorkit import MotorKit
from adafruit_motor import stepper
import time

# Sensor setup

# value of other resistor
SERIESRESISTOR = 560

# PIN OF SENSOR
SENSORPIN = 18

def read_sensor():
    GPIO.setmode(GPIO.BCM)
    # set up the GPIO pin as an analog input
    GPIO.setup(SENSORPIN, GPIO.IN)

    # read the analog value from the sensor
    reading = GPIO.input(SENSORPIN)

    # calculate the resistance of the sensor
    reading = (1023 / reading) - 1
    reading = SERIESRESISTOR / reading

    return reading
    
     
# Initialize the motor kit
kit = MotorKit()
kit2 = MotorKit(address=0x61)

# Define the four possible stepper motors
STEPPER_A = kit.stepper1
STEPPER_B = kit.stepper2
STEPPER_C = kit2.stepper1
STEPPER_D = kit2.stepper2

def initialize_motors():
    STEPPER_A.release()
    STEPPER_B.release()
    STEPPER_C.release()
    STEPPER_D.release()

def run_stepper(pumpmat, direction, usr_time):
    # Choose the correct stepper motor based on the input variable
    if pumpmat == 'A':
        stpr = STEPPER_A
        STEPPER_B.release()
        STEPPER_C.release()
        STEPPER_D.release()
    elif pumpmat == 'B':
        stpr = STEPPER_B
        STEPPER_A.release()
        STEPPER_C.release()
        STEPPER_D.release()
    elif pumpmat == 'C':
        stpr = STEPPER_C
        STEPPER_A.release()
        STEPPER_B.release()
        STEPPER_D.release()
    elif pumpmat == 'D':
        stpr = STEPPER_D
        STEPPER_A.release()
        STEPPER_B.release()
        STEPPER_C.release()
    else:
        raise ValueError("Invalid stepper number")
    # Release the stepper motor

    # Set the speed and number of steps for the stepper motor
    
    stpr.steps = 200
    stpr.setSpeed = 0.005
    #stpr.release()
    #time.sleep(20)
    # Run the stepper motor until the desired level is reached
    t_end = time.time()+usr_time
    while time.time() < t_end:
        if direction == 'F':
            
            stpr.onestep(direction=stepper.FORWARD)
            time.sleep(0.005)
        else:
            stpr.onestep(direction=stepper.BACKWARD)
            time.sleep(0.005)
    stpr.release()

def run_stepperrev(pumpmat, reqlevel):
     # Choose the correct stepper motor based on the input variable
    if pumpmat == 'A':
        stpr = STEPPER_1
    elif pumpmat == 'B':
        stpr = STEPPER_2
    #elif pumpmat == 'C':
       # stpr = STEPPER_3
    #elif pumpmat == 'W':
     #   stpr = STEPPER_4
    else:
        raise ValueError("Invalid stepper number")
    # Set the speed and number of steps for the stepper motor
    stpr.release()
    stpr.steps = 200
    stpr.speed = 0.001
    #time.sleep(20)
    t_end = time.time()+180
    
    # Run the stepper motor until the desired level is reached
    while time.time() < t_end:
    
        stpr.onestep(direction=stepper.BACKWARD)
        time.sleep(0.001)

    # Release the stepper motor
    stpr.release()

#run_stepper('D', 'F', 30000)
#run_stepperrev('B', 100)
 



