import os


def ensure_path(path):
    os.makedirs(path, exist_ok=True)


def save_value_to_file(value, file_path):

    # write value to file (overwrite if exists)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(str(value))


def read_value_from_file(file_path):

    if not os.path.exists(file_path):
        print("Error: File does not exist: " + file_path)
        return None

    # read value from file
    with open(file_path, "r", encoding="utf-8") as f:
        value = f.read()

    return value
