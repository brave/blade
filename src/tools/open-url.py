#!/usr/bin/python3

# Note:   Open a url at default android
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   15/12/2023


import argparse
import os
import sys

from libs import devicelib
from libs.automation import adb_commands

DEVICES = devicelib.get_devices()


def main(args):
    device_name = args.device_name
    connection = args.connection
    browser = args.browser
    url = args.url

    device = DEVICES[device_name]
    adb_commands.browser_open_url(device, connection, browser, url)


# argument parser
def __parse_arguments(args):

    parser = argparse.ArgumentParser(
        description="Open a url at a web browser of your choice"
    )

    parser.add_argument(
        "-d",
        "--device",
        dest="device_name",
        choices=DEVICES.keys(),
        required=False,
        default=None,
        help="Required device name for control operations.",
    )

    connection_options = ["usb", "wifi"]
    parser.add_argument(
        "-c",
        "--connection",
        choices=connection_options,
        default=connection_options[0],
        help="ADB connection",
    )

    browser_options = [
        "Brave",
        "Chrome",
        "Firefox",
        "Firefox Focus",
        "Edge",
        "DuckDuckGo",
        "Opera",
    ]
    parser.add_argument(
        "-b", "--browser", choices=browser_options, required=True, help="Web browser"
    )

    parser.add_argument("-u", "--url", required=True, help="Url to load.")

    parsed = parser.parse_args(args)
    return parsed


if __name__ == "__main__":

    # parse args
    arguments = __parse_arguments(sys.argv[1:])
    main(arguments)
