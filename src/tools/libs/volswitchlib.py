# Note:   Switch Monsoon voltage to a particular channel
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   01/03/2023

import json
import os

from libs import gpiolib

# get current file path
__location__ = os.path.dirname(os.path.realpath(__file__))


class VoltageSwitch:

    def __init__(self):
        self.config = self.__read_config()

    def __read_config(self):

        # read monsoon's configuration file
        filename = os.path.join(__location__, "../configs", "channels.json")
        with open(filename, encoding="utf-8") as f:
            return json.load(f)

    def init_state(self):
        self.switch_all_off()

    def switch_all_off(self):
        for _, details in self.config.items():
            pin = details["gpio_pin"]
            state = self.__state_to_int("off")
            gpiolib.write(pin, state)

    def switch_to(self, channel):
        pin = self.__get_gpio_pin(channel)
        self.switch_all_off()
        state = self.__state_to_int("on")
        gpiolib.write(pin, state)

    def switch_off(self, channel):
        pin = self.__get_gpio_pin(channel)
        state = self.__state_to_int("off")
        gpiolib.write(pin, state)

    def read_state(self, channel):
        pin = self.__get_gpio_pin(channel)
        state = gpiolib.read(pin)
        return self.__state_to_str(state)

    def is_all_channels_off(self):
        for channel in self.config.keys():
            if self.read_state(channel) == "on":
                return False
        return True

    ##################################################################
    # PRIVATE
    ##################################################################

    def __get_gpio_pin(self, channel):

        # get details
        details = self.config.get(channel)
        if details is None:
            raise Exception(
                f"Channel '{channel}' is not available in 'channels.json'")

        pin = details["gpio_pin"]
        return pin

    # converts int state to str (1: off and 0: on in this context)
    def __state_to_str(self, state):

        if state == 1:
            return "off"

        if state == 0:
            return "on"

        raise Exception(f"Error: Unknown state: '{state}'.")

    # converts str state to int (1: off and 0: on in this context)
    def __state_to_int(self, state_str):

        if state_str == "off":
            return 1

        if state_str == "on":
            return 0

        raise Exception(f"Error: Unknown state: '{state_str}'.")
