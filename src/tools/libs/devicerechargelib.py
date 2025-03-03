# Note:   Functions that are used to check the battery level of a device and charge it if needed.
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   29/11/2024

import time

from libs import usblib
from libs.automation import adb_commands
from libs import constants
from libs import logger as blade_logger


def auto_recharge_if_needed(device, current_connection="wifi", min_threshold_ratio=0.30, max_threshold_ratio=1.00):
    # checks the battery level of the device and charges it if it is below the threshold.
    # Returns True if charging was needed, False otherwise.

    battery_details = adb_commands.get_battery_details(device, connection=current_connection)
    current_battery_level_ratio = battery_details["level_ratio"]
    blade_logger.logger.info(f"Device battery level is at {current_battery_level_ratio:.2f}. (threshold range: {min_threshold_ratio:.2f}-{max_threshold_ratio:.2f})")

    if current_battery_level_ratio < min_threshold_ratio:

        blade_logger.logger.info(f"Device needs charging. Battery level is at {current_battery_level_ratio:.2f}.")

        # enable USB port if it is disabled
        usb_control = usblib.USBControl(device["usb"])
        if usb_control.get_state() == "disabled":
            blade_logger.logger.info("Enabling relevant USB port to allow device charging...")
            usb_control.set_state("enabled")
            time.sleep(constants.FIVE_SECONDS)
        
        # await...
        await_until_device_reaches_battery_level(device, max_threshold_ratio)

        # all done, re-disable the USB port to continue the experiment
        usb_control.set_state("disabled")
        time.sleep(constants.FIVE_SECONDS)

        return True
    
    return False


def await_until_device_reaches_battery_level(device, max_battery_level_ratio=1.00):
    # waits until the device is charged to the threshold level
    # connection should always be "usb" since we are charging the device

    while True:
        battery_details = adb_commands.get_battery_details(device, "usb")
        current_battery_level_ratio = battery_details["level_ratio"]
        if current_battery_level_ratio >= max_battery_level_ratio:
            blade_logger.logger.info(f"Device reached battery level {current_battery_level_ratio:.2f}. Continuing...")
            break

        blade_logger.logger.info(f"Device is charging while at battery level {current_battery_level_ratio:.2f}. Waiting until it reaches {max_battery_level_ratio:.2f}.")
        time.sleep(constants.SIXTY_SECONDS)
