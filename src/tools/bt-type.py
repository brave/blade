#!/usr/bin/python

# Note:   Type using BT keyboard
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   16/02/2024


import argparse
import json
import os
import sys

from libs import btklib

# get current file path
__location__ = os.path.dirname(os.path.realpath(__file__))

# read device configuration file
devices_config_path = os.path.join(__location__, "configs", "devices.json")
with open(devices_config_path, encoding="utf-8") as f:
    devices = json.load(f)


def main(args):
    message = args.message

    btk = btklib.BtkLib()
    btk.send_text(message, delay=0.1)


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
