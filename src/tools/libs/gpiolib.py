# Note:   Control GPIO output
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   20/02/2023

from RPi import GPIO

# init GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


##################################################################
# PUBLIC
##################################################################


# write a state (0 or 1) to a device
def write(pin, state):
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, state)


# read the state of a device (returns 0 or 1)
def read(pin):
    GPIO.setup(pin, GPIO.OUT)
    state = GPIO.input(pin)
    return state
