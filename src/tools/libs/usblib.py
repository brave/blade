# Note:   Control USB port power state, using:
#         * https://www.yepkit.com/product/300110/YKUSH3 (usb control)
#         * https://pypi.org/project/usbid/ (usb info)
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   20/02/2023

import time

import usb.core
import usb.util
from pykush import pykush

from libs import constants
from libs import logger as blade_logger


class USBControl:

    def __init__(self, usb_info):
        self.usb_info = usb_info

    ##################################################################
    # PUBLIC
    ##################################################################

    # check if a usb device is available
    def is_device_available(self):
        return self.usb_info["id"] in self.__get_all_available_ids()

    # wait until a usb device becomes available
    def wait_for_device_availability(self, timeout=60 * 5):
        blade_logger.logger.info("Waiting for device to become available...")

        start_time = time.perf_counter()
        while True:

            if self.is_device_available():
                blade_logger.logger.info("Device is now available.")
                return True

            if time.perf_counter() - start_time > timeout:
                blade_logger.logger.warning(
                    f"Warning: Device failed to become available after waiting for {timeout} seconds."
                )
                return False

            time.sleep(constants.USB_LIBRARY_CHECK_FOR_DEVICE_AVAILABILITY_FREQUENCY)

    # switch the state ('enabled' or 'disabled') of a usb port
    def set_state(self, state_str):

        # init ykush lib
        yk = pykush.YKUSH(self.usb_info["ykush_serial"])

        state = self.__str_to_state(state_str)
        yk.set_port_state(self.usb_info.get("ykush_port"), state)

    # read the state of a usb port (returns 'enabled' or 'disabled')
    def get_state(self, error_patience=constants.USB_LIBRARY_GET_STATE_ERROR_PATIENCE):

        # init ykush lib
        yk = pykush.YKUSH(self.usb_info["ykush_serial"])

        # attempt `error_patience` times to get state (in case it reports YKUSH_PORT_STATE_ERROR)
        state = yk.get_port_state(self.usb_info.get("ykush_port"))
        while state == pykush.YKUSH_PORT_STATE_ERROR and error_patience > 0:
            time.sleep(constants.USB_LIBRARY_GET_STATE_RETRY_TIMEOUT)
            state = yk.get_port_state(self.usb_info.get("ykush_port"))
            error_patience -= 1

        return self.__state_to_str(state)

    ##################################################################
    # PRIVATE
    ##################################################################

    # converts int state to str
    def __state_to_str(self, state):

        if state == pykush.YKUSH_PORT_STATE_DOWN:
            return "disabled"

        if state == pykush.YKUSH_PORT_STATE_UP:
            return "enabled"

        if state == pykush.YKUSH_PORT_STATE_ERROR:
            usb_port = self.usb_info.get("ykush_port")
            blade_logger.logger.error(f"Error: Persistent YKUSH_PORT_STATE_ERROR while getting state of ykush port '{usb_port}'.")
            raise Exception(
                f"Error: Persistent YKUSH_PORT_STATE_ERROR while getting state of ykush port '{usb_port}'."
            )

        raise Exception(f"Error: Unknown state: '{state}'.")

    # converts str state to int
    def __str_to_state(self, state_str):

        if state_str == "disabled":
            return pykush.YKUSH_PORT_STATE_DOWN

        if state_str == "enabled":
            return pykush.YKUSH_PORT_STATE_UP

        blade_logger.logger.error(f"Error: Unknown state_str: '{state_str}'.")
        raise Exception(f"Error: Unknown state_str: '{state_str}'.")

    def __get_all_available_ids(self):

        devices = usb.core.find(find_all=True)
        all_ids = []
        for device in devices:
            device_id = "%04x:%04x" % (device.idVendor, device.idProduct)
            all_ids.append(device_id)
        return all_ids
