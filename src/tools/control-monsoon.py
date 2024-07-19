#!/usr/bin/python

# Note:   Control Monsoon device to enable data collection
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   06/02/2023

import argparse
import os
import sys

from libs import monsoonlib

##################################################################
# MAIN
##################################################################


def main(args):

    # init lib
    monsoon = monsoonlib.Monsoon()

    # --init-state
    if args.init_state:
        monsoon.init_state()
        return

    # --read-state
    if args.read_state:
        state = monsoon.read_state()
        print(state)
        return

    # --switch
    if args.switch is not None:
        state = args.switch
        monsoon.switch(state)
        return

    # check if monsoon is available
    if not monsoon.is_available():
        sys.exit("Error: Monsoon is not available.")

    # connect to monsoon
    if not monsoon.connect():
        sys.exit("Error: Could not connect to Monsoon")

    # Set voltage if needed
    voltage = args.set_voltage
    if voltage is not None:
        print("Setting voltage to: " + str(voltage))
        monsoon.set_voltage(voltage)

    # Collect measurements if needed
    if args.collect_measurements:
        output = args.output
        duration = args.duration
        t_sleep = args.t_sleep
        if duration:
            print(f"Collecting measurements for {duration} secs...")
        else:
            print(f"Collecting measurements...")
        start_time = monsoon.collect_measurements(output, duration, t_sleep)
        print(f"Done! .t_monsoon: {start_time}")


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

    return parser.parse_args(args)


if __name__ == "__main__":

    # parse args
    arguments = __parse_arguments(sys.argv[1:])
    main(arguments)
