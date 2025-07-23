#!/usr/bin/python3

# Note:   Type using BT keyboard
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   16/02/2024


import argparse
import sys

from libs import btklib
from libs import constants


def main(args):
    message = args.message
    delay = args.delay

    btk = btklib.BtkLib()
    btk.send_text(message, delay=delay)


# argument parser
def __parse_arguments(args):

    parser = argparse.ArgumentParser(description="Type using BT keyboard")

    parser.add_argument("message", 
                        help="Message to type")
    
    parser.add_argument("-d", "--delay", type=float, default=constants.BT_IOS_COMMANDS_DEFAULT_KEYBOARD_TYPE_DELAY,
                        help=f"Delay between characters (in seconds). Default is {constants.BT_IOS_COMMANDS_DEFAULT_KEYBOARD_TYPE_DELAY}.")

    parsed = parser.parse_args(args)
    return parsed


if __name__ == "__main__":

    # parse args
    arguments = __parse_arguments(sys.argv[1:])
    main(arguments)
