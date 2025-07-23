# Note:   Useful BT-related functions for controlling iOS devices
# Author: Kleomenis Katevas (kkatevas@brave.com)
# Date:   22/03/2023

import sys
import time

from libs import btklib

# import subprocess
from libs import constants


btk = btklib.BtkLib()

screen_min = (0, 0)
screen_max = (2436, 1125)

# TODO: refactor using a class that saves the mouse's state
mouse_coordinates = (0, 0)


# setup device for the experiment
def setup_device(device):
    pass


# cleanup device after the experiment
def cleanup_device(device):
    pass


def type_text(device, text, delay=constants.BT_IOS_COMMANDS_DEFAULT_KEYBOARD_TYPE_DELAY):
    btk.send_text(text, delay=delay)
    time.sleep(constants.BT_IOS_COMMANDS_EXECUTION_TIMEOUT)

def move_pointer_with_delta(device, x_delta, y_delta, delay=constants.BT_IOS_COMMANDS_DEFAULT_MOUSE_DELAY):

    # constants
    step = 100

    # apply x
    repeat_x = int(x_delta / step)
    remainder_x = abs(x_delta) % step
    modifier = 1 if x_delta > 0 else -1
    for _ in range(abs(repeat_x)):
        btk.move_mouse(modifier * step, 0)
        time.sleep(delay)
    btk.move_mouse(modifier * remainder_x, 0)
    time.sleep(delay)

    # apply y
    repeat_y = int(y_delta / step)
    remainder_y = abs(y_delta) % step
    modifier = 1 if y_delta > 0 else -1
    for i in range(abs(repeat_y)):
        btk.move_mouse(0, modifier * step)
        time.sleep(delay)
    btk.move_mouse(0, modifier * remainder_y)
    time.sleep(constants.BT_IOS_COMMANDS_EXECUTION_TIMEOUT)


def move_pointer(device, abs_x, abs_y, delay=constants.BT_IOS_COMMANDS_DEFAULT_MOUSE_DELAY):
    # TODO: Needs improvements, doesn't work well

    # first reset the pointer
    reset_pointer(device, mode="top-left", delay=delay)
    time.sleep(constants.BT_IOS_COMMANDS_DEFAULT_MOUSE_SLOW_ACTIONS_DELAY)

    # TODO: refactor using a class that saves the mouse's state
    global mouse_coordinates

    # protect from negative coordinates
    if abs_x < 0 or abs_y < 0:
        raise Exception("Error: Coordinates can only be positive integers.")

    # set to max if needed
    if abs_x > screen_max[0]:
        abs_x = screen_max[0]

    if abs_y > screen_max[1]:
        abs_y = screen_max[1]

    # find deltas
    x_delta = abs_x - mouse_coordinates[0]
    y_delta = abs_y - mouse_coordinates[1]

    # move pointer
    move_pointer_with_delta(device, x_delta, y_delta, delay)

    # save new coordinates
    mouse_coordinates = (abs_x, abs_y)
    time.sleep(constants.BT_IOS_COMMANDS_EXECUTION_TIMEOUT)


def reset_pointer(device, mode="top-left", delay=constants.BT_IOS_COMMANDS_DEFAULT_MOUSE_DELAY):

    # TODO: refactor using a class that saves the mouse's state
    global mouse_coordinates

    # constants
    step = 100
    repeat = 20
    # get x/y based on mode
    if mode == "top-left":
        x, y = -step, -step
    elif mode == "top-right":
        x, y = step, -step
    elif mode == "bottom-left":
        x, y = -step, step
    elif mode == "bottom-right":
        x, y = step, step
    else:
        raise Exception("Error: Unknown mode: %s" % mode)

    # apply
    for _ in range(repeat):
        btk.move_mouse(x, y)
        time.sleep(delay)

    # save new coordinates
    mouse_coordinates = screen_min
    # print('Mouse coordinates: (%d, %d)' % mouse_coordinates)
    time.sleep(constants.BT_IOS_COMMANDS_EXECUTION_TIMEOUT)


def open_app(device, app_name):
    btk.send_shortcut("$SEARCH")
    time.sleep(constants.BT_IOS_COMMANDS_EXTENDED_EXECUTION_TIMEOUT)
    btk.send_text(app_name)
    time.sleep(constants.BT_IOS_COMMANDS_EXECUTION_TIMEOUT)
    btk.send_shortcut("$ENTER")
    time.sleep(constants.BT_IOS_COMMANDS_EXTENDED_EXECUTION_TIMEOUT)


def close_app(device, number_of_apps=1, delay=constants.BT_IOS_COMMANDS_DEFAULT_MOUSE_FAST_ACTIONS_DELAY):

    # tap at the virtual button
    reset_pointer(device, "bottom-right")
    time.sleep(delay)
    move_pointer_with_delta(device, -25, -25)
    time.sleep(delay)
    mouse_click(device)
    time.sleep(constants.BT_IOS_COMMANDS_EXECUTION_TIMEOUT)

    # double tap at home button
    reset_pointer(device, "bottom-right")
    move_pointer_with_delta(device, -100, -60)
    time.sleep(delay)
    double_mouse_click(device)
    time.sleep(constants.BT_IOS_COMMANDS_EXECUTION_TIMEOUT)

    # swipe up
    for _ in range(number_of_apps):
        swipe_up(device)

    # Send HOME
    btk.send_shortcut("$HOME")
    time.sleep(constants.BT_IOS_COMMANDS_EXECUTION_TIMEOUT)


