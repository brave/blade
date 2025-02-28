# Note:   Useful external async calls for measuring performance
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   09/03/2023

import os
import signal
import subprocess
import time
import socket
from pathlib import Path

from libs import tools
from libs import constants
from libs import logger as blade_logger

# get current file path
__location__ = os.path.dirname(os.path.realpath(__file__))


# start collecting adb measurements
def collect_adb_measurements(adb_identifier, sleep_time, sw_power_enabled, output_file):

    # collect measurements
    script = os.path.join(__location__, "../collect_adb_measurements.sh")
    process = subprocess.Popen(
        [
            script,
            adb_identifier,
            str(sleep_time),
            str(int(sw_power_enabled)),
            output_file,
        ]
    )

    # save pid to file
    filename = ".adb_measurements_pid"
    tools.save_value_to_file(process.pid, filename)


# stop collecting adb measurements
def stop_collecting_adb_measurements():

    pid = tools.read_value_from_file(".adb_measurements_pid")
    if pid:

        try:
            os.kill(int(pid), signal.SIGKILL)
        except OSError:
            blade_logger.logger.warning("Warning: Could not stop adb measurements. Process already stopped.")


def collect_memory_measurements(adb_identifier, app_package, output_file, interval_ms=constants.ONE_SECOND*1000):

    # collect measurements
    script = os.path.join(__location__, "../collect_memory_measurements.py")
    process = subprocess.Popen(
        [
            script,
            adb_identifier,
            app_package,
            output_file,
            f"--interval={interval_ms}",
        ]
    )

    # save pid to file
    filename = ".memory_measurements_pid"
    tools.save_value_to_file(process.pid, filename)

    
def stop_memory_measurements():
    pid = tools.read_value_from_file(".memory_measurements_pid")
    if pid:

        try:
            os.kill(int(pid), signal.SIGINT)
        except OSError:
            blade_logger.logger.warning(
                "Warning: Could not stop memory measurements. Process already stopped."
            )


# start collecting monsoon measurements
def collect_monsoon_measurements(output_file):

    # collect measurements
    script = os.path.join(__location__, "../control-monsoon.py")
    process = subprocess.Popen(
        [script, "--collect-measurements", "--output", output_file]
    )

    # save pid to file
    filename = ".monsoon_measurements_pid"
    tools.save_value_to_file(process.pid, filename)


# stop collecting monsoon measurements
def stop_collecting_monsoon_measurements():

    pid = tools.read_value_from_file(".monsoon_measurements_pid")
    if pid:

        try:
            os.kill(int(pid), signal.SIGINT)
        except OSError:
            blade_logger.logger.warning(
                "Warning: Could not stop monsoon measurements. Process already stopped."
            )


# connect to a Bluetooth device
def connect_to_bt_device(bt_mac_address):

    # collect measurements
    script = os.path.join(__location__, "../bt-connect.py")
    process = subprocess.Popen(["sudo", script, "--device", bt_mac_address])
    time.sleep(constants.FIVE_SECONDS)

    # save pid to file
    filename = ".bt-connect_pid"
    tools.save_value_to_file(process.pid, filename)


# disconnect from a Bluetooth device
def disconnect_from_bt_device():

    pid = tools.read_value_from_file(".bt-connect_pid")
    if pid:

        try:
            os.kill(int(pid), signal.SIGINT)
        except OSError:
            blade_logger.logger.warning(
                "Warning: Could not disconnect from Bluetooth device. Process already stopped."
            )
    time.sleep(constants.FIVE_SECONDS)

# enable remote control through NoVNC web interface
def enable_remote_control(device_id):
    
    script = os.path.join(__location__, "../enable_remote_control.sh")
    subprocess.Popen([script, device_id])
    time.sleep(constants.FIVE_SECONDS)


# disable remote control through NoVNC web interface
def disable_remote_control():

    script = os.path.join(__location__, "../disable_remote_control.sh")
    os.system(script)
    time.sleep(constants.ONE_SECOND)

def start_pageload_proxy(browser_name, server_ip=None, port=8443, verbose=False):
    """Start mitmproxy with inject script for specific browser
    
    Args:
        browser_name: Name of the browser being tested
        server_ip: Optional IP address for the server (default: auto-detect)
        port: Port number for the server (default: 8443)
    """

    # Set environment variables for the inject script
    os.environ["BROWSER_NAME"] = browser_name
    os.environ["SERVER_IP"] = server_ip or tools.get_local_ip()
    os.environ["SERVER_PORT"] = str(port)
    
    # Start mitmproxy with inject script
    blade_logger.logger.info("Starting mitmdump with parameters:")
    blade_logger.logger.info("BROWSER_NAME: %s", os.environ.get("BROWSER_NAME"))
    blade_logger.logger.info("SERVER_IP: %s", os.environ.get("SERVER_IP"))
    blade_logger.logger.info("SERVER_PORT: %s", os.environ.get("SERVER_PORT"))
    inject_script = os.path.join(__location__, "../pageload-inject.py")

    command = [
            "mitmdump",
            "-s", inject_script,
            "--ssl-insecure"
        ]
    if not verbose:
        command.append("-q")
    process = subprocess.Popen(command)

    # Save pid to file
    filename = ".pageload_proxy_pid"
    tools.save_value_to_file(process.pid, filename)

def stop_pageload_proxy():
    """Stop the mitmproxy process"""
    pid = tools.read_value_from_file(".pageload_proxy_pid")
    if pid:
        try:
            os.kill(int(pid), signal.SIGTERM)
        except OSError:
            blade_logger.logger.warning("Warning: Could not stop pageload proxy. Process already stopped.")

def start_pageload_server(output_dir, port=8443):
    """Start the HTTPS server for collecting measurements"""
    server_script = os.path.join(__location__, "../pageload-server.py")
    process = subprocess.Popen([
        "python3", server_script,
        "--port", str(port),
        "--cert", "cert.pem",
        "--key", "key.pem",
        "--output", output_dir,
    ])

    # Save pid to file
    filename = ".pageload_server_pid"
    tools.save_value_to_file(process.pid, filename)

def stop_pageload_server():
    """Stop the pageload server and collect results"""
    pid = tools.read_value_from_file(".pageload_server_pid")
    if pid:
        try:
            os.kill(int(pid), signal.SIGTERM)
                
        except OSError:
            blade_logger.logger.warning("Warning: Could not stop pageload server. Process already stopped.")
