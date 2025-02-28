# Note:   Useful ADB-related functions for controlling Android devices
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   04/03/2023

import subprocess
import sys
import time
import urllib.parse
from ast import literal_eval

from libs import tools
from libs import constants
from libs import logger as blade_logger

browser_settings = {
    "Chrome": {
    },
}


# returns adb identifier base don the connection type
def __get_adb_identifier(device, connection, port=5555):

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
    time.sleep(constants.TWO_SECONDS)

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

    # escape url
    url = url.replace("&", "\\&")

    # open url
    run_adb_command(
        device,
        connection,
        f"shell am start -a android.intent.action.VIEW -d '{url}' {package}/{activity}",
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
    time.sleep(constants.ONE_SECOND)
    press_key(device, connection, "KEYCODE_MENU")


# close all running applications
def close_all(device, connection):

    press_key(device, connection, "KEYCODE_APP_SWITCH")
    time.sleep(constants.ONE_SECOND)

    if device["type"] in ["Google Pixel 6a"]:

        swipe_screen(device, connection, 445, 1270, 940, 1270)
        time.sleep(constants.ONE_SECOND)

        tap_screen(device, connection, 229, 1209)
        time.sleep(constants.FIVE_SECONDS)

    elif device["type"] in ["Samsung Galaxy S23"]:

        tap_screen(device, connection, 530, 1820)
        time.sleep(constants.FIVE_SECONDS)

    else:
        blade_logger.logger.warning("WARNING: Unsupported device type")


# open a particular browser
def open_browser(device, connection, browser):

    if browser == "Chrome":
        start_activity(
            device,
            connection,
            "com.android.chrome",
            "com.google.android.apps.chrome.Main",
        )

    elif browser == "Brave":
        start_activity(
            device,
            connection,
            "com.brave.browser",
            "com.google.android.apps.chrome.Main",
        )

    elif browser == "Firefox":
        start_activity(
            device,
            connection,
            "org.mozilla.firefox",
            "org.mozilla.gecko.BrowserApp"
        )

    elif browser == "Firefox Focus":
        start_activity(
            device,
            connection,
            "org.mozilla.focus",
            "org.mozilla.focus.activity.MainActivity",
        )

    elif browser == "Edge":
        start_activity(
            device,
            connection,
            "com.microsoft.emmx",
            "com.microsoft.ruby.Main"
        )

    elif browser == "DuckDuckGo":
        start_activity(
            device,
            connection,
            "com.duckduckgo.mobile.android",
            "com.duckduckgo.app.launch.Launcher",
        )

    elif browser == "Opera":
        start_activity(
            device,
            connection,
            "com.opera.browser",
            "com.opera.Opera"
        )

    elif browser == "Vivaldi":
        start_activity(
            device,
            connection,
            "com.vivaldi.browser",
            "com.google.android.apps.chrome.Main",
        )

    else:
        blade_logger.logger.error(f"Error: Unsupported browser '{browser}'.")
        raise Exception(f"Error: Unsupported browser '{browser}'.")


# open url in a particular browser
def browser_open_url(device, connection, browser, url):

    if browser == "Chrome":
        open_url_on_activity(
            device,
            connection,
            "com.android.chrome",
            "com.google.android.apps.chrome.IntentDispatcher",
            url,
        )

    elif browser == "Brave":
        open_url_on_activity(
            device,
            connection,
            "com.brave.browser",
            "com.google.android.apps.chrome.IntentDispatcher",
            url,
        )

    elif browser == "Firefox":
        open_url_on_activity(
            device,
            connection,
            "org.mozilla.firefox",
            "org.mozilla.gecko.BrowserApp",
            url,
        )

    elif browser == "Firefox Focus":
        open_url_on_activity(
            device,
            connection,
            "org.mozilla.focus",
            ".activity.IntentReceiverActivity",
            url,
        )

    elif browser == "Edge":
        open_url_on_activity(
            device,
            connection,
            "com.microsoft.emmx",
            "com.google.android.apps.chrome.IntentDispatcher",
            url,
        )

    elif browser == "DuckDuckGo":
        # Working, but returns "Warning: Activity not started, intent has been delivered to currently running top-most instance."
        open_url_on_activity(
            device,
            connection,
            "com.duckduckgo.mobile.android",
            "com.duckduckgo.app.browser.BrowserActivity",
            url,
        )

    elif browser == "Opera":
        # Working, but returns "Warning: Activity not started, intent has been delivered to currently running top-most instance."
        open_url_on_activity(
            device,
            connection,
            "com.opera.browser",
            "com.opera.android.BrowserActivity",
            url,
        )

    elif browser == "Vivaldi":
        open_url_on_activity(
            device,
            connection,
            "com.vivaldi.browser",
            "com.google.android.apps.chrome.IntentDispatcher",
            url,
        )

    else:
        raise Exception(f"Error: Unsupported browser '{browser}'.")


# close current tab in a particular browser (assumes it is in the foreground)
def browser_close_tab(device, connection, browser):

    if browser == "Chrome":
        blade_logger.logger.error("Error: Unsupported feature.")

    elif browser == "Brave":
        blade_logger.logger.error("Error: Unsupported feature.")

    elif browser == "Firefox":
        blade_logger.logger.error("Error: Unsupported browser.")

    elif browser == "Firefox Focus":
        blade_logger.logger.error("Error: Unsupported browser.")

    elif browser == "Edge":
        blade_logger.logger.error("Error: Unsupported browser.")

    elif browser == "DuckDuckGo":
        blade_logger.logger.error("Error: Unsupported browser.")

    elif browser == "Opera":
        blade_logger.logger.error("Error: Unsupported browser.")

    elif browser == "Vivaldi":
        blade_logger.logger.error("Error: Unsupported browser.")

    else:
        blade_logger.logger.error(f"Error: Unsupported browser '{browser}'.")
        raise Exception(f"Error: Unsupported browser '{browser}'.")


# close all tabs in a particular browser (assumes it is in the foreground)
def browser_close_all_tabs(device, connection, browser):
    # Note: Duration is identical per browser (8 seconds)

    if browser == "Chrome":

        # click on the tab button
        tap_screen(device, connection, 870, 232)
        time.sleep(constants.ONE_SECOND)

        # click on the options button
        tap_screen(device, connection, 1024, 211)
        time.sleep(constants.ONE_SECOND)

        # tap at the close all button
        tap_screen(device, connection, 735, 481)
        time.sleep(constants.ONE_SECOND)

        # confirm
        tap_screen(device, connection, 830, 1386)
        time.sleep(constants.FIVE_SECONDS)

    elif browser == "Brave":

        # click on the tab button
        tap_screen(device, connection, 756, 2266)
        time.sleep(constants.ONE_SECOND)

        # click on the options button (lower right corner)
        tap_screen(device, connection, 950, 2300)
        time.sleep(constants.ONE_SECOND)

        # tap at the close all button
        tap_screen(device, connection, 650, 1900)
        time.sleep(constants.ONE_SECOND)

        # confirm
        tap_screen(device, connection, 830, 1386)
        time.sleep(constants.FIVE_SECONDS)

    elif browser == "Firefox":

        # click on the tab button
        tap_screen(device, connection, 925, 2272)
        time.sleep(constants.ONE_SECOND)

        # change tab screen into full screen
        swipe_screen(device, connection, 513, 755, 513, 313)
        time.sleep(constants.ONE_SECOND)

        # click on the options button
        tap_screen(device, connection, 1022, 382)
        time.sleep(constants.ONE_SECOND)

        # tap at the close all button
        tap_screen(device, connection, 821, 920)
        time.sleep(constants.FIVE_SECONDS)

    elif browser == "Firefox Focus":

        # tap at the close all button
        tap_screen(device, connection, 54, 236)
        time.sleep(constants.EIGHT_SECONDS)

    elif browser == "Edge":

        # click on the tab button
        tap_screen(device, connection, 785, 2303)
        time.sleep(constants.ONE_SECOND)

        # tap at the close all button
        tap_screen(device, connection, 102, 2247)
        time.sleep(constants.TWO_SECONDS)

        # open new tab so context is the same
        tap_screen(device, connection, 537, 2294)
        time.sleep(constants.FIVE_SECONDS)

    elif browser == "DuckDuckGo":

        # click on the tab button
        tap_screen(device, connection, 925, 225)
        time.sleep(constants.ONE_SECOND)

        # close the last tab
        tap_screen(device, connection, 466, 371)
        time.sleep(constants.TWO_SECONDS)

        # go back to the home screen
        tap_screen(device, connection, 73, 212)
        time.sleep(constants.FIVE_SECONDS)

    elif browser == "Opera":

        # click on the tab button
        tap_screen(device, connection, 767, 2258)
        time.sleep(constants.ONE_SECOND)

        # click on the options button
        tap_screen(device, connection, 990, 2265)
        time.sleep(constants.ONE_SECOND)

        # tap at the close all button
        tap_screen(device, connection, 723, 2222)
        time.sleep(constants.ONE_SECOND)

        # confirm
        tap_screen(device, connection, 802, 1315)
        time.sleep(constants.FIVE_SECONDS)

    elif browser == "Vivaldi":

        # click on the tab button
        tap_screen(device, connection, 980, 2301)
        time.sleep(constants.ONE_SECOND)

        # click on the options button
        tap_screen(device, connection, 887, 259)
        time.sleep(constants.ONE_SECOND)

        # tap at the close all button
        tap_screen(device, connection, 555, 475)
        time.sleep(constants.ONE_SECOND)

        # confirm
        tap_screen(device, connection, 829, 1378)
        time.sleep(constants.FIVE_SECONDS)

    else:
        blade_logger.logger.error(f"Error: Unsupported browser '{browser}'.")
        raise Exception(f"Error: Unsupported browser '{browser}'.")


# clean cache of a particular browser (assumes it is in the foreground)
def browser_clean_cache(device, connection, browser):

    if browser == "Chrome":

        # click on the options button
        tap_screen(device, connection, 1024, 211)
        time.sleep(constants.ONE_SECOND)

        # tap at the settings button
        tap_screen(device, connection, 700, 720)
        time.sleep(constants.ONE_SECOND)

        # tap at the privacy and security button
        tap_screen(device, connection, 500, 1590)
        time.sleep(constants.ONE_SECOND)

        # tap at the clear browsing data button
        tap_screen(device, connection, 500, 527)
        time.sleep(constants.ONE_SECOND)

        # tap at the clear data button
        tap_screen(device, connection, 890, 2242)
        time.sleep(constants.FIVE_SECONDS)

    elif browser == "Brave":

        # click on the options button (lower right corner)
        tap_screen(device, connection, 950, 2300)
        time.sleep(constants.ONE_SECOND)

        # tap at the settings button
        tap_screen(device, connection, 714, 2160)
        time.sleep(constants.ONE_SECOND)

        # tap at the privacy button
        tap_screen(device, connection, 500, 495)
        time.sleep(constants.ONE_SECOND)

        # tap at the clear browsing data button (need to swipe up first)
        swipe_screen(device, connection, 500, 2005, 500, 1100)
        time.sleep(constants.ONE_SECOND)
        tap_screen(device, connection, 500, 2250)
        time.sleep(constants.ONE_SECOND)

        # tap at the clear data button
        tap_screen(device, connection, 900, 2250)
        time.sleep(constants.ONE_SECOND)

        # confirm
        tap_screen(device, connection, 940, 1411)
        time.sleep(constants.FOUR_SECONDS)

    elif browser == "Firefox":

        # click on the options button (lower right corner)
        tap_screen(device, connection, 1058, 2264)
        time.sleep(constants.ONE_SECOND)

        # tap at the settings button
        tap_screen(device, connection, 735, 2122)
        time.sleep(constants.ONE_SECOND)

        # tap at the Delete browsing data button (need to swipe up first)
        swipe_screen(device, connection, 500, 1880, 500, 1110)
        time.sleep(constants.ONE_SECOND)
        tap_screen(device, connection, 500, 2217)
        time.sleep(constants.ONE_SECOND)

        # tap at the Delete browsing data button
        tap_screen(device, connection, 500, 1370)
        time.sleep(constants.ONE_SECOND)

        # tap at the Delete button
        tap_screen(device, connection, 860, 1340)
        time.sleep(constants.FIVE_SECONDS)

    elif browser == "Firefox Focus":
        # not needed, close tabs will deal with it
        pass

    elif browser == "Edge":

        # click on the options button (lower middle)
        tap_screen(device, connection, 947, 2286)
        time.sleep(constants.ONE_SECOND)

        # tap at the settings button
        tap_screen(device, connection, 960, 1542)
        time.sleep(constants.ONE_SECOND)

        # tap at the privacy and security button
        tap_screen(device, connection, 526, 834)
        time.sleep(constants.ONE_SECOND)

        # tap at Clear browsing data button
        tap_screen(device, connection, 526, 492)
        time.sleep(constants.ONE_SECOND)

        # tap at Clear data button
        tap_screen(device, connection, 900, 2118)
        time.sleep(constants.FIVE_SECONDS)

    elif browser == "DuckDuckGo":

        # click on the fire button
        tap_screen(device, connection, 780, 213)
        time.sleep(constants.ONE_SECOND)

        # tap at the Clear all tabs and data button
        tap_screen(device, connection, 532, 2087)
        time.sleep(constants.FIVE_SECONDS)

    elif browser == "Opera":

        # click on the options button (lower right)
        tap_screen(device, connection, 970, 2280)
        time.sleep(constants.ONE_SECOND)

        # tap at the settings button
        tap_screen(device, connection, 990, 1113)
        time.sleep(constants.ONE_SECOND)

        # tap at the privacy and security button
        tap_screen(device, connection, 500, 2303)
        time.sleep(constants.ONE_SECOND)

        # tap at Clear browsing data button (need to swipe up first)
        swipe_screen(device, connection, 500, 1880, 500, 1080)
        time.sleep(constants.ONE_SECOND)
        tap_screen(device, connection, 500, 2254)
        time.sleep(constants.ONE_SECOND)

        # select relevant options and tap at Clear data button
        tap_screen(device, connection, 500, 371)  # Browsing history
        time.sleep(constants.ONE_SECOND)
        tap_screen(device, connection, 500, 933)  # Cookies and site data
        time.sleep(constants.ONE_SECOND)
        tap_screen(device, connection, 500, 1682)  # Advanced
        time.sleep(constants.ONE_SECOND)
        swipe_screen(device, connection, 500, 1880, 500, 600)  # Swipe up
        time.sleep(constants.ONE_SECOND)
        tap_screen(device, connection, 500, 2023)  # Cached images and files
        time.sleep(constants.ONE_SECOND)
        tap_screen(device, connection, 885, 2255)  # Clear data
        time.sleep(constants.FIVE_SECONDS)

    elif browser == "Vivaldi":
        blade_logger.logger.error(f"Error: Unsupported browser '{browser}'.")
        raise Exception(f"Error: Unsupported browser '{browser}'.")

    else:
        blade_logger.logger.error(f"Error: Unsupported browser '{browser}'.")
        raise Exception(f"Error: Unsupported browser '{browser}'.")

def enable_proxy(device, connection, port=8443):

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