def mouse_click(device):
    btk.mouse_click()
    time.sleep(constants.BT_IOS_COMMANDS_MOUSE_CLICK_DELAY)
    btk.mouse_release()
    time.sleep(constants.BT_IOS_COMMANDS_EXECUTION_TIMEOUT)


def double_mouse_click(device):
    btk.mouse_click()
    time.sleep(constants.BT_IOS_COMMANDS_MOUSE_CLICK_DELAY)
    btk.mouse_release()
    time.sleep(constants.BT_IOS_COMMANDS_MOUSE_CLICK_DELAY)
    btk.mouse_click()
    time.sleep(constants.BT_IOS_COMMANDS_MOUSE_CLICK_DELAY)
    btk.mouse_release()
    time.sleep(constants.BT_IOS_COMMANDS_EXECUTION_TIMEOUT)


def swipe_up(device):
    # Not perfect, but it works.

    # move to lower middle
    reset_pointer(device, "bottom-right")
    time.sleep(constants.BT_IOS_COMMANDS_EXECUTION_TIMEOUT)
    move_pointer_with_delta(device, -40, -100)
    time.sleep(constants.BT_IOS_COMMANDS_EXECUTION_TIMEOUT)

    btk.mouse_click()
    for _ in range(10):
        move_pointer_with_delta(device, 0, -100)
    btk.mouse_release()

    time.sleep(constants.BT_IOS_COMMANDS_EXECUTION_TIMEOUT)


def scroll(device, direction="up", delay=constants.BT_IOS_COMMANDS_DEFAULT_MOUSE_FAST_ACTIONS_DELAY):
    # Not perfect, but it works.

    if direction == "up":
        modifier = -1
    elif direction == "down":
        modifier = 1
    else:
        sys.exit("Unknown direction: %s" % direction)

    # move to lower middle
    reset_pointer(device, "top-left")
    move_pointer_with_delta(device, 750, 1200)
    time.sleep(delay)

    btk.mouse_click()
    for _ in range(50):
        move_pointer_with_delta(device, 0, modifier * 4)
    for _ in range(10):
        move_pointer_with_delta(device, 0, modifier * 1)
    btk.mouse_release()

    time.sleep(constants.BT_IOS_COMMANDS_EXECUTION_TIMEOUT)


def unlock_device(device):

    btk.send_shortcut("$ENTER")  # wake up device
    time.sleep(constants.BT_IOS_COMMANDS_EXECUTION_TIMEOUT)
    btk.send_shortcut("$HOME")  # try to unlock
    time.sleep(constants.BT_IOS_COMMANDS_EXECUTION_TIMEOUT)

    # if pin exists, enter it
    if device.get("pin"):
        btk.send_text(device["pin"])
        btk.send_shortcut("$ENTER")

    time.sleep(constants.BT_IOS_COMMANDS_EXTENDED_EXECUTION_TIMEOUT)


def lock_device(device):

    btk.send_shortcut("$LOCK")
    time.sleep(constants.BT_IOS_COMMANDS_EXTENDED_EXECUTION_TIMEOUT)


def browser_reload(device, browser):
    btk.send_hid_keys(["KEY_LEFTMETA", "KEY_R"])
    time.sleep(constants.BT_IOS_COMMANDS_EXECUTION_TIMEOUT)


def browser_open_new_tab(device, browser):
    btk.send_hid_keys(["KEY_LEFTMETA", "KEY_T"])
    time.sleep(constants.BT_IOS_COMMANDS_EXECUTION_TIMEOUT)

def browser_close_tab(device, browser):
    btk.send_hid_keys(["KEY_LEFTMETA", "KEY_W"])
    time.sleep(constants.BT_IOS_COMMANDS_EXECUTION_TIMEOUT)


def browser_scroll_down(device, browser):

    if browser in ["Firefox", "Firefox Focus"]:
        btk.send_hid_keys(["KEY_DOWN"])
    else:
        btk.send_hid_keys(["KEY_SPACE"])

    time.sleep(constants.BT_IOS_COMMANDS_EXECUTION_TIMEOUT)


def browser_open_url(device, browser, url):

    # add https:// prefix if needed
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    btk.send_hid_keys(["KEY_LEFTMETA", "KEY_L"])
    time.sleep(constants.BT_IOS_COMMANDS_DEFAULT_MOUSE_SLOW_ACTIONS_DELAY)
    btk.send_text(url)
    time.sleep(constants.BT_IOS_COMMANDS_DEFAULT_MOUSE_SLOW_ACTIONS_DELAY)
    btk.send_hid_keys(["KEY_ENTER"])

    time.sleep(constants.BT_IOS_COMMANDS_EXECUTION_TIMEOUT)