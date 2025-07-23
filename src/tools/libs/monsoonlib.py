# Note:   Control Monsoon devices to enable data collection
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   20/02/2023

import json
import os
import time
import csv

import numpy as np
import pandas as pd

import Monsoon.HVPM as Monitor
import Monsoon.Operations as op

from fastparquet import write as write_parquet
from libs import gpiolib, tools, usblib
from Monsoon import sampleEngine
from libs import logger as blade_logger
from libs import constants


# get current file path
__location__ = os.path.dirname(os.path.realpath(__file__))

class Monsoon:

    def __init__(self):
        """
        Initialize a new Monsoon instance.
        Reads configuration from monsoon.json file.
        """
        self.config = self.__read_config()
        self.monitor = None
        self.parquet_buffer = []  # Buffer for accumulating samples before writing to Parquet

    def __read_config(self):
        """
        Read Monsoon configuration from JSON file.
        
        Returns:
            dict: Configuration settings loaded from monsoon.json
        """
        # read monsoon's configuration file
        filename = os.path.join(__location__, "../configs", "monsoon.json")
        with open(filename, encoding="utf-8") as f:
            return json.load(f)

    # connect to monsoon device
    def connect(self):
        """
        Connect to the Monsoon power monitor device.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
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
        """
        Check if the Monsoon device is available on USB.
        
        Returns:
            bool: True if device is available, False otherwise
        """
        usb_control = usblib.USBControl(self.config["usb"])
        port_available = usb_control.is_device_available()
        return port_available

    def wait_for_device_availability(self, timeout=60 * 5):
        """
        Wait for Monsoon device to become available.
        
        Args:
            timeout (int): Maximum time to wait in seconds. Defaults to 300 seconds (5 minutes)
            
        Returns:
            bool: True if device became available within timeout, False otherwise
        """
        usb_control = usblib.USBControl(self.config["usb"])
        device_available = usb_control.wait_for_device_availability(timeout)
        return device_available

    def disconnect(self):
        """
        Disconnect from the Monsoon device and clean up resources.
        """
        if self.monitor:
            self.monitor.closeDevice()
            self.monitor = None

    def init_state(self):
        """
        Initialize GPIO pin state to default 'off' position.
        """
        pin = self.config["gpio_pin"]
        default_state = self.__state_to_int("off")
        gpiolib.init(pin, default_state)

    def read_state(self):
        """
        Read current state of the GPIO pin.
        
        Returns:
            str: Current state ('on' or 'off')
        """
        pin = self.config["gpio_pin"]
        state = gpiolib.read(pin)
        return self.__state_to_str(state)

    def switch(self, state):
        """
        Switch the GPIO pin to specified state.
        
        Args:
            state (str): Desired state ('on' or 'off')
            
        Raises:
            Exception: If state is not 'on' or 'off'
        """
        pin = self.config["gpio_pin"]
        state = self.__state_to_int(state)
        gpiolib.write(pin, state)

    def set_voltage(self, voltage):
        """
        Set output voltage of the Monsoon device.
        
        Args:
            voltage (float): Desired output voltage
            
        Raises:
            Exception: If not connected to Monsoon device
        """

        # check voltage
        if voltage < constants.MONSOON_MIN_VOLTAGE or voltage > constants.MONSOON_MAX_VOLTAGE:
            blade_logger.logger.error(f"Error: Voltage must be between {constants.MONSOON_MIN_VOLTAGE} and {constants.MONSOON_MAX_VOLTAGE}V")
            raise Exception(f"Error: Voltage must be between {constants.MONSOON_MIN_VOLTAGE} and {constants.MONSOON_MAX_VOLTAGE}V")

        # if not connected
        if self.monitor is None:
            blade_logger.logger.error("Error: You need to call 'connect()' first")
            return

        self.monitor.setVout(voltage)

    # Enable data collection in CSV format
    def collect_measurements(self, output_file, format="csv", duration=None, granularity=1):
        """
        Collect power measurements from the Monsoon device.
        
        Args:
            output_file (str): Path to the output file
            format (str): Output format, either 'csv' or 'parquet'
            duration (float, optional): Duration in seconds to collect data, or None for indefinite
            granularity (int): Sampling granularity (1 = full sampling rate)
            
        Returns:
            float: Start time of the measurement
        """
        # Reset parquet buffer at start of collection
        self.parquet_buffer = []

        # check format
        if format not in ["csv", "parquet"]:
            blade_logger.logger.error("Error: Format must be either 'csv' or 'parquet'")
            raise Exception("Error: Format must be either 'csv' or 'parquet'")
        
        # check extension
        if format == "csv":
            if not output_file.endswith(".csv"):
                blade_logger.logger.error("Error: Output file must have a .csv extension")
                raise Exception("Error: Output file must have a .csv extension")
        elif format == "parquet":
            if not output_file.endswith(".parquet"):
                blade_logger.logger.error("Error: Output file must have a .parquet extension")
                raise Exception("Error: Output file must have a .parquet extension")

        # check granularity
        if granularity < 1 or granularity > constants.MONSOON_COLLECTED_SAMPLES_PER_BATCH:
            blade_logger.logger.error(f"Error: Granularity must be between 1 and {constants.MONSOON_COLLECTED_SAMPLES_PER_BATCH}")
            raise Exception(f"Error: Granularity must be between 1 and {constants.MONSOON_COLLECTED_SAMPLES_PER_BATCH}")

        # check granularity
        if granularity < 1 or granularity > 100:
            blade_logger.logger.error("Error: Granularity must be between 1 and 100")
            return None

        # if not connected
        if self.monitor is None:
            blade_logger.logger.error("Error: You need to call 'connect()' first")
            raise Exception("Error: You need to call 'connect()' first")

        # delete outputs if exists
        if os.path.exists(output_file):
            os.remove(output_file)

        # put monsoon in sample mode
        engine = sampleEngine.SampleEngine(self.monitor)
        engine.periodicStopSampling()  # Just in case

        # configure output channels
        engine.enableChannel(sampleEngine.channels.MainCurrent)
        engine.enableChannel(sampleEngine.channels.MainVoltage)
        engine.disableChannel(sampleEngine.channels.USBCurrent)
        engine.disableChannel(sampleEngine.channels.USBVoltage)
        engine.disableChannel(sampleEngine.channels.AuxCurrent)

        # further configurations
        self.monitor.setUSBPassthroughMode(op.USB_Passthrough.Off)
        engine.ConsoleOutput(False)  # disable console output

        # start sampling
        engine.periodicStartSampling()
        start_time = engine._SampleEngine__startTime  # hack to get a ref of the actual start time
        curr_time = start_time

        # choose the correct writer based on the format
        if format == "csv":
            writer = self.__csv_sample_writer

            # initialize the csv file
            output = open(output_file, 'w')
            output_writer = csv.writer(output)
            output_writer.writerow(constants.MONSOON_COLUMN_NAMES)

        elif format == "parquet":
            writer = self.__parquet_sample_writer

            metadata = {
                "start_time": str(start_time).encode('utf-8')
            }

            # initialize the parquet file
            df = pd.DataFrame(columns=constants.MONSOON_COLUMN_NAMES)
            output_writer = output_file  # for consistency with csv writer
            write_parquet(output_writer, df, compression=constants.MONSOON_PARQUET_COMPRESSION, object_encoding='decimal', write_index=False, custom_metadata=metadata)

        else:
            raise Exception("Error: Format must be either 'csv' or 'parquet'")

        # save sync barrier
        output_path = os.path.dirname(output_file)
        tools.save_value_to_file(str(start_time), ".t_monsoon", custom_path=output_path)

        # start data collection
        try:
            while duration == None or (curr_time - start_time) < duration:
                samples = engine.periodicCollectSamples(constants.MONSOON_COLLECTED_SAMPLES_PER_BATCH)
                writer(output_writer, samples, granularity)
                curr_time = time.time()

        except KeyboardInterrupt:
            blade_logger.logger.info("Collecting measurements was interrupted by user.")

        finally:
            engine.periodicStopSampling()
            if format == "parquet" and self.parquet_buffer:
                self.__flush_parquet_buffer(output_writer)
            elif format == "csv":
                output.close()

        return start_time
        
    def __csv_sample_writer(self, output_writer, samples, granularity=1):
        """
        Write power measurement samples to CSV file.
        
        Args:
            output_writer: CSV writer object
            samples: Collection of power measurement samples
            granularity (int): Sampling granularity (1 = full sampling rate)
        """
        samples = self.__format_samples(samples, granularity)
        samples = samples.tolist()
        output_writer.writerows(samples)

    def __parquet_sample_writer(self, output_writer, samples, granularity=1):
        """
        Write power measurement samples to Parquet file.
        
        Args:
            output_writer: Path to output Parquet file
            samples: Collection of power measurement samples
            granularity (int): Sampling granularity (1 = full sampling rate)
        """
        samples = self.__format_samples(samples, granularity)
        samples = pd.DataFrame(samples, columns=constants.MONSOON_COLUMN_NAMES)
        
        # Add samples to buffer
        self.parquet_buffer.append(samples)
        
        # Write to disk when buffer reaches threshold
        if len(self.parquet_buffer) >= constants.MONSOON_PARQUET_BUFFER_SIZE:
            self.__flush_parquet_buffer(output_writer)

    def __flush_parquet_buffer(self, output_writer):
        """
        Flush the Parquet buffer to disk.
        """
        buffered_samples = pd.concat(self.parquet_buffer, ignore_index=True)
        write_parquet(output_writer, buffered_samples, compression=constants.MONSOON_PARQUET_COMPRESSION, write_index=False, append=True)
        self.parquet_buffer = []

    def __format_samples(self, samples, granularity=1):
        """
        Format and downsample measurement data.
        
        Args:
            samples: Raw measurement samples
            granularity (int): Sampling granularity (1 = full sampling rate)
            
        Returns:
            numpy.ndarray: Formatted and downsampled measurement data
        """
        # convert samples to a list of lists with custom granularity

        # only keep the data we need (other columns are empty)
        selected_indexes = [0, 1, 4]  # [time, current, voltage]
        filtered_data = [samples[i] for i in selected_indexes]

        # transpose the data
        samples = np.array(filtered_data)
        samples = samples.T

        # downsample using the given granularity
        if granularity > 1:
            samples = samples[::granularity]

        return samples

    # converts int state to str (0: off and 1: on in this context)
    def __state_to_str(self, state):
        """
        Convert numeric state to string representation.
        
        Args:
            state (int): Numeric state (0 or 1)
            
        Returns:
            str: String state ('off' or 'on')
            
        Raises:
            Exception: If state is not 0 or 1
        """
        if state == 0:
            return "off"

        if state == 1:
            return "on"

        blade_logger.logger.error(f"Error: Unknown state: '{state}'.")
        raise Exception(f"Error: Unknown state: '{state}'.")

    # converts str state to int (0: off and 1: on in this context)
    def __state_to_int(self, state_str):
        """
        Convert string state to numeric representation.
        
        Args:
            state_str (str): String state ('off' or 'on')
            
        Returns:
            int: Numeric state (0 or 1)
            
        Raises:
            Exception: If state_str is not 'off' or 'on'
        """
        if state_str == "off":
            return 0

        if state_str == "on":
            return 1

        blade_logger.logger.error(f"Error: Unknown state: '{state_str}'.")
        raise Exception(f"Error: Unknown state: '{state_str}'.")

    def __enter__(self):
        """Enable use of 'with' statement for automatic resource cleanup"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup resources when exiting 'with' block"""
        self.disconnect()
