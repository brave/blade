# Note:   Useful external async calls for measuring performance
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   09/03/2023

import os
import signal
import subprocess
import time

from libs import tools

# get current file path
__location__ = os.path.dirname(os.path.realpath(__file__))


# start collecting adb measurements
def collect_adb_measurements(adb_identifier, sleep_time, sw_power_enabled, output_file):

    # collect measurements
    script = os.path.join(__location__, "../collect_adb_measurements.sh")
    process = subprocess.Popen(
        [
            script,
            adb_identifier,
            str(sleep_time),
            str(int(sw_power_enabled)),
            output_file,
        ]
    )

    # save pid to file
    filename = ".adb_measurements_pid"
    tools.save_value_to_file(process.pid, filename)


# stop collecting adb measurements
def stop_collecting_adb_measurements():

    pid = tools.read_value_from_file(".adb_measurements_pid")
    if pid:

        try:
            os.kill(int(pid), signal.SIGKILL)
        except OSError:
            print("Warning: Could not stop adb measurements. Process already stopped.")


# start collecting nethogs measurements
def collect_nethogs_measurements(adb_identifier, delay, output_file):

    # collect measurements
    script = os.path.join(__location__, "../collect_nethogs_measurements.sh")
    process = subprocess.Popen(
        [script, adb_identifier, str(delay), output_file])

    # save pid to file
    filename = ".nethogs_measurements_pid"
    tools.save_value_to_file(process.pid, filename)


# stop collecting nethogs measurements
def stop_collecting_nethogs_measurements():

    pid = tools.read_value_from_file(".nethogs_measurements_pid")
    if pid:

        try:
            os.kill(int(pid), signal.SIGKILL)
        except OSError:
            print(
                "Warning: Could not stop nethogs measurements. Process already stopped."
            )


# start collecting monsoon measurements
def collect_monsoon_measurements(output_file):

    # collect measurements
    script = os.path.join(__location__, "../control-monsoon.py")
    process = subprocess.Popen(
        [script, "--collect-measurements", "--output", output_file]
    )

    # save pid to file
    filename = ".monsoon_measurements_pid"
    tools.save_value_to_file(process.pid, filename)


# stop collecting monsoon measurements
def stop_collecting_monsoon_measurements():

    pid = tools.read_value_from_file(".monsoon_measurements_pid")
    if pid:

        try:
            os.kill(int(pid), signal.SIGINT)
        except OSError:
            print(
                "Warning: Could not stop monsoon measurements. Process already stopped."
            )


# connect to a Bluetooth device
def connect_to_bt_device(bt_mac_address):

    # collect measurements
    script = os.path.join(__location__, "../bt-connect.py")
    process = subprocess.Popen(["sudo", script, "--device", bt_mac_address])
    time.sleep(5)

    # save pid to file
    filename = ".bt-connect_pid"
    tools.save_value_to_file(process.pid, filename)


# disconnect from a Bluetooth device
def disconnect_from_bt_device():

    pid = tools.read_value_from_file(".bt-connect_pid")
    if pid:

        try:
            os.kill(int(pid), signal.SIGINT)
        except OSError:
            print(
                "Warning: Could not disconnect from Bluetooth device. Process already stopped."
            )
    time.sleep(5)
