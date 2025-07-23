# Note:   Control BLaDE device automations
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   17/02/2023

import json
import os
import subprocess
import time

from libs import tools
from libs import adblib
from libs import monsoonlib
from libs import usblib
from libs import volswitchlib
from libs import devicerechargelib
from libs.automation import adb_commands

from libs import async_calls as acalls
from libs import constants
from libs import logger as blade_logger

# get current file path
__location__ = os.path.dirname(os.path.realpath(__file__))

# read device configuration file
devices_config_path = os.path.join(__location__, "../configs", "devices.json")
with open(devices_config_path, encoding="utf-8") as f:
    devices = json.load(f)


def get_devices():
    return devices


def switch(device, state, auto_recharge_battery_level=None):
    
    # check auto-recharge battery level
    if auto_recharge_battery_level is not None and (auto_recharge_battery_level < 0.00 or auto_recharge_battery_level > 1.00):
        blade_logger.logger.error(f"Error: Auto-recharge battery level must be between 0.00 and 1.00")
        raise Exception(f"Error: Auto-recharge battery level must be between 0.00 and 1.00")

    # init libs
    monsoon = monsoonlib.Monsoon()
    vs = volswitchlib.VoltageSwitch()
    usb_control = usblib.USBControl(device["usb"])

    # get properties
    monsoon_info = device.get("monsoon")
    if monsoon_info is None:
        blade_logger.logger.error("Error: Device doesn't have a Monsoon configuration.")
        raise Exception("Error: Device doesn't have a Monsoon configuration.")
    channel = monsoon_info["channel"]

    if state == "on":

        # check if all devices are off
        if not vs.is_all_channels_off():
            blade_logger.logger.error("Error: All devices must be switched off before switching to a new device.")
            raise Exception("Error: All devices must be switched off before switching to a new device.")

        # switch monsoon on
        monsoon.switch("on")

        # check if device is available
        if not monsoon.wait_for_device_availability():
            blade_logger.logger.error("Error: Monsoon is not available.")
            raise Exception("Error: Monsoon is not available.")

        # connect to monsoon
        if not monsoon.connect():
            blade_logger.logger.error("Error: Could not connect to Monsoon")
            raise Exception("Error: Could not connect to Monsoon")

        # enable device's USB
        usb_control.set_state("enabled")

        # switch voltage to the device
        vs.switch_to(channel)
        time.sleep(constants.CONTROL_DEVICE_DEFAULT_WAIT_TIME)

        # set voltage to the device
        voltage = monsoon_info["voltage"]
        monsoon.set_voltage(voltage)
        monsoon.disconnect()

        # wait for device to become available
        if not usb_control.wait_for_device_availability():
            blade_logger.logger.error("Error: Device is not available.")
            raise Exception("Error: Device is not available.")
        time.sleep(constants.CONTROL_DEVICE_DEVICE_AVAILABLE_WAIT_TIME)  # Extra time needed atop of the above

        # report battery level at boot
        if device["os"] == "Android":
            battery_details = adb_commands.get_battery_details(device, connection="usb")
            battery_level_ratio = battery_details["level_ratio"]
            blade_logger.logger.info(f"Device battery level is at {battery_level_ratio:.2f}.")

        # auto-recharge if needed
        if device["os"] == "Android" and auto_recharge_battery_level is not None:
            devicerechargelib.await_until_device_reaches_battery_level(device, auto_recharge_battery_level)

        # sync time for iOS (Android only possible for rooted devices)
        if device["os"] == "iOS":
            blade_logger.logger.info("Syncing device time with Pi...")
            subprocess.run("idevicedate -c", shell=True, check=True, text=True)
            time.sleep(constants.CONTROL_DEVICE_DEFAULT_WAIT_TIME)

        # if iOS, unlock device to authorize USB connection
        if device["os"] == "iOS":

            # bt connect
            acalls.connect_to_bt_device(device["bt_mac_address"])
            time.sleep(constants.CONTROL_DEVICE_DEFAULT_WAIT_TIME)

            # screen unlock
            change_screen_lock(device, "unlock")
            time.sleep(constants.CONTROL_DEVICE_DEFAULT_WAIT_TIME)

            # lock again
            change_screen_lock(device, "lock")
            time.sleep(constants.CONTROL_DEVICE_DEFAULT_WAIT_TIME)

            # bt disconnect
            acalls.disconnect_from_bt_device()

        # done
        blade_logger.logger.info("Device is ready.")
        return

    if state == "off":

        # check if already on
        if vs.read_state(channel) == "off":
            blade_logger.logger.warning("Warning: Device appears to be 'off' already.")

        # kill all 'collect_', and other related processes, in case they are still running
        os.system("pkill -f collect_")
        os.system("pkill -f mitmdump")
        os.system("pkill -f pageload-server.py")
        os.system("pkill -f control-monsoon.py")

        # kill related processes for remote control (if alive)
        if device["os"] == "Android":
            disable_remote_control()

        # disable adb-over-wifi if needed
        if device["os"] == "Android":
            adb_connection_state = adblib.get_device_adb_connection_state(device)
            if adb_connection_state == "wifi":
                adblib.disable_adb_over_wifi(device)
                time.sleep(constants.CONTROL_DEVICE_DEFAULT_WAIT_TIME)
            elif adb_connection_state == None:
                blade_logger.logger.warning("Warning: Device is not connected via ADB.")
        
        # power off device
        if device["os"] == "Android":
            blade_logger.logger.info("Powering off device...")
            adblib.power_off_device(device, connection="usb")
            time.sleep(constants.CONTROL_DEVICE_POWER_OFF_WAIT_TIME)

        # disable USB
        if usb_control.get_state() == "enabled":
            usb_control.set_state("disabled")

        # check if device is available
        if monsoon.read_state() == "on" and monsoon.is_available():

            try:
                # set voltage to 0 and disconnect
                monsoon.connect()
                monsoon.set_voltage(0)
                monsoon.disconnect()
                time.sleep(constants.CONTROL_DEVICE_DEFAULT_WAIT_TIME)

            except Exception as e:
                blade_logger.logger.warning(f"Warning: {e}")

        # switch to device using GPIO
        vs.switch_off(channel)

        # switch monsoon off
        monsoon.switch("off")

        # done
        return

    blade_logger.logger.error(f"Error: Unknown state: '{state}'")
    raise Exception(f"Error: Unknown state: '{state}'")


def change_screen_lock(device, screen_lock_state):

    # TODO: right now it relies on being in measuring mode (since BT is only available then). Fix is required.

    # check state first
    if read_state(device) == "off":
        blade_logger.logger.error("Error: Device is off.")
        raise Exception("Error: Device is off.")

    # init device
    if device["os"] == "Android":
        blade_logger.logger.error("Error: Changing the device lock state is only supported for iOS devices for now.")
        raise Exception("Error: Changing the device lock state is only supported for iOS devices for now.")

    elif device["os"] == "iOS":

        # TODO: dirty. Should be at toplevel (though causing BT issues if iOS device not available. Needs fix)
        from automation import bt_ios_commands

        if screen_lock_state == "lock":
            bt_ios_commands.lock_device(device)

        elif screen_lock_state == "unlock":
            bt_ios_commands.unlock_device(device)

        else:
            blade_logger.logger.error(f"Error: Unknown screen lock state: '{screen_lock_state}'")
            raise Exception(f"Error: Unknown screen lock state: '{screen_lock_state}'")

    else:
        blade_logger.logger.error(f"Error: Device has unknown OS: '{device['os']}'")
        raise Exception(f"Error: Device has unknown OS: '{device['os']}'")


def read_state(device):
    vs = volswitchlib.VoltageSwitch()
    channel = device["monsoon"]["channel"]
    return vs.read_state(channel)


def start_measuring(device, output_path, auto_recharge_battery_level=None, granularity=1):
    
    # check granularity
    if granularity < 1 or granularity > constants.MONSOON_COLLECTED_SAMPLES_PER_BATCH:
        blade_logger.logger.error(f"Error: Granularity must be between 1 and {constants.MONSOON_COLLECTED_SAMPLES_PER_BATCH}")
        raise Exception(f"Error: Granularity must be between 1 and {constants.MONSOON_COLLECTED_SAMPLES_PER_BATCH}")
    
    # check auto-recharge battery level
    if auto_recharge_battery_level is not None and (auto_recharge_battery_level < 0.00 or auto_recharge_battery_level > 1.00):
        blade_logger.logger.error(f"Error: Auto-recharge battery level must be between 0.00 and 1.00")
        raise Exception(f"Error: Auto-recharge battery level must be between 0.00 and 1.00")

    # ensure output path exists
    tools.ensure_path(output_path)

    # check state first
    if read_state(device) == "off":
        blade_logger.logger.error("Error: Device is off.")
        raise Exception("Error: Device is off.")

    # check if device is available
    usb_control = usblib.USBControl(device["usb"])
    if not usb_control.is_device_available():
        blade_logger.logger.error("Error: Device doesn't appear to be available.")
        raise Exception("Error: Device doesn't appear to be available.")
    
    # auto-recharge if needed
    if device["os"] == "Android" and auto_recharge_battery_level is not None:
        devicerechargelib.await_until_device_reaches_battery_level(device, auto_recharge_battery_level)

    # init device
    if device["os"] == "Android":
        adblib.enable_adb_over_wifi(device)
        time.sleep(constants.SWITCH_ADB_CONNECTION_STATE_TIMEOUT)

        adb_identifier = f"{device['ip']}:{constants.ADB_OVER_WIFI_DEFAULT_PORT}"

        # SW-based measuring using ADB
        sw_power_enabled = True
        output_file = os.path.join(output_path, "measurements_adb.csv")
        acalls.collect_adb_measurements(
            adb_identifier, constants.ADB_MEASUREMENTS_DEFAULT_SAMPLE_DELAY, sw_power_enabled, output_file
        )
        time.sleep(constants.CONTROL_DEVICE_DEFAULT_WAIT_TIME)

    elif device["os"] == "iOS":
        pass

    else:
        blade_logger.logger.error(f"Error: Device has unknown OS: '{device['os']}'")
        raise Exception(f"Error: Device has unknown OS: '{device['os']}'")

    # disable USB
    usb_control.set_state("disabled")
    time.sleep(constants.CONTROL_DEVICE_DEFAULT_WAIT_TIME)

    # HW-based measuring using Monsoon (if available)
    monsoon_info = device.get("monsoon")
    if monsoon_info is None:
        blade_logger.logger.warning(
            "Warning: Device doesn't have a Monsoon configuration. Skipping HW-based measurements."
        )

    else:
        # start collecting with monsoon (async)
        output_file = os.path.join(output_path, "measurements_monsoon.csv")
        acalls.collect_monsoon_measurements(output_file, granularity=granularity)
        time.sleep(constants.CONTROL_DEVICE_WAIT_TIME_AFTER_ASYNC_CALLS)


def stop_measuring(device):

    # check state first
    if read_state(device) == "off":
        blade_logger.logger.error("Error: Device is off.")
        raise Exception("Error: Device is off.")

    # Stop HW-based measuring using Monsoon (if available)
    monsoon_info = device.get("monsoon")
    if monsoon_info is None:
       blade_logger.logger.warning("Warning: Device doesn't have a Monsoon configuration. Skipping stopping HW-based measurements.")

    else:
        # stop measuring with monsoon (async)
        acalls.stop_collecting_monsoon_measurements()

    # re-enable USB
    usb_control = usblib.USBControl(device["usb"])
    usb_control.set_state("enabled")
    time.sleep(constants.CONTROL_DEVICE_DEFAULT_WAIT_TIME)

    # restore device state
    if device["os"] == "Android":

        # stop SW-based measuring using ADB
        acalls.stop_collecting_adb_measurements()
        time.sleep(constants.CONTROL_DEVICE_DEFAULT_WAIT_TIME)

        # disable adb-over-wifi
        adblib.disable_adb_over_wifi(device)
        time.sleep(constants.CONTROL_DEVICE_DEFAULT_WAIT_TIME)

    elif device["os"] == "iOS":
        pass

    else:
       blade_logger.logger.error(f"Error: Device has unknown OS: '{device['os']}'")
       raise Exception(f"Error: Device has unknown OS: '{device['os']}'")


def connect_to_bt_device(device):
    acalls.connect_to_bt_device(device["bt_mac_address"])


def disconnect_from_bt_device():
    acalls.disconnect_from_bt_device()


def enable_remote_control(device):

    if device["os"] != "Android":
        blade_logger.logger.error("Error: Remote control is only supported for Android devices.")
        raise Exception("Error: Remote control is only supported for Android devices.")

    # TODO: This relies on USB-based device-id. Fix is required to support measuring mode over WiFi.
    device_id = device["adb_identifier"]
    acalls.enable_remote_control(device_id)

    current_ip = tools.get_local_ip()
    blade_logger.logger.info(f"Remote control enabled at http://{current_ip}:6080/vnc.html")


def disable_remote_control():
    acalls.disable_remote_control()
