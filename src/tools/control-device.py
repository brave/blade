#!/usr/bin/python

# Note:   Control BLaDE automations
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   17/02/2023

import argparse
import datetime
import glob
import importlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

from libs import adblib
from libs import async_calls as acalls
from libs import monsoonlib, tools, tslog, usblib, volswitchlib

# get current file path
__location__ = os.path.dirname(os.path.realpath(__file__))

# read device configuration file
devices_config_path = os.path.join(__location__, "configs", "devices.json")
with open(devices_config_path, encoding="utf-8") as f:
    devices = json.load(f)


def switch(device, state):

    # init libs
    monsoon = monsoonlib.Monsoon()
    vs = volswitchlib.VoltageSwitch()
    usb_control = usblib.USBControl(device["usb"])

    # get properties
    monsoon_info = device.get("monsoon")
    if monsoon_info is None:
        sys.exit("Error: Device doesn't have a Monsoon configuration.")
    channel = monsoon_info["channel"]

    if state == "on":

        # check if all devices are off
        if not vs.is_all_channels_off():
            sys.exit(
                "Error: All devices must be switched off before switching to a new device."
            )

        # switch monsoon on
        monsoon.switch("on")

        # check if device is available
        if not monsoon.wait_for_device_availability():
            sys.exit("Error: Monsoon is not available.")

        # connect to monsoon
        if not monsoon.connect():
            sys.exit("Error: Could not connect to Monsoon")

        # enable device's USB
        usb_control.set_state("enabled")

        # switch voltage to the device
        vs.switch_to(channel)
        time.sleep(1)

        # set voltage to the device
        voltage = monsoon_info["voltage"]
        monsoon.set_voltage(voltage)
        monsoon.disconnect()

        # wait for device to become available
        if not usb_control.wait_for_device_availability():
            sys.exit("Error: Device is not available.")
        time.sleep(5)  # Extra 5 secs are needed atop of the above

        # sync time for iOS (Android only possible for rooted devices)
        if device["os"] == "iOS":
            print("Syncing device time with Pi...")
            subprocess.run("idevicedate -c", shell=True, check=True, text=True)
            time.sleep(1)

        # if iOS, unlock device to authorize USB connection
        if device["os"] == "iOS":

            # bt connect
            acalls.connect_to_bt_device(device["bt_mac_address"])
            time.sleep(1)

            # screen unlock
            change_screen_lock(device, "unlock")
            time.sleep(1)

            # lock again
            change_screen_lock(device, "lock")
            time.sleep(1)

            # bt disconnect
            acalls.disconnect_from_bt_device()

        # done
        print("Device is ready.")
        return

    if state == "off":

        # check if already on
        if vs.read_state(channel) == "off":
            print("Warning: Device appears to be 'off' already.")

        # TODO: disable adb-over-wifi if needed

        # disable USB
        if usb_control.get_state() == "enabled":
            usb_control.set_state("disabled")

        # check if device is available
        if monsoon.read_state() == "on" and monsoon.is_available():

            try:
                # set voltage to 0 and disconnect
                monsoon.connect()
                monsoon.set_voltage(0)
                monsoon.disconnect()
                time.sleep(1)

            except Exception as e:
                print(f"Error: {e}")

        # switch to device using GPIO
        vs.switch_off(channel)

        # switch monsoon off
        monsoon.switch("off")

        # done
        return

    sys.exit(f"Unknown state: '{state}'")


def change_screen_lock(device, screen_lock_state):

    # TODO: right now it relies on being in measuring mode (since BT is only available then). Fix is required.

    # check state first
    if read_state(device) == "off":
        sys.exit("Error: Device is off.")

    # init device
    if device["os"] == "Android":
        sys.exit(
            "Changing the device lock state is only supported for iOS devices for now."
        )

    elif device["os"] == "iOS":

        # TODO: dirty. Should be at toplevel (though causing BT issues if iOS device not available. Needs fix)
        from libs.automation import bt_ios_commands

        if screen_lock_state == "lock":
            bt_ios_commands.lock_device(device)

        elif screen_lock_state == "unlock":
            bt_ios_commands.unlock_device(device)

        else:
            sys.exit(f"Unknown screen lock state: '{screen_lock_state}'")

    else:
        sys.exit(f"Error: Device has unknown OS: '{device['os']}'")


def read_state(device):
    vs = volswitchlib.VoltageSwitch()
    channel = device["monsoon"]["channel"]
    return vs.read_state(channel)


