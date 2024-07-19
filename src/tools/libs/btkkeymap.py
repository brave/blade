# Note:   Char to HID mapping
# Author: Kleomenis Katevas (kkatevas@brave.com)
#         Inspired by: https://gist.github.com/ukBaz/a47e71e7b87fbc851b27cde7d1c0fcf0
# Date:   13/03/2023

from libs import hid_keymap

characters = {
    "1": ["KEY_1"],
    "2": ["KEY_2"],
    "3": ["KEY_3"],
    "4": ["KEY_4"],
    "5": ["KEY_5"],
    "6": ["KEY_6"],
    "7": ["KEY_7"],
    "8": ["KEY_8"],
    "9": ["KEY_9"],
    "0": ["KEY_0"],
    "-": ["KEY_MINUS"],
    "=": ["KEY_EQUAL"],
    "[": ["KEY_LEFTBRACE"],
    "]": ["KEY_RIGHTBRACE"],
    ";": ["KEY_SEMICOLON"],
    "'": ["KEY_APOSTROPHE"],
    "\\": ["KEY_BACKSLASH"],
    ",": ["KEY_COMMA"],
    ".": ["KEY_DOT"],
    "/": ["KEY_SLASH"],
    "`": ["KEY_GRAVE"],
    "!": ["KEY_LEFTSHIFT", "KEY_1"],
    "@": ["KEY_LEFTSHIFT", "KEY_2"],
    "£": ["KEY_LEFTSHIFT", "KEY_3"],
    "$": ["KEY_LEFTSHIFT", "KEY_4"],
    "%": ["KEY_LEFTSHIFT", "KEY_5"],
    "^": ["KEY_LEFTSHIFT", "KEY_6"],
    "&": ["KEY_LEFTSHIFT", "KEY_7"],
    "*": ["KEY_LEFTSHIFT", "KEY_8"],
    "(": ["KEY_LEFTSHIFT", "KEY_9"],
    ")": ["KEY_LEFTSHIFT", "KEY_0"],
    "_": ["KEY_LEFTSHIFT", "KEY_MINUS"],
    "+": ["KEY_LEFTSHIFT", "KEY_EQUAL"],
    "{": ["KEY_LEFTSHIFT", "KEY_LEFTBRACE"],
    "}": ["KEY_LEFTSHIFT", "KEY_RIGHTBRACE"],
    ":": ["KEY_LEFTSHIFT", "KEY_SEMICOLON"],
    '"': ["KEY_LEFTSHIFT", "KEY_APOSTROPHE"],
    "|": ["KEY_LEFTSHIFT", "KEY_BACKSLASH"],
    "<": ["KEY_LEFTSHIFT", "KEY_COMMA"],
    ">": ["KEY_LEFTSHIFT", "KEY_DOT"],
    "?": ["KEY_LEFTSHIFT", "KEY_SLASH"],
    "~": ["KEY_LEFTSHIFT", "KEY_GRAVE"],
    "a": ["KEY_A"],
    "b": ["KEY_B"],
    "c": ["KEY_C"],
    "d": ["KEY_D"],
    "e": ["KEY_E"],
    "f": ["KEY_F"],
    "g": ["KEY_G"],
    "h": ["KEY_H"],
    "i": ["KEY_I"],
    "j": ["KEY_J"],
    "k": ["KEY_K"],
    "l": ["KEY_L"],
    "m": ["KEY_M"],
    "n": ["KEY_N"],
    "o": ["KEY_O"],
    "p": ["KEY_P"],
    "q": ["KEY_Q"],
    "r": ["KEY_R"],
    "s": ["KEY_S"],
    "t": ["KEY_T"],
    "u": ["KEY_U"],
    "v": ["KEY_V"],
    "w": ["KEY_W"],
    "x": ["KEY_X"],
    "y": ["KEY_Y"],
    "z": ["KEY_Z"],
    "A": ["KEY_LEFTSHIFT", "KEY_A"],
    "B": ["KEY_LEFTSHIFT", "KEY_B"],
    "C": ["KEY_LEFTSHIFT", "KEY_C"],
    "D": ["KEY_LEFTSHIFT", "KEY_D"],
    "E": ["KEY_LEFTSHIFT", "KEY_E"],
    "F": ["KEY_LEFTSHIFT", "KEY_F"],
    "G": ["KEY_LEFTSHIFT", "KEY_G"],
    "H": ["KEY_LEFTSHIFT", "KEY_H"],
    "I": ["KEY_LEFTSHIFT", "KEY_I"],
    "J": ["KEY_LEFTSHIFT", "KEY_J"],
    "K": ["KEY_LEFTSHIFT", "KEY_K"],
    "L": ["KEY_LEFTSHIFT", "KEY_L"],
    "M": ["KEY_LEFTSHIFT", "KEY_M"],
    "N": ["KEY_LEFTSHIFT", "KEY_N"],
    "O": ["KEY_LEFTSHIFT", "KEY_O"],
    "P": ["KEY_LEFTSHIFT", "KEY_P"],
    "Q": ["KEY_LEFTSHIFT", "KEY_Q"],
    "R": ["KEY_LEFTSHIFT", "KEY_R"],
    "S": ["KEY_LEFTSHIFT", "KEY_S"],
    "T": ["KEY_LEFTSHIFT", "KEY_T"],
    "U": ["KEY_LEFTSHIFT", "KEY_U"],
    "V": ["KEY_LEFTSHIFT", "KEY_V"],
    "W": ["KEY_LEFTSHIFT", "KEY_W"],
    "X": ["KEY_LEFTSHIFT", "KEY_X"],
    "Y": ["KEY_LEFTSHIFT", "KEY_Y"],
    "Z": ["KEY_LEFTSHIFT", "KEY_Z"],
    " ": ["KEY_SPACE"],
}

shortcuts = {
    "$ESC": ["KEY_ESC"],
    "$ENTER": ["KEY_ENTER"],
    "$TAB": ["KEY_TAB"],
    "$BACKSPACE": ["KEY_BACKSPACE"],
    "$CAPSLOCK": ["KEY_CAPSLOCK"],
    "$UP": ["KEY_UP"],
    "$DOWN": ["KEY_DOWN"],
    "$LEFT": ["KEY_LEFT"],
    "$RIGHT": ["KEY_RIGHT"],
    "$HOME": ["KEY_LEFTMETA", "KEY_H"],
    "$SEARCH": ["KEY_LEFTMETA", "KEY_SPACE"],
    "$LOCK": ["KEY_LEFTMETA", "KEY_LEFTCTRL", "KEY_Q"],
}


def hid_from_character(character):

    hid_keys = characters.get(character)

    if hid_keys is None:
        return None

    return [hid_keymap.convert_key(key) for key in hid_keys]


def hid_from_shortcut(shortcut):
    hid_keys = shortcuts.get(shortcut)

    if hid_keys is None:
        return None

    return hid_from_keys(hid_keys)


def hid_from_keys(hid_keys):
    return [hid_keymap.convert_key(key) for key in hid_keys]
