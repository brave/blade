#!/usr/bin/python3

# Note:   Control BLaDE automations
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   17/02/2023

import argparse
import os
import sys
import logging

from libs import devicelib
from libs import logger as blade_logger
from libs import tools

HOME = os.path.expanduser("~")
DEVICES = devicelib.get_devices()


##################################################################
# MAIN
##################################################################

def main(args):

    # log output to a logfile if enabled
    if args.log_output:
        filename = os.path.join(args.output, "log.txt")
        tools.ensure_path(args.output, clear=True)
        blade_logger.add_file_handler(log_file=filename)

    # set log-level if specified
    if args.log_level:
        blade_logger.set_logging_level(level=args.log_level)

    blade_logger.logger.info("Control-Device")

    # list devices
    if args.list_devices:
        blade_logger.logger.info("Available devices:\n")
        for device_key, device in DEVICES.items():
            blade_logger.logger.info(f" - {device_key}:")
            blade_logger.logger.info(f"\tOS: {device['os']}")
            blade_logger.logger.info(f"\tType: {device['type']}")
            blade_logger.logger.info(f"\tHW Measurements: {device.get('monsoon') is not None}")
            blade_logger.logger.info("")
        return

    # device name is mandatory from now on.
    if args.device_name is None:
        blade_logger.logger.critical("Error: You need to set device name (-d / --device).")
        sys.exit("Error: You need to set device name (-d / --device).")

    # get device
    device = DEVICES.get(args.device_name)
    if device is None:
        blade_logger.logger.critical(f"Device named '{args.device_name}' was not found at 'src/tools/configs/devices.json'.")
        sys.exit(
            f"Device named '{args.device_name}' was not found at 'src/tools/configs/devices.json'."
        )

    # read_state (depends on gpio)
    if args.read_state:
        state = devicelib.read_state(device)
        blade_logger.logger.info(f"Device '{args.device_name}' is {state}.")
        return

    # switch
    if args.switch is not None:
        blade_logger.logger.info(f"Switching device '{args.device_name}' {args.switch}...")
        devicelib.switch(device, args.switch, auto_recharge_battery_level=args.auto_recharge)
        blade_logger.logger.info("Done!")
        return

    # screen
    if args.screen is not None:
        blade_logger.logger.info(
            f"Changing device '{args.device_name}' screen lock state to '{args.screen}'..."
        )
        devicelib.change_screen_lock(device, args.screen)
        blade_logger.logger.info("Done!")
        return

    # start measuring
    if args.measuring is not None:

        if args.measuring == "start":
            output_path = args.output

            blade_logger.logger.info(f"Started measuring device '{args.device_name}'...")
            devicelib.start_measuring(device, output_path, auto_recharge_battery_level=args.auto_recharge)

        elif args.measuring == "stop":
            blade_logger.logger.info(f"Stopped measuring device '{args.device_name}'...")
            devicelib.stop_measuring(device)

        return

    # bt connect/disconnect
    if args.bt is not None:

        if args.bt == "connect":
            blade_logger.logger.info(
                f"Connect to the device using Bluetooth... ({device['bt_mac_address']})"
            )
            devicelib.connect_to_bt_device(device)

        elif args.bt == "disconnect":
            blade_logger.logger.info(
                f"disconnect Bluetooth from the device... ({device['bt_mac_address']})"
            )
            devicelib.disconnect_from_bt_device()

        return
    
    # remote control
    if args.remote_control is not None:
        if args.remote_control == "enable":
            blade_logger.logger.info(f"Enabling remote control for device '{args.device_name}'...")
            devicelib.enable_remote_control(device)
        elif args.remote_control == "disable":
            blade_logger.logger.info(f"Disabling remote control for device '{args.device_name}'...")
            devicelib.disable_remote_control()
        return

    # if not action chosen, report error
    blade_logger.logger.error("Error: You haven't selected any device operation.")


# argument parser
def __parse_arguments(args):

    parser = argparse.ArgumentParser(
        description="Control BLaDE automations.")
    
    # Positional argument for "device name", not required initially
    parser.add_argument(
        dest="device_name",
        nargs="?",
        choices=DEVICES.keys(),
        default=None,
        help="Required device name for control operations.",
    )

    parser.add_argument(
        "-ld",
        "--list-devices",
        action="store_true",
        help="List all available devices and states.",
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
        "-o",
        "--output",
        required=False,
        default=os.path.join(HOME, "measurements"),
        help="Output folder for storing the measurements. Default is '~/measurements'.",
    )

    parser.add_argument(
        "--remote-control",
        choices=["enable", "disable"],
        default=None,
        help="Enable/Disable remote control for the device. Only available for Android devices.",
    )

    def ratio_type(value):
        try:
            value = float(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"'{value}' is not a valid float.")
        if 0.0 <= value <= 1.0:
            return value
        else:
            raise argparse.ArgumentTypeError(f"'{value}' is out of the allowed range (0.00 to 1.00).")

    parser.add_argument(
        "-ar", "--auto-recharge",
        type=ratio_type,
        metavar="BATTERY_LEVEL_RATIO",
        default=None,
        help="Enable auto-recharge for the device, until the given battery level ratio is reached. 'None' means no auto-recharge. Only available for Android devices. Default threshold is None."
    )

    parser.add_argument(
        "--log-output",
        required=False,
        action='store_true',
        help="Set flag to write logging output to a log file located in the default output folder. Default is False.",
    )

    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        default="",
        help="This flag allows to change the log-level. By default only levels higher than warning will be written to the log.",
    )

    args, _ = parser.parse_known_args()

    # Enforce "device_name" only if -h, -ld or --list-devices is NOT used
    if not args.device_name \
        and "-h" not in sys.argv \
        and "-ld" not in sys.argv \
        and "--list-devices" not in sys.argv:
        parser.error("device_name is required unless -h or -ld is used.")

    return args


if __name__ == "__main__":

    # parse args
    arguments = __parse_arguments(sys.argv[1:])
    main(arguments)
