# Note:   Useful ADB-related functions for controlling Android devices
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   04/03/2023

import subprocess
import sys
import time
import urllib.parse


# returns adb identifier base don the connection type
def __get_adb_identifier(device, connection, port=5555):

    if connection == "usb":
        return device["adb_identifier"]

    if connection == "wifi":
        return f"{device['ip']}:{port}"

    sys.exit(f"Error: Unknown connection '{connection}'.")


# execute an adb command to the device ('adb -s <device_id> ' prefix is included automatically)
def run_adb_command(device, connection, command):
    adb_identifier = __get_adb_identifier(device, connection)
    command = f"adb -s {adb_identifier} {command}"
    print(f"\t{command}", flush=True)

    return subprocess.check_output(command, shell=True).rstrip().decode()


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
def swipe_screen(device, connection, from_x, from_y, to_x, to_y, duration=1000):
    run_adb_command(
        device,
        connection,
        f"shell input swipe {from_x} {from_y} {to_x} {to_y} {duration}",
    )


# simulate a scroll up or down gesture
def scroll(device, connection, direction, length=1200, duration=1000):

    if direction == "up":
        from_y = 600
        to_y = from_y + length

    elif direction == "down":
        from_y = 1800
        to_y = from_y - length

    else:
        print("Error: Unsupported scroll direction.")
        return

    swipe_screen(device, connection, 500, from_y, 500, to_y, duration)


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
def start_activity(device, connection, package, activity):
    run_adb_command(device, connection,
                    f"shell am start -n {package}/{activity}")


# take a screenshot and store it into a local file
def take_screenshot(device, connection, filename):
    run_adb_command(device, connection,
                    f"shell screencap -p /sdcard/screenshot.png")
    run_adb_command(device, connection,
                    f"pull /sdcard/screenshot.png {filename}")
    run_adb_command(device, connection, f"shell rm /sdcard/screenshot.png")


# open a url on an activity (e.g. browser)
def open_url_on_activity(device, connection, package, activity, url):

    # add https:// prefix if needed
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    # escape url
    # url = urllib.parse.quote(url, safe='/:')

    # open url
    run_adb_command(
        device,
        connection,
        f"shell am start -a android.intent.action.VIEW -d '{url}' -n {package}/{activity}",
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
        print(
            f"Warning: Wrong brightness value '{brightness}'. Should be in the range [0, 255]. Setting it to minimum (0)."
        )
        brightness = 0

    elif brightness > 255:
        print(
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
        "shell dumpsys input_method | grep -i mActive | cut -d '=' -f2 | cut -d ' ' -f1",
    )

    if current_state == "true":
        return "on"
    else:
        return "off"


# press power button
def power_button(device, connection):
    press_key(device, connection, "KEYCODE_POWER")


# unlock device
def unlock_device(device, connection):
    switch_screen(device, connection, "on")
    time.sleep(1)
    press_key(device, connection, "KEYCODE_MENU")


# close all running applications
def close_all(device, connection):

    press_key(device, connection, "KEYCODE_APP_SWITCH")
    time.sleep(1)

    if device["type"] in ["Google Pixel 6a"]:

        swipe_screen(device, connection, 445, 1270, 940, 1270)
        time.sleep(1)

        tap_screen(device, connection, 229, 1209)
        time.sleep(5)

    elif device["type"] in ["Samsung Galaxy S23"]:

        tap_screen(device, connection, 530, 1820)
        time.sleep(5)

    else:
        print("WARNING: Unsupported device type")


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
            device, connection, "org.mozilla.firefox", "org.mozilla.gecko.BrowserApp"
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
            device, connection, "com.microsoft.emmx", "com.microsoft.ruby.Main"
        )

    elif browser == "DuckDuckGo":
        start_activity(
            device,
            connection,
            "com.duckduckgo.mobile.android",
            "com.duckduckgo.app.launch.Launcher",
        )

    elif browser == "Opera":
        start_activity(device, connection,
                       "com.opera.browser", "com.opera.Opera")

    elif browser == "Vivaldi":
        start_activity(
            device,
            connection,
            "com.vivaldi.browser",
            "com.google.android.apps.chrome.Main",
        )

    else:
        print("Error: Unsupported browser.")


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
        print("Error: Unsupported browser.")


