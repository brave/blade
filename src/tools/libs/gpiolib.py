# Note:   Control GPIO output
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   20/02/2023

import gpiod

# Define GPIO chip (typically /dev/gpiochip4 for Raspberry Pi 5)
GPIO_CHIP = "/dev/gpiochip4"
CONSUMER = "BLaDE"


# initialize pin to output and off
def init(pin, default_state=1):
    with gpiod.Chip(GPIO_CHIP) as chip:
        line = chip.get_line(pin)
        if not line.is_requested():
            line.request(consumer=CONSUMER, type=gpiod.LINE_REQ_DIR_OUT, default_vals=[default_state])
        line.set_value(default_state)
        line.release()


# write a state (0 or 1) to a device
def write(pin, state):
    with gpiod.Chip(GPIO_CHIP) as chip:
        line = chip.get_line(pin)
        if not line.is_requested():
            line.request(consumer=CONSUMER, type=gpiod.LINE_REQ_DIR_OUT, default_vals=[state])
        line.set_value(state)
        line.release()

# read the state of a device (returns 0 or 1)
def read(pin):
    with gpiod.Chip(GPIO_CHIP) as chip:
        line = chip.get_line(pin)
        if not line.is_requested():
            line.request(consumer=CONSUMER, type=gpiod.LINE_REQ_DIR_AS_IS, default_vals=[1])
        value = line.get_value()
        line.release()
        return value
