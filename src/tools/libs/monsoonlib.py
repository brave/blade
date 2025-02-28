# Note:   Control Monsoon devices to enable data collection
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   20/02/2023

import json
import os
import time

import Monsoon.HVPM as Monitor
import Monsoon.Operations as op
from libs import gpiolib, tools, usblib
from Monsoon import sampleEngine
from libs import logger as blade_logger

# get current file path
__location__ = os.path.dirname(os.path.realpath(__file__))


class Monsoon:

    def __init__(self):
        self.config = self.__read_config()
        self.monitor = None

    def __read_config(self):

        # read monsoon's configuration file
        filename = os.path.join(__location__, "../configs", "monsoon.json")
        with open(filename, encoding="utf-8") as f:
            return json.load(f)

    # connect to monsoon device
    def connect(self):

        monitor = Monitor.Monsoon()

        try:
            monitor.setup_usb()
            monitor.fillStatusPacket()
            blade_logger.logger.info(
                "Connected to Monsoon with Serial Number: "
                + str(monitor.getSerialNumber())
            )
            self.monitor = monitor
            return True

        except Exception:
            blade_logger.logger.error("Monsoon is currently unreachable.")
            self.monitor = None
            return False

    def is_available(self):
        usb_control = usblib.USBControl(self.config["usb"])
        port_available = usb_control.is_device_available()
        return port_available

    def wait_for_device_availability(self, timeout=60 * 5):
        usb_control = usblib.USBControl(self.config["usb"])
        device_available = usb_control.wait_for_device_availability(timeout)
        return device_available

    def disconnect(self):
        if self.monitor:
            self.monitor.closeDevice()
            self.monitor = None

    def init_state(self):
        pin = self.config["gpio_pin"]
        default_state = self.__state_to_int("off")
        gpiolib.init(pin, default_state)

    def read_state(self):
        pin = self.config["gpio_pin"]
        state = gpiolib.read(pin)
        return self.__state_to_str(state)

    def switch(self, state):
        pin = self.config["gpio_pin"]
        state = self.__state_to_int(state)
        gpiolib.write(pin, state)

    def set_voltage(self, voltage):

        # if not connected
        if self.monitor is None:
            blade_logger.logger.error("Error: You need to call 'connect()' first")
            return

        self.monitor.setVout(voltage)

    # Enable data collection in CSV format
    # original code from Matteo Varvello at Brave Software
    def collect_measurements(self, output, duration=None, t_sleep=0):

        # if not connected
        if self.monitor is None:
            blade_logger.logger.error("Error: You need to call 'connect()' first")
            return None

        # delete outputs if exists
        if os.path.exists(output):
            os.remove(output)

        # put monsoon in sample mode
        HVengine = sampleEngine.SampleEngine(self.monitor)

        # configure output channels
        ##########################################
        HVengine.enableChannel(sampleEngine.channels.MainCurrent)
        HVengine.enableChannel(sampleEngine.channels.MainVoltage)
        HVengine.disableChannel(sampleEngine.channels.USBCurrent)
        HVengine.disableChannel(sampleEngine.channels.USBVoltage)
        HVengine.disableChannel(sampleEngine.channels.AuxCurrent)
        self.monitor.setUSBPassthroughMode(op.USB_Passthrough.Off)
        ##########################################

        HVengine.ConsoleOutput(False)
        HVengine.periodicStopSampling(closeCSV=True)
        HVengine.periodicStartSampling()
        HVengine.enableCSVOutput(output)

        start_time = time.time()
        curr_time = start_time

        # sync barrier
        custom_path = os.path.dirname(output)
        sync_filename = ".t_monsoon"
        tools.save_value_to_file(str(start_time), sync_filename, custom_path=custom_path)

        try:
            # iterate on data collection
            while duration == None or (curr_time - start_time) < duration:
                HVengine.periodicCollectSamples(100)

                # rate control
                time.sleep(t_sleep / 1000)
                curr_time = time.perf_counter()

        except KeyboardInterrupt:
            blade_logger.logger.info("Collecting measurements was interrupted by user.")

        # close everything
        HVengine.periodicStopSampling(closeCSV=True)

        return start_time

    # converts int state to str (0: off and 1: on in this context)
    def __state_to_str(self, state):

        if state == 0:
            return "off"

        if state == 1:
            return "on"

        blade_logger.logger.error(f"Error: Unknown state: '{state}'.")
        raise Exception(f"Error: Unknown state: '{state}'.")

    # converts str state to int (0: off and 1: on in this context)
    def __state_to_int(self, state_str):

        if state_str == "off":
            return 0

        if state_str == "on":
            return 1

        blade_logger.logger.error(f"Error: Unknown state: '{state_str}'.")
        raise Exception(f"Error: Unknown state: '{state_str}'.")