# close current tab in a particular browser (assumes it is in the foreground)
def browser_close_tab(device, connection, browser):

    if browser == "Chrome":
        print("Error: Unsupported feature.")

    elif browser == "Brave":
        print("Error: Unsupported feature.")

    elif browser == "Firefox":
        print("Error: Unsupported browser.")

    elif browser == "Firefox Focus":
        print("Error: Unsupported browser.")

    elif browser == "Edge":
        print("Error: Unsupported browser.")

    elif browser == "DuckDuckGo":
        print("Error: Unsupported browser.")

    elif browser == "Opera":
        print("Error: Unsupported browser.")

    elif browser == "Vivaldi":
        print("Error: Unsupported browser.")

    else:
        print("Error: Unsupported browser.")


# close all tabs in a particular browser (assumes it is in the foreground)
def browser_close_all_tabs(device, connection, browser):
    # Note: Duration is identical per browser (8 seconds)

    if browser == "Chrome":

        # click on the tab button
        tap_screen(device, connection, 870, 232)
        time.sleep(1)

        # click on the options button
        tap_screen(device, connection, 1024, 211)
        time.sleep(1)

        # tap at the close all button
        tap_screen(device, connection, 735, 481)
        time.sleep(1)

        # confirm
        tap_screen(device, connection, 830, 1386)
        time.sleep(5)

    elif browser == "Brave":

        # click on the tab button
        tap_screen(device, connection, 756, 2266)
        time.sleep(1)

        # click on the options button (lower right corner)
        tap_screen(device, connection, 950, 2300)
        time.sleep(1)

        # tap at the close all button
        tap_screen(device, connection, 650, 1900)
        time.sleep(1)

        # confirm
        tap_screen(device, connection, 830, 1386)
        time.sleep(5)

    elif browser == "Firefox":

        # click on the tab button
        tap_screen(device, connection, 925, 2272)
        time.sleep(1)

        # change tab screen into full screen
        swipe_screen(device, connection, 513, 755, 513, 313)
        time.sleep(1)

        # click on the options button
        tap_screen(device, connection, 1022, 382)
        time.sleep(1)

        # tap at the close all button
        tap_screen(device, connection, 821, 920)
        time.sleep(5)

    elif browser == "Firefox Focus":

        # tap at the close all button
        tap_screen(device, connection, 54, 236)
        time.sleep(8)

    elif browser == "Edge":

        # click on the tab button
        tap_screen(device, connection, 785, 2303)
        time.sleep(1)

        # tap at the close all button
        tap_screen(device, connection, 102, 2247)
        time.sleep(2)

        # open new tab so context is the same
        tap_screen(device, connection, 537, 2294)
        time.sleep(5)

    elif browser == "DuckDuckGo":

        # click on the tab button
        tap_screen(device, connection, 925, 225)
        time.sleep(1)

        # close the last tab
        tap_screen(device, connection, 466, 371)
        time.sleep(2)

        # go back to the home screen
        tap_screen(device, connection, 73, 212)
        time.sleep(5)

    elif browser == "Opera":

        # click on the tab button
        tap_screen(device, connection, 767, 2258)
        time.sleep(1)

        # click on the options button
        tap_screen(device, connection, 990, 2265)
        time.sleep(1)

        # tap at the close all button
        tap_screen(device, connection, 723, 2222)
        time.sleep(1)

        # confirm
        tap_screen(device, connection, 802, 1315)
        time.sleep(5)

    elif browser == "Vivaldi":

        # click on the tab button
        tap_screen(device, connection, 980, 2301)
        time.sleep(1)

        # click on the options button
        tap_screen(device, connection, 887, 259)
        time.sleep(1)

        # tap at the close all button
        tap_screen(device, connection, 555, 475)
        time.sleep(1)

        # confirm
        tap_screen(device, connection, 829, 1378)
        time.sleep(5)

    else:
        print("Error: Unsupported browser.")


