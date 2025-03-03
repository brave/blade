# Note:   Bluetooth HID Emulator DBUS Service
# Author: Kleomenis Katevas (kkatevas@brave.com)
#         Inspired by: https://gist.github.com/ukBaz/a47e71e7b87fbc851b27cde7d1c0fcf0
# Date:   13/03/2023

import time

import dbus
from libs import btkkeymap as keymap
from libs import constants
from libs import logger as blade_logger

HID_DBUS = "org.yaptb.btkbservice"
HID_SRVC = "/org/yaptb/btkbservice"

KEY_PRESSED_EVENT = 1
KEY_RELEASED_EVENT = 0


class BtkLib:
    """
    Library used for sending HID messages (mouse + keyboard)
    """

    def __init__(self):

        # init service
        self.target_length = 6
        self.mod_keys = 0b00000000
        self.pressed_keys = []

        self.bus = dbus.SystemBus()
        self.btkobject = self.bus.get_object(HID_DBUS, HID_SRVC)
        self.btk_service = dbus.Interface(self.btkobject, HID_DBUS)

        # mouse
        self.mouse_buttons = 0b00000000

    def _update_mod_keys(self, mod_key, key_event_type):
        """
        Which modifier keys are active is stored in an 8 bit number.
        Each bit represents a different key. This method takes which bit
        and its new value as input
        :param mod_key: The value of the bit to be updated with new value
        :param key_event_type: Binary 1 or 0 depending if pressed or released
        """
        self.mod_keys = key_event_type << mod_key

    def _update_keys(self, norm_key, key_event_type):

        if key_event_type == KEY_RELEASED_EVENT:
            self.pressed_keys.remove(norm_key)
        elif norm_key not in self.pressed_keys:
            self.pressed_keys.insert(0, norm_key)

        len_delta = self.target_length - len(self.pressed_keys)

        if len_delta < 0:
            self.pressed_keys = self.pressed_keys[:len_delta]
        elif len_delta > 0:
            self.pressed_keys.extend([0] * len_delta)

    @property
    def _state(self):
        """
        property with the HID message to send for the current keys pressed
        on the keyboards
        :return: bytes of HID message
        """
        return [0xA1, 0x01, self.mod_keys, 0, *self.pressed_keys]

    def _send_keys(self):
        self.btk_service.send_keys(self._state)

    def _convert_to_signed_byte(self, value):

        if value < -127 or value > 127:
            blade_logger.logger.error("Error: Value not in range of (-127, 127)")
            raise Exception("Error: Value not in range of (-127, 127)")

        if value < 0:
            return value + 256
        else:
            return value

    def _send_hid_mouse_message(self, buttons, x, y):

        sbyte_x = self._convert_to_signed_byte(x)
        sbyte_y = self._convert_to_signed_byte(y)
        self.btk_service.send_keys([0xA1, 0x02, buttons, sbyte_x, sbyte_y])

    def _send_hid_as_combo(self, hid_combo):

        for hid_key in hid_combo:

            # press keys
            self._update_keys(hid_key, KEY_PRESSED_EVENT)
            self._send_keys()

        for hid_key in hid_combo:

            # release keys
            self._update_keys(hid_key, KEY_RELEASED_EVENT)
            self._send_keys()

    # move mouse to a given position (relative to the current position)
    def move_mouse(self, x, y):
        self._send_hid_mouse_message(self.mouse_buttons, x, y)

    # perform a mouse click
    def mouse_click(self):
        self.mouse_buttons = 0b00000001
        self._send_hid_mouse_message(self.mouse_buttons, 0, 0)

    # perform a mouse release
    def mouse_release(self):
        self.mouse_buttons = 0b00000000
        self._send_hid_mouse_message(self.mouse_buttons, 0, 0)

    # send a text, character by character, with a given delay (in seconds)
    def send_text(self, text, delay=constants.TENTH_OF_A_SECOND):

        for character in text:

            hid_keys = keymap.hid_from_character(character)

            if hid_keys is None:
                blade_logger.logger.warning(f"WARNING: Unknown key for character: {character}")
                return

            time.sleep(delay)
            self._send_hid_as_combo(hid_keys)

    # send a shortcut, e.g., "$ENTER", with a given delay (in seconds)
    def send_shortcut(self, shortcut, delay=constants.TENTH_OF_A_SECOND):

        hid_commands = keymap.hid_from_shortcut(shortcut)

        if hid_commands is None:
            blade_logger.logger.warning(f"WARNING: Unknown command: {shortcut}")
            return

        time.sleep(delay)
        self._send_hid_as_combo(hid_commands)

    # send a key combo, e.g., ["KEY_LEFTMETA", "KEY_R"], with a given delay (in seconds)
    def send_hid_keys(self, key_combo, delay=constants.TENTH_OF_A_SECOND):

        hid_keys = keymap.hid_from_keys(key_combo)

        if hid_keys is None:
            blade_logger.logger.warning(f"WARNING: Unknown hid_keys: {hid_keys}")
            return

        time.sleep(delay)
        self._send_hid_as_combo(hid_keys)
