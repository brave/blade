#!/usr/bin/python3

# Note:   Type using BT keyboard
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   16/02/2024


import argparse
import os
import sys

from libs import btklib
from libs import constants


def main(args):
    message = args.message

    btk = btklib.BtkLib()
    btk.send_text(message, delay=constants.TENTH_OF_A_SECOND)


# argument parser
def __parse_arguments(args):

    parser = argparse.ArgumentParser(description="Type using BT keyboard")

    parser.add_argument("-m", "--message", required=True,
                        help="Message to type")

    parsed = parser.parse_args(args)
    return parsed


if __name__ == "__main__":

    # parse args
    arguments = __parse_arguments(sys.argv[1:])
    main(arguments)
