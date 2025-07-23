# Note:   Useful ADB-related functions for controlling Android devices
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   04/03/2023

import os
import time
from subprocess import PIPE, Popen

from libs import constants
from libs import logger as blade_logger

# get current file path
__location__ = os.path.dirname(os.path.realpath(__file__))
TCPDUMP_PATH = "/data/local/tmp/tcpdump"


# returns adb identifier base don the connection type
def __get_adb_identifier(device, connection, port=constants.ADB_OVER_WIFI_DEFAULT_PORT):

    if connection == "usb":
        return device["adb_identifier"]

    if connection == "wifi":
        return f"{device['ip']}:{port}"

    raise Exception(f"Error: Unknown connection '{connection}'.")


# enable adb over wifi
def enable_adb_over_wifi(device, port=constants.ADB_OVER_WIFI_DEFAULT_PORT):

    adb_identifier = device["adb_identifier"]
    ip = device["ip"]

    # enable adb over wifi
    os.system(f"adb -s {adb_identifier} tcpip {port}")
    time.sleep(constants.ADB_COMMANDS_EXECUTION_TIMEOUT)

    # disconnect and reconnect over wifi, ignoring the expected error
    with Popen(
        ["adb", "disconnect", "{ip}:{port}"], stdout=PIPE, stderr=PIPE
    ) as process:
        output, _ = process.communicate()
        if output:
            print(output)
    time.sleep(constants.ADB_COMMANDS_EXTENDED_EXECUTION_TIMEOUT)

    os.system(f"adb connect {ip}:{port}")
    time.sleep(constants.ADB_COMMANDS_EXECUTION_TIMEOUT)


# disable adb over wifi
def disable_adb_over_wifi(device, port=constants.ADB_OVER_WIFI_DEFAULT_PORT):

    ip = device["ip"]

    # disable adb over wifi
    os.system(f"adb disconnect {ip}:{port}")
    time.sleep(constants.SWITCH_ADB_CONNECTION_STATE_TIMEOUT)


def get_device_adb_connection_state(device, port=constants.ADB_OVER_WIFI_DEFAULT_PORT):

    # list adb devices and check if given device is listed (either identifier or ip:port)
    output = os.popen("adb devices").read()
    for line in output.splitlines():
        if device["adb_identifier"] in line:
            return "usb"
        elif f"{device['ip']}:{port}" in line:
            return "wifi"

    return None


def power_off_device(device, connection):

    adb_identifier = __get_adb_identifier(device, connection)
    os.system(f"adb -s {adb_identifier} reboot -p")


def reboot_device(device, connection):

    adb_identifier = __get_adb_identifier(device, connection)
    os.system(f"adb -s {adb_identifier} reboot")


def get_device_traffic(device, connection):

    if device["os"] != "Android":
        return 0, 0

    adb_identifier = __get_adb_identifier(device, connection)
    script = os.path.join(__location__, "../get_data_usage.sh")
    output = os.popen(f"{script} {adb_identifier}").read()
    results = output.split(",")
    rx = int(results[0].split("=")[1])
    tx = int(results[1].split("=")[1])
    return rx, tx


# install Android apk on device
def install_application(device, apk_path):

    adb_identifier = device["adb_identifier"]
    os.system(f"adb -s {adb_identifier} install {apk_path}")


# uninstall Android apk on device
def uninstall_application(device, apk_name):

    adb_identifier = device["adb_identifier"]
    os.system(f"adb -s {adb_identifier} uninstall {apk_name}")


# check if apk exists on device
def apk_exists(device, apk_name):

    adb_identifier = device["adb_identifier"]
    output = os.popen(
        f"adb -s {adb_identifier} shell pm list packages | grep {apk_name}"
    ).read()
    return output != ""


def start_tcpdump(device, filename, interface="any"):

    adb_identifier = device["adb_identifier"]
    os.system(
        f'adb -s {adb_identifier} shell "su -c {TCPDUMP_PATH} -i {interface} ip6 or ip -w {filename}"'
    )


def stop_tcpdump(device):

    adb_identifier = device["adb_identifier"]
    os.system(f'adb -s {adb_identifier} shell "su -c pkill tcpdump"')


def netstat(device, grep_filter=None):

    adb_identifier = device["adb_identifier"]
    command = f'adb -s {adb_identifier} shell "su -c netstat -tup"'

    if grep_filter is not None:
        command += f' | grep {grep_filter}"'

    output = os.popen(command).read()
    return output


def ss(device, grep_filter=None):

    adb_identifier = device["adb_identifier"]
    command = f'adb -s {adb_identifier} shell "su -c ss -tup"'

    if grep_filter is not None:
        command += f' | grep {grep_filter}"'

    output = os.popen(command).read()
    return output