def start_measuring(device, output_path):

    # check state first
    if read_state(device) == "off":
        sys.exit("Error: Device is off.")

    # check if device is available
    usb_control = usblib.USBControl(device["usb"])
    if not usb_control.is_device_available():
        sys.exit("Device doesn't appear to be available.")

    # init device
    if device["os"] == "Android":
        adblib.enable_adb_over_wifi(device)
        time.sleep(3)

        adb_identifier = f"{device['ip']}:5555"

        # SW-based measuring using ADB
        sleep_time = 3
        sw_power_enabled = False
        output_file = os.path.join(output_path, "measurements_adb.csv")
        acalls.collect_adb_measurements(
            adb_identifier, sleep_time, sw_power_enabled, output_file
        )
        time.sleep(1)

        # collect nethogs measurements
        # delay = 1
        # output_file = os.path.join(output_path, 'measurements_nethogs.csv')
        # acalls.collect_nethogs_measurements(adb_identifier, delay, output_file)
        # time.sleep(1)

    elif device["os"] == "iOS":
        pass

    else:
        sys.exit(f"Error: Device has unknown OS: '{device['os']}'")

    # disable USB
    usb_control.set_state("disabled")
    time.sleep(1)

    # HW-based measuring using Monsoon (if available)
    monsoon_info = device.get("monsoon")
    if monsoon_info is None:
        print(
            "Warning: Device doesn't have a Monsoon configuration. Skipping HW-based measurements."
        )

    else:
        # start collecting wtih monsoon (async)
        output_file = os.path.join(output_path, "measurements_monsoon.csv")
        acalls.collect_monsoon_measurements(output_file)
        time.sleep(5)


def stop_measuring(device):

    # check state first
    if read_state(device) == "off":
        sys.exit("Error: Device is off.")

    # Stop HW-based measuring using Monsoon (if available)
    monsoon_info = device.get("monsoon")
    if monsoon_info is None:
        print(
            "Warning: Device doesn't have a Monsoon configuration. Skipping stopping HW-based measurements."
        )

    else:
        # stop measuring with monsoon (async)
        acalls.stop_collecting_monsoon_measurements()

    # re-enable USB
    usb_control = usblib.USBControl(device["usb"])
    usb_control.set_state("enabled")
    time.sleep(1)

    # restore device state
    if device["os"] == "Android":

        # stop SW-based measuring using ADB
        acalls.stop_collecting_adb_measurements()
        time.sleep(1)

        # stop collecting nethogs measurements
        # acalls.stop_collecting_nethogs_measurements()
        # time.sleep(1)

        # disable adb-over-wifi
        adblib.disable_adb_over_wifi(device)
        time.sleep(1)

    elif device["os"] == "iOS":
        pass

    else:
        sys.exit(f"Error: Device has unknown OS: '{device['os']}'")


def get_available_experiments():
    exp_files = glob.glob(os.path.join(__location__, "experiments/*.py"))
    return exp_files


def execute_experiment(device, connection, experiment, output_path):

    # check state first
    if read_state(device) == "off":
        sys.exit("Error: Device is off.")

    # check if experiment filename exists
    exp_filename = os.path.join(
        __location__, f"experiments/{experiment[0]}.py")
    if not os.path.isfile(exp_filename):
        sys.exit(f"Error: Experiment '{experiment[0]}' doesn't exist.")

    # load experiment
    exp_module = importlib.import_module(f"experiments.{experiment[0]}")
    if exp_module is None:
        sys.exit(f"Error: Unable to load experiment '{experiment[0]}'.")

    # check if experiment is supported on this device
    if exp_module.automation_type() not in device["supported_automations"]:
        sys.exit(
            f"Error: Experiment '{experiment[0]}' is not supported on this device."
        )

    print("Description: " + exp_module.description())

    # call experiment module functions
    arguments = experiment[1:]
    if exp_module.check_device(device) and exp_module.check_arguments(arguments):

        # init tslogger
        output_file = os.path.join(output_path, "measurements_ts.csv")
        tslogger = tslog.TSLog(output_file, device, connection)

        try:
            # run experiment
            exp_module.setup_device(device, tslogger, arguments)
            exp_module.run_experiment(device, tslogger, arguments)
            exp_module.cleanup_device(device, tslogger, arguments)

        except KeyboardInterrupt:
            print("Experiment interrupted by user.")

        # close tslogger
        tslogger.close()

    else:
        sys.exit(f"Error: Experiment '{experiment[0]}' failed.")


##################################################################
# MAIN
##################################################################


