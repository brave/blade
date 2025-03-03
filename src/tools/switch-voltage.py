#!/usr/bin/python

# Note:   Switch Monsoon voltage to a particular channel
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   01/03/2023

import argparse
import sys

from libs import volswitchlib

##################################################################
# MAIN
##################################################################


def main(args):

    # init lib
    vs = volswitchlib.VoltageSwitch()

    if args.init_state is True:
        vs.init_state()
        return

    if args.switch_all_off is True:
        vs.switch_all_off()
        return

    if args.switch_to is not None:
        channel = args.switch_to
        vs.switch_to(channel)
        return

    if args.switch_off is not None:
        channel = args.switch_off
        vs.switch_off(channel)
        return

    if args.read_state is not None:
        channel = args.read_state
        state = vs.read_state(channel)
        print(f"Channel '{channel}' is {state}.")
        return

    sys.exit("Error: You haven't selected any operation.")


# argument parser
def __parse_arguments(args):

    parser = argparse.ArgumentParser(
        description="Control BLaDE automations.")

    parser.add_argument(
        "-is",
        "--init-state",
        action="store_true",
        help="Init all channel's relevant GPIO to off (required once on Pi's boot).",
    )

    parser.add_argument(
        "-sao",
        "--switch-all-off",
        action="store_true",
        help="Switch off the voltage entirely (same behaviour with --init-state).",
    )

    parser.add_argument(
        "-st",
        "--switch-to",
        required=False,
        default=None,
        help="Switch the voltage into the particular channel.",
    )

    parser.add_argument(
        "-so",
        "--switch-off",
        required=False,
        default=None,
        help="Switch off the voltage of the particular channel",
    )

    parser.add_argument(
        "-rs",
        "--read-state",
        required=False,
        default=None,
        help="Read the channel's state (on/off).",
    )

    parsed = parser.parse_args(args)
    return parsed


if __name__ == "__main__":

    # parse args
    arguments = __parse_arguments(sys.argv[1:])
    main(arguments)
    