def proc_net(device, socket):

    if socket not in ["tcp", "tcp6", "udp", "udp6"]:
        blade_logger.logger.error(f"Error: Invalid socket type: {socket}")
        raise Exception(f"Error: Invalid socket type: {socket}")

    adb_identifier = device["adb_identifier"]
    output = os.popen(
        f'adb -s {adb_identifier} shell "su -c cat /proc/net/{socket}"'
    ).read()
    return output

def get_user_id(device, connection, package_name):

    adb_identifier = __get_adb_identifier(device, connection)
    output = os.popen(
        f'adb -s {adb_identifier} shell dumpsys package {package_name} | grep userId='
    ).read()

    if output == "":
        return None

    # Chrome returns multiple lines here, split into lines and get first valid appId
    for line in output.splitlines():
        if '=' in line:
            return line.split('=')[1].strip()

    return None

def get_data_usage(device, connection, package_name):

    app_id = get_user_id(device, connection, package_name)
    if app_id is None:
        blade_logger.logger.warning(f"Warning: Could not find app_id for package '{package_name}', might have not been opened since boot. Reporting (0, 0).")
        return 0, 0
    
    adb_identifier = __get_adb_identifier(device, connection)
    script = os.path.join(__location__, "../get_data_usage_per_app.sh")
    with Popen(
        [script, adb_identifier, app_id], stdout=PIPE, stderr=PIPE
    ) as process:
        output, error = process.communicate()
        if error or process.returncode != 0:
            blade_logger.logger.warning(f"Warning: Could not get data usage for package '{package_name}'. Reporting 0 for all relevant metrics.")
            rx, tx = 0, 0

        else:
            results = output.decode().split(",")
            rx = int(results[0].split("=")[1])
            tx = int(results[1].split("=")[1])
    
    return rx, tx

def lsof(device, pid):

    adb_identifier = device["adb_identifier"]
    output = os.popen(
        f'adb -s {adb_identifier} shell "su -c lsof -p {pid}"').read()
    return output


def pull(device, remote_path, local_path=None):

    adb_identifier = device["adb_identifier"]
    command = f"adb -s {adb_identifier} pull {remote_path}"
    if local_path is not None:
        command += f" {local_path}"
    os.system(command)


def push(device, local_path, remote_path):

    adb_identifier = device["adb_identifier"]
    command = f"adb -s {adb_identifier} push {local_path} {remote_path}"
    os.system(command)


def get_memory_usage(device, connection, package_name):
    """
    Collects memory information for all processes of a package.
    Returns: (total_pss, total_private_dirty, total_private_clean, main_process_rss)
    All values are in kilobytes.
    """

    memory_dict = {
        "accumulated_pss": 0,
        "accumulated_private_dirty": 0,
        "accumulated_private_clean": 0,
        "accumulated_heap_alloc": 0,
        "main_process_rss": 0,
    }
    
    adb_identifier = __get_adb_identifier(device, connection)
    
    # Get all process IDs for the package
    ps_cmd = f'adb -s {adb_identifier} shell "ps -A | grep {package_name}"'
    ps_output = os.popen(ps_cmd).read().strip()
    
    if not ps_output or len(ps_output) == 0:
        blade_logger.logger.warning(f"Warning: Could not get memory usage for package '{package_name}'. Reporting 0 for all relevant metrics.")
        return memory_dict
    
    # Process each line from ps output
    for line in ps_output.splitlines():
        parts = line.split()
        if len(parts) < 9:  # ps output should have at least 9 columns
            continue
            
        pid = parts[1]
        process_name = parts[8]
        is_main_process = process_name == package_name
        
        # Run dumpsys meminfo for this PID
        meminfo_cmd = f'adb -s {adb_identifier} shell dumpsys meminfo {pid}'
        meminfo_output = os.popen(meminfo_cmd).read()
        
        # Parse the TOTAL line
        for line in meminfo_output.splitlines():
            if line.strip().startswith('TOTAL'):
                parts = line.split()
                if len(parts) == 9:  # Ensure output format is correct
                    try:
                        pss = int(parts[1])
                        private_dirty = int(parts[2])
                        private_clean = int(parts[3])
                        rss = int(parts[5])
                        heap_alloc = int(parts[7])
                        
                        memory_dict["accumulated_pss"] += pss
                        memory_dict["accumulated_private_dirty"] += private_dirty
                        memory_dict["accumulated_private_clean"] += private_clean
                        memory_dict["accumulated_heap_alloc"] += heap_alloc
                        if is_main_process:
                            memory_dict["main_process_rss"] = rss
                            
                    except (IndexError, ValueError):
                        blade_logger.logger.warning(f"Warning: error parsing meminfo output for PID {pid}")
                        continue
                break

    return memory_dict
