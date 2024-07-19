# Note:   Measure the performance of On-Device LLMs on Android
# Author: Kleomenis Katevas (kkatevas@brave.com), Stefanos Laskaridis (stefanos@brave.com)
# Date:   26/10/2023

import os
import pathlib
import subprocess
import sys
import time

from libs import rest_await
from libs.automation import adb_commands as cmd

# Supported activities (package, activity)
ACTIVITIES = {
    "LlamaCpp": (None, None),  # It's a command line tool, so None is ok
    "MLCChat": ("ai.mlc.mlcchat", "ai.mlc.mlcchat.MainActivity"),
    "MLCChat++": ("ai.mlc.mlcchat32", "ai.mlc.mlcchat.MainActivity"),
}

# LlamaCpp consts
LLAMACPP_INPUT_PATH = "/data/local/tmp/"
LLAMACPP_INPUT_PROMPTS_FILENAME = (
    pathlib.Path(__file__).parent.resolve()
    / ".."
    / ".."
    / ".."
    / ".."
    / "blade"
    / "melt"
    / "src"
    / "prompts"
    / "conversations.json"
)
LLAMACPP_REPO_PATH = (
    pathlib.Path(__file__).parent.resolve()
    / ".."
    / ".."
    / ".."
    / ".."
    / "frameworks"
    / "llama.cpp"
    / "llama.cpp"
)
LLAMACPP_EVENTS_ROOT = f"{LLAMACPP_INPUT_PATH}/melt_measurements/"


# start REST API server
REST_AWAIT_SERVER = rest_await.RestAwaitApp()


def check_device(device):

    if device["os"] != "Android":
        print("Error: Device is not Android.")
        return False

    return True


def check_arguments(arguments):

    # check number of arguments passed
    if len(arguments) < 4:  # at least 4, more for LlamaCpp
        print(f"Error: Wrong number of arguments. Usage: {usage()}")
        return False

    # check brightness range
    brightness = int(arguments[0])
    if brightness < 0 or brightness > 255:
        print(f"Wrong brightness value '{brightness}'. Should be in the range [0, 255]")
        return False

    # check apps
    test_app = arguments[1]
    if test_app not in ACTIVITIES.keys():
        print(f"Unsupported app '{test_app}'. Should be one of: {ACTIVITIES.keys()}.")
        return False

    model_name = arguments[2]

    # check runs range
    runs = int(arguments[3])
    if runs < 1 or runs > 100:
        print(f"Wrong runs value '{runs}'. Should be in the range [1, 100]")
        return False

    # print arguments
    print(
        f"Arguments: brightness={brightness}, test-app={test_app}, model_name={model_name}, runs={runs}"
    )

    if len(arguments) > 4:

        conversation_from = int(arguments[4])
        conversation_to = int(arguments[5])
        output_path = arguments[6]
        print(
            f"Additional arguments: conversation_from={conversation_from}, conversation_to={conversation_to}, output_path={output_path}"
        )

    return True


def setup_device(device, tslogger, arguments):

    connection = "wifi"

    tslogger.log_begin("Setup")

    # always at the beginning of this method
    cmd.setup_device(device, connection)

    # screen on and unlock device
    cmd.unlock_device(device, connection)
    time.sleep(3)

    # set brightness level
    brightness = int(arguments[0])
    cmd.set_brightness(device, connection, brightness)

    # wait until brightness is set
    time.sleep(5)

    tslogger.log_end("Setup")


def run_experiment(device, tslogger, arguments):

    # parameters
    connection = "wifi"
    test_app = arguments[1]
    model_name = arguments[2]
    runs = int(arguments[3])

    tslogger.log_begin("Experiment")

    for run in range(runs):

        if test_app == "LlamaCpp":

            # parse extra arguments
            conversation_from = int(arguments[4])
            conversation_to = int(arguments[5])
            output_path = arguments[6]
            n_threads = int(arguments[7])

            automate_llamaCpp(
                device,
                tslogger,
                run,
                model_name,
                conversation_from,
                conversation_to,
                output_path,
                n_threads,
            )

        elif test_app in ["MLCChat", "MLCChat++"]:

            # open the app
            package, activity = ACTIVITIES[test_app]
            cmd.start_activity(device, connection, package, activity)
            time.sleep(5)

            automate_mlc_app(device, tslogger, model_name, run, test_app)
            time.sleep(5)

            # close apps
            cmd.close_all(device, connection)

        else:
            sys.exit(f"Error: Unknown app '{test_app}'")

        # close app
        time.sleep(60)

    tslogger.log_end("Experiment")


def automate_llamaCpp(
    device,
    tslogger,
    run,
    model_name,
    conversation_from,
    conversation_to,
    output_path,
    n_threads=1,
):

    tslogger.log_begin(f"Run_{run}")

    script = os.path.join(LLAMACPP_REPO_PATH, "run_scripts/run-llamacpp.sh")
    events_filename = os.path.join(LLAMACPP_EVENTS_ROOT, "measurements")
    _ = subprocess.run(
        [
            f"{script} android {LLAMACPP_INPUT_PATH} '{model_name}' '{LLAMACPP_INPUT_PROMPTS_FILENAME}' {conversation_from} {conversation_to} '{output_path}' '{events_filename}' {run} 1 {n_threads}"
        ],
        shell=True,
        check=True,
        text=True,
    )

    tslogger.log_end(f"Run_{run}")


