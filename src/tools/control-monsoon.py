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
from libs import tools
from libs import constants

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
        sys.exit(1)

    # connect to monsoon
    if not monsoon.connect():
        blade_logger.logger.critical("Error: Could not connect to Monsoon")
        sys.exit(1)

    # Set voltage if needed
    voltage = args.set_voltage
    if voltage is not None:
        blade_logger.logger.info("Setting output voltage (V) to: " + str(voltage))
        monsoon.set_voltage(voltage)

    # Collect measurements if needed
    if args.collect_measurements:
        output = args.output
        format = args.format
        duration = args.duration
        granularity = args.granularity
        if duration:
            blade_logger.logger.info(f"Collecting measurements for {duration} secs...")
        else:
            blade_logger.logger.info(f"Collecting measurements...")
        start_time = monsoon.collect_measurements(output, format=format, duration=duration, granularity=granularity)
        blade_logger.logger.info(f"Done! .t_monsoon: {start_time}")

    # disconnect from monsoon
    monsoon.disconnect()


# argument parser
def __parse_arguments(args):

    parser = argparse.ArgumentParser(
        description="Control Monsoon Power Monitor devices (HVPM version)."
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
        metavar=f"[{constants.MONSOON_MIN_VOLTAGE}-{constants.MONSOON_MAX_VOLTAGE}]",
        default=None,
        help=f"Set or change the output voltage (V) in range {constants.MONSOON_MIN_VOLTAGE}-{constants.MONSOON_MAX_VOLTAGE}. Set to '0' to deactivate power output.",
    )

    parser.add_argument(
        "-cm",
        "--collect-measurements",
        action="store_true",
        help="Start collecting measurements. If no duration is provided, measurements will be collected indefinitely. Exact `start_time` of data collection is stored at `.t_monsoon` file in the output directory, and as metadata if parquet format is selected.",
    )

    parser.add_argument(
        "-d",
        "--duration",
        type=int,
        metavar="[0-inf]",
        default=None,
        help="Data collection duration (in sec). Default is None (infinite).",
    )

    parser.add_argument(
        "-g",
        "--granularity",
        type=int,
        choices=range(1, constants.MONSOON_COLLECTED_SAMPLES_PER_BATCH + 1),
        metavar=f"[1-{constants.MONSOON_COLLECTED_SAMPLES_PER_BATCH}]",
        default=1,
        help=f"Downsample collected data by this factor. 1 means no downsampling (approx 5kHz in HVPM model), 10 means 1 sample every 10 samples. Must be between 1 and {constants.MONSOON_COLLECTED_SAMPLES_PER_BATCH}. Default is 1.",
    )

    parser.add_argument(
        "-f",
        "--format",
        choices=["csv", "parquet"],
        default="csv",
        help="Output file format. Default is 'csv'.",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="measurements.csv",
        help="Output file in csv or parquet format. Format: time (sec), current (mA), voltage (V). Default is 'measurements.csv'.",
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
