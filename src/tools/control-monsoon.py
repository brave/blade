#!/usr/bin/python3

# Note:   Control Monsoon device to enable data collection
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   06/02/2023

import argparse
import os
import sys
import logging

from libs import monsoonlib
from libs import logger as blade_logger
from libs import logger as blade_logger
from libs import tools

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

    blade_logger.logger.info("Control-Monsoon")

    # init lib
    monsoon = monsoonlib.Monsoon()

    # --init-state
    if args.init_state:
        monsoon.init_state()
        return

    # --read-state
    if args.read_state:
        state = monsoon.read_state()
        blade_logger.logger.info(state)
        return

    # --switch
    if args.switch is not None:
        state = args.switch
        monsoon.switch(state)
        return

    # check if monsoon is available
    if not monsoon.is_available():
        blade_logger.logger.critical("Error: Monsoon is not available.")

    # connect to monsoon
    if not monsoon.connect():
        blade_logger.logger.critical("Error: Could not connect to Monsoon")

    # Set voltage if needed
    voltage = args.set_voltage
    if voltage is not None:
        blade_logger.logger.info("Setting voltage to: " + str(voltage))
        monsoon.set_voltage(voltage)

    # Collect measurements if needed
    if args.collect_measurements:
        output = args.output
        duration = args.duration
        t_sleep = args.t_sleep
        if duration:
            blade_logger.logger.info(f"Collecting measurements for {duration} secs...")
        else:
            blade_logger.logger.info(f"Collecting measurements...")
        start_time = monsoon.collect_measurements(output, duration, t_sleep)
        blade_logger.logger.info(f"Done! .t_monsoon: {start_time}")


# argument parser
def __parse_arguments(args):

    parser = argparse.ArgumentParser(
        description="Control Monsoon Power Monitor devices (HV and LV versions)."
    )

    parser.add_argument(
        "-is",
        "--init-state",
        action="store_true",
        help="Init Monsoon's relevant GPIO state to off (required once on Pi's boot).",
    )

    parser.add_argument(
        "-rs",
        "--read-state",
        action="store_true",
        help="Read the device's power state (on/off).",
    )

    parser.add_argument(
        "-s",
        "--switch",
        choices=["on", "off"],
        default=None,
        help="Set device power to on/off.",
    )

    parser.add_argument(
        "-sv",
        "--set-voltage",
        type=float,
        default=None,
        help="Set or change the voltage (0 to deactivate).",
    )

    parser.add_argument(
        "-cm",
        "--collect-measurements",
        action="store_true",
        help="Start collecting measurements",
    )

    parser.add_argument(
        "-d",
        "--duration",
        type=int,
        default=None,
        help="Data collectuon duration (in sec)",
    )

    parser.add_argument(
        "-ts",
        "--t-sleep",
        type=int,
        default=0,
        help="Sleep per 100 samples, in ms. Needed for subsampling.",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="measurements.csv",
        help="Output file in csv. Format: time (Sec), current (mA), voltage (V).",
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

    return parser.parse_args(args)


if __name__ == "__main__":

    # parse args
    arguments = __parse_arguments(sys.argv[1:])
    main(arguments)
