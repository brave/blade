import os
import socket
import shutil

from libs import logger as blade_logger

GLOBAL_PID_FILES_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../../.pid_files/")


def ensure_path(path, clear=False):
    
    if clear and os.path.exists(path):
        shutil.rmtree(path)

    os.makedirs(path, exist_ok=True)



def save_value_to_file(value, filename, custom_path=None):

    # set path
    if custom_path:
        current_path = custom_path
    else:
        current_path = GLOBAL_PID_FILES_PATH

    # ensure path exists
    ensure_path(current_path)

    # write value to file (overwrite if exists)
    file_path = os.path.join(current_path, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(value))


def read_value_from_file(filename, custom_path=None):

    # set path
    if custom_path:
        current_path = custom_path
    else:
        current_path = GLOBAL_PID_FILES_PATH

    file_path = os.path.join(current_path, filename)
    if not os.path.exists(file_path):
        blade_logger.logger.error("Error: File does not exist: " + file_path)
        return None

    # read value from file
    with open(file_path, "r", encoding="utf-8") as f:
        value = f.read()

    return value


def get_local_ip():
    """Get the host's IP address that's accessible from the device"""

    # Create a socket to get the IP used to connect to an external host
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip
