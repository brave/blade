# Note:   Useful ADB-related functions for controlling Android devices
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   04/03/2023

import subprocess
import sys
import time
import urllib.parse
import shlex
from ast import literal_eval

from libs import tools
from libs import constants
from libs import logger as blade_logger


# returns adb identifier base don the connection type
def __get_adb_identifier(device, connection, port=constants.ADB_OVER_WIFI_DEFAULT_PORT):

    if connection == "usb":
        return device["adb_identifier"]

    if connection == "wifi":
        return f"{device['ip']}:{port}"

    blade_logger.logger.error(f"Error: Unknown connection '{connection}'.")
    raise Exception(f"Error: Unknown connection '{connection}'.")


# execute an adb command to the device ('adb -s <device_id> ' prefix is included automatically)
def run_adb_command(device, connection, command, min_duration=None):

    adb_identifier = __get_adb_identifier(device, connection)
    command = f"adb -s {adb_identifier} {command}"
    print(f"\t{command}", flush=True)

    # run the command
    start_time = time.time()
    output = subprocess.check_output(command, shell=True).rstrip().decode()

    # guarantee that the command will run for at least min_duration seconds
    elapsed_time = time.time() - start_time
    if min_duration:
        if elapsed_time < min_duration:
            time.sleep(min_duration - elapsed_time)
        else:
            blade_logger.logger.warning(f"Warning: Command '{command}' took longer than expected ({elapsed_time} sec).")

    return output


# execute an adb shell su command to the device ('adb -s <device_id> shell su -c ' prefix is included automatically). Requires root access.
def run_adb_shell_su_command(device, connection, command):
    command = f"shell su -c '{command}'"
    return run_adb_command(device, connection, command)


def type_text(device, connection, text):
    run_adb_command(device, connection, f"shell input text {text}")


# simulates a key press event
def press_key(device, connection, key):
    run_adb_command(device, connection, f"shell input keyevent {key}")


# tap at x, y coordinates
def tap_screen(device, connection, x, y):
    run_adb_command(device, connection, f"shell input tap {x} {y}")


# long tap at x, y coordinates (uses swipe command)
def long_tap_screen(device, connection, x, y):
    swipe_screen(device, connection, x, y, x, y, duration=2000)


# swipe from (x, y) to (x, y) coordinates, with a duration in milliseconds
def swipe_screen(device, connection, from_x, from_y, to_x, to_y, duration=1000, min_duration=None):
    run_adb_command(
        device,
        connection,
        f"shell input swipe {from_x} {from_y} {to_x} {to_y} {duration}",
        min_duration=min_duration
    )


def roll(device, connection, dx, dy, min_duration=None):
    run_adb_command(device, connection, f"shell input roll {dx} {dy}", min_duration=min_duration)


# simulate a scroll up or down gesture
def scroll(device, connection, direction, length=1200, duration=1000, min_duration=None):

    if direction == "up":
        from_y = 600
        to_y = from_y + length

    elif direction == "down":
        from_y = 1800
        to_y = from_y - length

    else:
        blade_logger.logger.error(f"Error: Unsupported scroll direction.")
        raise Exception(f"Error: Unsupported scroll direction.")

    swipe_screen(device, connection, 500, from_y, 500, to_y, duration, min_duration=min_duration)


# get the current battery info (e.g. level, status, etc.)
def get_battery_details(device, connection):
    result = run_adb_command(device, connection, "shell dumpsys battery")

    # Parse the output
    battery_info = {}
    for line in result.splitlines()[1:]:
        if ":" in line:
            key, value = line.split(":", 1)

            battery_info[key.strip()] = __simplest_type(value.strip())

    # add battery level ratio
    battery_level_ratio = battery_info["level"] / battery_info["scale"]
    battery_info["level_ratio"] = battery_level_ratio
    
    return battery_info


def __simplest_type(s):
    try:
        return literal_eval(s)
    except:
        return s


# returns foreground application
def get_foreground_app(device, connection):

    app = run_adb_command(
        device,
        connection,
        "shell dumpsys activity activities | grep -E 'mCurrentFocus' | cut -d '/' -f1 | sed 's/.* //g'",
    )
    return app


# returns device model
def get_device_model(device, connection):
    return run_adb_command(device, connection, "shell getprop ro.product.model")


# start an activity
def start_activity(device, connection, package, activity, min_duration=None):
    run_adb_command(device, connection,
                    f"shell am start -n {package}/{activity}",
                    min_duration=min_duration)


# open app on MAIN activity
def open_app(device, connection, package, min_duration=None):
    run_adb_command(device, connection,
                    f"shell monkey -p {package} -c android.intent.category.LAUNCHER 1",
                    min_duration=min_duration)


# clear app data
def clear_app_data(device, connection, package, min_duration=None):
    run_adb_command(device, connection,
                    f"shell pm clear {package}",
                    min_duration=min_duration)


# force stop an application
def close_app(device, connection, package, min_duration=None):
    run_adb_command(
        device,
        connection,
        f"shell am force-stop {package}",
        min_duration=min_duration
    )
    

def save_app_profile(device, connection, package, filename):

    # if file exists, delete it
    run_adb_shell_su_command(device, connection,
                             f"rm -f /data/local/tmp/{filename}")
    
    # tar app data from /data/data/$app_package
    run_adb_shell_su_command(device, connection,
                             f"tar -czvf /data/local/tmp/{filename} -C /data/data/{package} .")