def main(args):

    # list devices
    if args.list_devices:
        print("Available devices:\n")
        for device in devices:
            print(f" - {device}:")
            print(f"\tOS: {devices[device]['os']}")
            print(f"\tType: {devices[device]['type']}")
            print(
                f"\tHW Measurements: {devices[device].get('monsoon') is not None}")
            print()
        return

    # list experiments
    if args.list_experiments:

        exp_files = get_available_experiments()

        # only keep step (filename without extension)
        experiments = sorted([pathlib.Path(exp).stem for exp in exp_files])

        print("Available experiments:\n")
        for exp in experiments:

            module = importlib.import_module(f"experiments.{exp}")
            print(f" - {exp}:")
            print(f"\tUsage: '{module.usage()}'")
            print(f"\tDescription: {module.description()}")
            print(f"\tAutomation Type: {module.automation_type()}")
            print()
        return

    # device name is mandatory from now on.
    if args.device_name is None:
        sys.exit("Error: You need to set device name (-d / --device).")

    # get device
    device = devices.get(args.device_name)
    if device is None:
        sys.exit(
            f"Device named '{args.device_name}' was not found at '{devices_config_path}'."
        )

    # read_state (depends on gpio)
    if args.read_state:
        state = read_state(device)
        print(f"Device '{args.device_name}' is {state}.")
        return

    # switch
    if args.switch is not None:
        print(f"Switching device '{args.device_name}' {args.switch}...")
        switch(device, args.switch)
        print("Done!")
        return

    # screen
    if args.screen is not None:
        print(
            f"Changing device '{args.device_name}' screen lock state to '{args.screen}'..."
        )
        change_screen_lock(device, args.screen)
        print("Done!")
        return

    # start measuring
    if args.measuring is not None:

        if args.measuring == "start":
            output_path = args.output
            tools.ensure_path(output_path)

            print(f"Started measuring device '{args.device_name}'...")
            start_measuring(device, output_path)

        elif args.measuring == "stop":
            print(f"Stopped measuring device '{args.device_name}'...")
            stop_measuring(device)

        return

    # bt connect/disconnect
    if args.bt is not None:

        if args.bt == "connect":
            print(
                f"Connect to the device using Bluetooth... ({device['bt_mac_address']})"
            )
            acalls.connect_to_bt_device(device["bt_mac_address"])

        elif args.bt == "disconnect":
            print(
                f"disconnect Bluetooth from the device... ({device['bt_mac_address']})"
            )
            acalls.disconnect_from_bt_device()

        return

    # execute experiment
    if args.execute_experiment is not None:

        output_path = args.output
        tools.ensure_path(output_path)

        start_time = time.perf_counter()

        print(
            f"Executing experiment '{args.execute_experiment[0]}' on device '{args.device_name}'..."
        )
        execute_experiment(
            device, args.connection, args.execute_experiment, output_path
        )

        elapsed_time = time.perf_counter() - start_time
        print(
            f"Completed! Duration: {str(datetime.timedelta(seconds=int(elapsed_time)))}"
        )
        return

    # if not action chosen, report error
    sys.exit("Error: You haven't selected any device operation.")


# argument parser
def __parse_arguments(args):

    parser = argparse.ArgumentParser(
        description="Control BLaDE automations.")

    parser.add_argument(
        "-ld",
        "--list-devices",
        action="store_true",
        help="List all available devices and states.",
    )

    parser.add_argument(
        "-d",
        "--device",
        dest="device_name",
        choices=devices.keys(),
        required=False,
        default=None,
        help="Required device name for control operations.",
    )

    parser.add_argument(
        "-rs",
        "--read-state",
        action="store_true",
        help="Read the device's state (on/off).",
    )

    parser.add_argument(
        "-s",
        "--switch",
        choices=["on", "off"],
        default=None,
        help="Set device power to on/off.",
    )

    parser.add_argument(
        "-m",
        "--measuring",
        choices=["start", "stop"],
        default=None,
        help="Start/Stop measuring the chosen device. Power discharge is measured using Monsoon (iOS and Android), but also using ADB (Android only). CPU is measured using ADB (Android only).",
    )

    parser.add_argument(
        "--bt",
        choices=["connect", "disconnect"],
        default=None,
        help="Connect/Disconnect the BT HID (required for bt-based automations).",
    )

    parser.add_argument(
        "--screen",
        choices=["lock", "unlock"],
        default=None,
        help="Unlock/Lock the device. Pin will be used if available in configuration.",
    )

    parser.add_argument(
        "-le",
        "--list-experiments",
        action="store_true",
        help="List all available experiments.",
    )

    parser.add_argument(
        "-ee",
        "--execute-experiment",
        type=str,
        nargs="+",
        metavar=("experiment", "arguments"),
        default=None,
        help="Execute an experiment listed in 'experiments' folder. First argument is always the experiment name. The rest are optional arguments that are passed to the experiment script.",
    )

    connection_options = ["usb", "wifi"]
    parser.add_argument(
        "-c",
        "--connection",
        choices=connection_options,
        default=connection_options[1],
        help="ADB connection (relevant to ADB automations only)",
    )

    parser.add_argument(
        "-o",
        "--output",
        required=False,
        default="measurements",
        help="Output folder for storing the measurements.",
    )

    parsed = parser.parse_args(args)
    return parsed


if __name__ == "__main__":

    # parse args
    arguments = __parse_arguments(sys.argv[1:])
    main(arguments)
