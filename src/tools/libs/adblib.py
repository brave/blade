# Note:   Useful ADB-related functions for controlling Android devices
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   04/03/2023

import os
import sys
import time
from subprocess import PIPE, Popen

# get current file path
__location__ = os.path.dirname(os.path.realpath(__file__))
TCPDUMP_PATH = "/data/local/tmp/tcpdump"


# returns adb identifier base don the connection type
def __get_adb_identifier(device, connection, port=5555):

    if connection == "usb":
        return device["adb_identifier"]

    if connection == "wifi":
        return f"{device['ip']}:{port}"

    sys.exit(f"Error: Unknown connection '{connection}'.")


# enable adb over wifi (default port is 5555)
def enable_adb_over_wifi(device, port=5555):

    adb_identifier = device["adb_identifier"]
    ip = device["ip"]

    # enable adb over wifi
    os.system(f"adb -s {adb_identifier} tcpip {port}")
    time.sleep(1)

    # disconnect and reconnect over wifi, ignoring the expected error
    with Popen(
        ["adb", "disconnect", "{ip}:{port}"], stdout=PIPE, stderr=PIPE
    ) as process:
        output, _ = process.communicate()
        if output:
            print(output)
    time.sleep(2)

    os.system(f"adb connect {ip}:{port}")
    time.sleep(1)


# disable adb over wifi (default port is 5555)
def disable_adb_over_wifi(device, port=5555):

    ip = device["ip"]

    # disable adb over wifi
    os.system(f"adb disconnect {ip}:{port}")
    time.sleep(1)


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
        raise Exception(f"Invalid socket type: {socket}")

    adb_identifier = device["adb_identifier"]
    output = os.popen(
        f'adb -s {adb_identifier} shell "su -c cat /proc/net/{socket}"'
    ).read()
    return output


def get_process_id(device, package_name):

    adb_identifier = device["adb_identifier"]
    output = os.popen(
        f'adb -s {adb_identifier} shell dumpsys package {package_name} | grep userId="'
    ).read()

    if output == "":
        return None

    output = output.split("=")
    if len(output) < 2:
        return None

    return output[1]


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
