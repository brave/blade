# Note:   Useful Lighthouse functions for controlling Android devices
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   14/12/2023

import os
import time

from libs import constants

def activate_port_fw(device, port=9222):

    command = f"adb -s {device['adb_identifier']} forward tcp:{port} localabstract:chrome_devtools_remote"
    os.system(command)
    time.sleep(constants.LIGHTHOUSE_COMMANDS_WAIT_TIME)


def deactivate_port_fw(device, port=9222):

    command = f"adb -s {device['adb_identifier']} forward --remove tcp:{port}"
    os.system(command)
    time.sleep(constants.LIGHTHOUSE_COMMANDS_WAIT_TIME)


def deactivate_all_port_fw(device):

    command = f"adb -s {device['adb_identifier']} forward --remove-all"
    os.system(command)
    time.sleep(constants.LIGHTHOUSE_COMMANDS_WAIT_TIME)


def measure_url(url, path, port=9222, max_wait_load_time=200000):

    # make sure path exists
    os.makedirs(path, exist_ok=True)
    filename = "".join(
        filter(str.isalnum, url)
    )  # remove special (illegal for filename) characters
    filepath = os.path.join(path, f"{filename}.json")

    command = f"lighthouse {url} --max-wait-for-load {max_wait_load_time} --port={port} --save-assets --emulated-form-factor=none --throttling-method=provided --output-path={filepath} --output=json"
    os.system(command)
    time.sleep(constants.LIGHTHOUSE_COMMANDS_WAIT_TIME)