def automate_mlc_app(device, tslogger, model_name, run, app):

    model_idx = __get_model_idx(model_name, device, app)

    connection = "wifi"

    tslogger.log_begin(f"Run_{run}")

    # choose model and wait to load
    x_coord, y_coord = __get_select_model_coordinates(device, model_idx)
    cmd.tap_screen(device, connection, x_coord, y_coord)
    time.sleep(10)

    # click reload button (start's the automation)
    x_coord, y_coord = __get_reload_button_coordinates(device)
    cmd.tap_screen(device, connection, x_coord, y_coord)
    time.sleep(1)

    # tap at the center of the screen to enable keyboard input
    x_coord, y_coord = __get_center_of_screen_coordinates(device)
    cmd.tap_screen(device, connection, x_coord, y_coord)
    time.sleep(1)

    # type filename
    filename = f"measurements_iter{run}"
    cmd.type_text(device, connection, filename)
    time.sleep(1)
    x_coord, y_coord = __get_run_button_coordinates(device)
    cmd.tap_screen(device, connection, x_coord, y_coord)  # tap Run
    time.sleep(1)

    # wait until the app notifies that experiment is done
    REST_AWAIT_SERVER.set_await(timeout=3600)
    time.sleep(5)
    # app will exit automatically when done

    tslogger.log_end(f"Run_{run}")


def cleanup_device(device, tslogger, arguments):

    connection = "wifi"

    tslogger.log_begin("Cleanup")

    # always at the end of this method
    cmd.cleanup_device(device, connection)

    tslogger.log_end("Cleanup")


def automation_type():
    return "ADB"


def usage():
    return "llm-evaluation-android5 <brightness> <test-app> <runs>"


def description():
    return "Measures the performance of On-Device LLMs on Android"


def __get_model_idx(model_name, device, app):

    if device["friendly_name"] == "Galaxy S23":
        if app == "MLCChat":
            models = [
                "Llama-2-7b-chat-hf-q4f16_1",
                "mistralai_Mistral-7B-Instruct-v0.1-q3f16_1",
                "mistralai_Mistral-7B-Instruct-v0.1-q4f16_1",
                "TinyLlama_TinyLlama-1.1B-Chat-v0.5-q3f16_1",
                "TinyLlama_TinyLlama-1.1B-Chat-v0.5-q4f16_1",
                "TinyLlama_TinyLlama-1.1B-Chat-v0.5-q0f32",
                "stabilityai_stablelm-zephyr-3b-q3f16_1",
                "stabilityai_stablelm-zephyr-3b-q4f16_1",
            ]
        elif app == "MLCChat++":
            models = [
                "meta-llama_Llama-2-7b-chat-hf-q3f16_1",
                "meta-llama_Llama-2-7b-chat-hf-q4f16_1",
                "google_gemma-2b-it-q3f16_1",
                "google_gemma-2b-it-q4f16_1",
                "google_gemma-7b-it-q4f16_1",
                "google_gemma-7b-it-q3f16_1",
            ]
    elif device["friendly_name"] == "Pixel 6a":
        if app == "MLCChat":
            models = [
                "mistralai_Mistral-7B-Instruct-v0.1-q3f16_1",
                "mistralai_Mistral-7B-Instruct-v0.1-q4f16_1",
                "TinyLlama_TinyLlama-1.1B-Chat-v0.5-q3f16_1",
                "TinyLlama_TinyLlama-1.1B-Chat-v0.5-q4f16_1",
                "TinyLlama_TinyLlama-1.1B-Chat-v0.5-q0f32",
                "stabilityai_stablelm-zephyr-3b-q3f16_1",
                "stabilityai_stablelm-zephyr-3b-q4f16_1",
            ]
        elif app == "MLCChat++":
            models = [
                "meta-llama_Llama-2-7b-chat-hf-q3f16_1",
                "meta-llama_Llama-2-7b-chat-hf-q4f16_1",
                "google_gemma-2b-it-q3f16_1",
                "google_gemma-2b-it-q4f16_1",
                "google_gemma-7b-it-q4f16_1",
                "google_gemma-7b-it-q3f16_1",
            ]
    else:
        raise ValueError(
            f"Unknown device with device_friendly_name '{device['friendly_name']}'"
        )

    idx = models.index(model_name)
    if idx == -1:
        sys.exit(f"Error: Unknown model '{model_name}'")

    return idx


def __get_select_model_coordinates(device, model_idx):

    if device["friendly_name"] == "Galaxy S23":
        offset = 412
        height = 150
        y_coord = model_idx * height + offset

    elif device["friendly_name"] == "Pixel 6a":
        y_coords = [436, 576, 700, 840, 975, 1096, 1196]
        y_coord = y_coords[model_idx]

    else:
        raise ValueError(
            f"Unknown device with device_friendly_name '{device['friendly_name']}'"
        )

    return 887, y_coord


def __get_reload_button_coordinates(device):

    if device["friendly_name"] == "Galaxy S23":
        return (983, 170)

    elif device["friendly_name"] == "Pixel 6a":
        return (1020, 215)

    raise ValueError(
        f"Unknown device with device_friendly_name '{device['friendly_name']}'"
    )


def __get_center_of_screen_coordinates(device):

    if device["friendly_name"] == "Galaxy S23":
        return (544, 1138)

    elif device["friendly_name"] == "Pixel 6a":
        return (511, 1204)

    raise ValueError(
        f"Unknown device with device_friendly_name '{device['friendly_name']}'"
    )


def __get_run_button_coordinates(device):

    if device["friendly_name"] == "Galaxy S23":
        return (846, 912)

    elif device["friendly_name"] == "Pixel 6a":
        return (783, 962)

    raise ValueError(
        f"Unknown device with device_friendly_name '{device['friendly_name']}'"
    )