# clean cache of a particular browser (assumes it is in the foreground)
def browser_clean_cache(device, connection, browser):

    if browser == "Chrome":

        # click on the options button
        tap_screen(device, connection, 1024, 211)
        time.sleep(1)

        # tap at the settings button
        tap_screen(device, connection, 700, 720)
        time.sleep(1)

        # tap at the privacy and security button
        tap_screen(device, connection, 500, 1590)
        time.sleep(1)

        # tap at the clear browsing data button
        tap_screen(device, connection, 500, 527)
        time.sleep(1)

        # tap at the clear data button
        tap_screen(device, connection, 890, 2242)
        time.sleep(5)

    elif browser == "Brave":

        # click on the options button (lower right corner)
        tap_screen(device, connection, 950, 2300)
        time.sleep(1)

        # tap at the settings button
        tap_screen(device, connection, 714, 2160)
        time.sleep(1)

        # tap at the privacy button
        tap_screen(device, connection, 500, 495)
        time.sleep(1)

        # tap at the clear browsing data button (need to swipe up first)
        swipe_screen(device, connection, 500, 2005, 500, 1100)
        time.sleep(1)
        tap_screen(device, connection, 500, 2250)
        time.sleep(1)

        # tap at the clear data button
        tap_screen(device, connection, 900, 2250)
        time.sleep(1)

        # confirm
        tap_screen(device, connection, 940, 1411)
        time.sleep(4)

    elif browser == "Firefox":

        # click on the options button (lower right corner)
        tap_screen(device, connection, 1058, 2264)
        time.sleep(1)

        # tap at the settings button
        tap_screen(device, connection, 735, 2122)
        time.sleep(1)

        # tap at the Delete browsing data button (need to swipe up first)
        swipe_screen(device, connection, 500, 1880, 500, 1110)
        time.sleep(1)
        tap_screen(device, connection, 500, 2217)
        time.sleep(1)

        # tap at the Delete browsing data button
        tap_screen(device, connection, 500, 1370)
        time.sleep(1)

        # tap at the Delete button
        tap_screen(device, connection, 860, 1340)
        time.sleep(5)

    elif browser == "Firefox Focus":
        # not needed, close tabs will deal with it
        pass

    elif browser == "Edge":

        # click on the options button (lower middle)
        tap_screen(device, connection, 947, 2286)
        time.sleep(1)

        # tap at the settings button
        tap_screen(device, connection, 960, 1542)
        time.sleep(1)

        # tap at the privacy and security button
        tap_screen(device, connection, 526, 834)
        time.sleep(1)

        # tap at Clear browsing data button
        tap_screen(device, connection, 526, 492)
        time.sleep(1)

        # tap at Clear data button
        tap_screen(device, connection, 900, 2118)
        time.sleep(5)

    elif browser == "DuckDuckGo":

        # click on the fire button
        tap_screen(device, connection, 780, 213)
        time.sleep(1)

        # tap at the Clear all tabs and data button
        tap_screen(device, connection, 532, 2087)
        time.sleep(5)

    elif browser == "Opera":

        # click on the options button (lower right)
        tap_screen(device, connection, 970, 2280)
        time.sleep(1)

        # tap at the settings button
        tap_screen(device, connection, 990, 1113)
        time.sleep(1)

        # tap at the privacy and security button
        tap_screen(device, connection, 500, 2303)
        time.sleep(1)

        # tap at Clear browsing data button (need to swipe up first)
        swipe_screen(device, connection, 500, 1880, 500, 1080)
        time.sleep(1)
        tap_screen(device, connection, 500, 2254)
        time.sleep(1)

        # select relevant options and tap at Clear data button
        tap_screen(device, connection, 500, 371)  # Browsing history
        time.sleep(1)
        tap_screen(device, connection, 500, 933)  # Cookies and site data
        time.sleep(1)
        tap_screen(device, connection, 500, 1682)  # Advanced
        time.sleep(1)
        swipe_screen(device, connection, 500, 1880, 500, 600)  # Swipe up
        time.sleep(1)
        tap_screen(device, connection, 500, 2023)  # Cached images and files
        time.sleep(1)
        tap_screen(device, connection, 885, 2255)  # Clear data
        time.sleep(5)

    elif browser == "Vivaldi":
        print("Error: Unsupported browser.")

    else:
        print("Error: Unsupported browser.")