def restore_app_profile(device, connection, package, filename):

    # check if file exists
    output = run_adb_shell_su_command(device, connection,
                                           f"ls /data/local/tmp/{filename}").strip()
    
    # TODO: change into a more robust check, in a new function
    if "No such file or directory" in output:
        blade_logger.logger.error(f"Error: File /data/local/tmp/'{filename}' does not exist.")
        raise Exception(f"Error: File /data/local/tmp/'{filename}' does not exist.")
    
    # clear first
    clear_app_data(device, connection, package)
    time.sleep(constants.ADB_COMMANDS_EXTENDED_EXECUTION_TIMEOUT)

    # Restore app data from the backup file
    run_adb_shell_su_command(device, connection,
                             f"tar -xzvf /data/local/tmp/{filename} -C /data/data/{package}")


# take a screenshot and store it into a local file
def take_screenshot(device, connection, filename):
    run_adb_command(device, connection,
                    f"shell screencap -p /sdcard/screenshot.png")
    run_adb_command(device, connection,
                    f"pull /sdcard/screenshot.png {filename}")
    run_adb_command(device, connection, f"shell rm /sdcard/screenshot.png")


# open a url on an activity (e.g. browser)
def open_url_on_activity(device, connection, package, activity, url, min_duration=None):

    # add https:// prefix if needed
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    # Escape any double quotes in the URL to prevent breaking the command's quoting
    url = url.replace('"', '\\"')
    
    # open url
    run_adb_command(
        device,
        connection,
        f"shell 'am start -a android.intent.action.VIEW -n {package}/{activity} -d \"{url}\"'",
        min_duration=min_duration
    )


# setup device for the experiment: disable notifications, disable screen timeout, etc.
def setup_device(device, connection):

    # disable notifications
    run_adb_command(
        device, connection, "shell settings put global heads_up_notifications_enabled 0"
    )

    # disable screen timeout
    default_screen_timeout = 2147483647
    run_adb_command(
        device,
        connection,
        f"shell settings put system screen_off_timeout {default_screen_timeout}",
    )


# cleanup device after the experiment: re-enable notifications, restore screen timeout, etc.
def cleanup_device(device, connection):

    # re-enable notifications
    run_adb_command(
        device, connection, "shell settings put global heads_up_notifications_enabled 1"
    )

    # restore screen timeout
    default_screen_timeout = 30000
    run_adb_command(
        device,
        connection,
        f"shell settings put system screen_off_timeout {default_screen_timeout}",
    )


# set device brightness level (0-255)
def set_brightness(device, connection, brightness):

    # check that brightness is in the right range
    if brightness < 0:
        blade_logger.logger.warning(
            f"Warning: Wrong brightness value '{brightness}'. Should be in the range [0, 255]. Setting it to minimum (0)."
        )
        brightness = 0

    elif brightness > 255:
        blade_logger.logger.warning(
            f"Warning: Wrong brightness value '{brightness}'. Should be in the range [0, 255]. Setting it to maximum (255)."
        )
        brightness = 255

    run_adb_command(
        device, connection, f"shell settings put system screen_brightness {brightness}"
    )


# switch screen on/off
def switch_screen(device, connection, state):

    # get current screen state
    current_state = get_screen_state(device, connection)

    # switch screen if needed
    if state != current_state:
        press_key(device, connection, "KEYCODE_POWER")


# returns screen state ('on' or 'off')
def get_screen_state(device, connection):

    # get current screen state
    current_state = run_adb_command(
        device,
        connection,
        "shell dumpsys display | grep 'mScreenState' | cut -d '=' -f2 | sed 's/ //g'",
    )

    if current_state == "ON":
        return "on"
    elif current_state == "OFF":
        return "off"
    else:
        blade_logger.logger.warning(f"Warning: Unknown screen state '{current_state}'.")


# returns screen state ('on_locked' or 'off_locked' or 'on_unlocked')
# requires a device with NFC enabled
def get_screen_lock_state(device, connection):

    # get current screen state
    current_state = run_adb_command(
        device,
        connection,
        "shell dumpsys nfc | grep 'mScreenState=' | cut -d '=' -f2 | sed 's/ //g'",
    )

    if current_state == "ON_LOCKED":
        return "on_locked"
    elif current_state == "OFF_LOCKED":
        return "off_locked"
    elif current_state == "ON_UNLOCKED":
        return "on_unlocked"
    else:
        blade_logger.logger.warning(f"Warning: Unknown screen lock state '{current_state}'.")


# returns the app_package of the current focus application
def get_current_focus(device, connection):
    return run_adb_command(device, connection, "shell dumpsys window displays | grep -E mCurrentFocus | cut -d '/' -f1 | sed 's/.* //g'")


# press power button
def power_button(device, connection):
    press_key(device, connection, "KEYCODE_POWER")


# unlock device
def unlock_device(device, connection):
    switch_screen(device, connection, "on")
    time.sleep(constants.ADB_COMMANDS_EXECUTION_TIMEOUT)
    press_key(device, connection, "KEYCODE_MENU")
    time.sleep(constants.ADB_COMMANDS_EXECUTION_TIMEOUT)


def enable_proxy(device, connection, port=constants.PROXY_DEFAULT_SERVER_PORT):

    # get Pi's local IP address
    local_ip = tools.get_local_ip()

    run_adb_command(
        device, connection, f"shell settings put global http_proxy {local_ip}:{port}"
    )


def disable_proxy(device, connection):

    run_adb_command(
        device, connection, "shell settings put global http_proxy :0"
    )


def change_orientation(device, connection, orientation):

    if orientation == "portrait":
        run_adb_command(device, connection, "shell settings put system user_rotation 0")

    elif orientation == "landscape":
        run_adb_command(device, connection, "shell settings put system user_rotation 1")

    else:
        blade_logger.logger.error(f"Error: Unsupported orientation '{orientation}'.")
        raise Exception(f"Error: Unsupported orientation '{orientation}'.")
