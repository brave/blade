# Note:   Measure the performance of On-Device LLMs on iOS
# Author: Kleomenis Katevas (kkatevas@brave.com), Stefanos Laskaridis (stefanos@brave.com)
# Date:   02/10/2023

import json
import os
import sys
import time
from datetime import datetime

from libs import rest_await, tools
from libs.automation import bt_ios_commands as cmd

SUPPORTED_APPS = ["LLMFarmEval", "MLCChat", "MLCChat++"]

# start REST API server
REST_AWAIT_SERVER = rest_await.RestAwaitApp()


def check_device(device):

    if device["os"] != "iOS":
        print("Error: Device is not iOS.")
        return False

    return True


def check_arguments(arguments):

    # check number of arguments passed
    if len(arguments) < 4:
        print(f"Error: Wrong number of arguments. Usage: {usage()}")
        return False

    # check brightness range
    brightness = int(arguments[0])
    if brightness < 0 or brightness > 255:
        print(
            f"Wrong brightness value '{brightness}'. Should be in the range [0, 255]")
        return False

    # check apps
    test_app = arguments[1]
    if test_app not in SUPPORTED_APPS:
        print(
            f"Unsupported app '{test_app}'. Should be one of: {SUPPORTED_APPS}.")
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

    return True


def setup_device(device, tslogger, arguments):

    tslogger.log_begin("Setup")

    # always at the beginning of this method
    cmd.setup_device(device)

    # screen on and unlock device
    cmd.unlock_device(device)
    time.sleep(3)

    # set brightness level
    brightness = int(arguments[0])
    # cmd.set_brightness(device, brightness)  # TODO: not available

    # wait until brightness is set
    time.sleep(5)

    tslogger.log_end("Setup")


def run_experiment(device, tslogger, arguments):

    # parameters
    test_app = arguments[1]
    model_name = arguments[2]
    runs = int(arguments[3])

    tslogger.log_begin("Experiment")

    for run in range(runs):

        # open the app
        if test_app == "MLCChat++":
            cmd.open_app(device, "MLChat++")
        else:
            cmd.open_app(device, test_app)
        time.sleep(10)

        if test_app == "LLMFarmEval":
            automate_llmfarmeval(device, tslogger, model_name, run)

        elif test_app in ["MLCChat", "MLCChat++"]:
            automate_mlcchat(device, tslogger, model_name, run, test_app)

        else:
            sys.exit(f"Error: Unknown test_app '{test_app}'")

        tslogger.log_end(f"Run_{run}")
        time.sleep(5)

    tslogger.log_end("Experiment")


def automate_llmfarmeval(device, tslogger, model_name, run):

    tslogger.log_begin(f"Run_{run}")

    # type filename
    filename = f"melt_measurements/measurements_iter{run}"
    cmd.type_text(device, filename)
    time.sleep(1)

    # type model
    model_name_to_type = model_name.split("/")[-1]
    cmd.btk.send_hid_keys(["KEY_TAB"])
    time.sleep(1)
    cmd.btk.send_hid_keys(["KEY_TAB"])
    time.sleep(1)
    cmd.btk.send_hid_keys(["KEY_SPACE"])
    time.sleep(1)
    cmd.type_text(device, model_name_to_type)
    time.sleep(1)

    # start measuring
    cmd.btk.send_hid_keys(["KEY_TAB"])
    time.sleep(1)
    cmd.btk.send_hid_keys(["KEY_SPACE"])

    # wait until the app notifies that experiment is done
    REST_AWAIT_SERVER.set_await(timeout=3600)
    time.sleep(5)
    # app will exit automatically when done

    # close app
    cmd.btk.send_hid_keys(["KEY_TAB"])
    time.sleep(1)
    cmd.btk.send_hid_keys(["KEY_TAB"])
    time.sleep(1)
    cmd.btk.send_hid_keys(["KEY_SPACE"])
    time.sleep(5)


def automate_mlcchat(device, tslogger, model_name, run, app):

    model_idx = __get_model_idx(model_name, device, app)

    tslogger.log_begin(f"Run_{run}")

    if app == "MLCChat":
        # an error message appears, skip it
        cmd.btk.send_hid_keys(["KEY_DOWN"])
        time.sleep(1)
        cmd.btk.send_hid_keys(["KEY_SPACE"])
        time.sleep(1)

    if app == "MLCChat++":
        model_idx += 1

    # select model based on the index (1st model is already selected)
    for _ in range(model_idx):
        cmd.btk.send_hid_keys(["KEY_DOWN"])
        time.sleep(1)

    # choose model
    cmd.btk.send_hid_keys(["KEY_SPACE"])
    time.sleep(5)

    # press Automate
    cmd.btk.send_hid_keys(["KEY_TAB"])
    time.sleep(1)
    cmd.btk.send_hid_keys(["KEY_TAB"])
    time.sleep(1)
    cmd.btk.send_hid_keys(["KEY_TAB"])
    time.sleep(1)
    cmd.btk.send_hid_keys(["KEY_SPACE"])
    time.sleep(5)

    # type filename
    filename = f"melt_measurements/measurements_iter{run}"
    cmd.type_text(device, filename)
    time.sleep(1)
    cmd.btk.send_hid_keys(["KEY_TAB"])
    time.sleep(1)
    cmd.btk.send_hid_keys(["KEY_TAB"])
    time.sleep(1)
    cmd.btk.send_hid_keys(["KEY_RIGHT"])
    time.sleep(1)
    cmd.btk.send_hid_keys(["KEY_SPACE"])
    time.sleep(1)

    # wait until the app notifies that experiment is done
    REST_AWAIT_SERVER.set_await(timeout=3600)
    time.sleep(5)
    # app will exit automatically when done


def cleanup_device(device, tslogger, arguments):

    tslogger.log_begin("Cleanup")

    # always at the end of this method
    cmd.cleanup_device(device)

    tslogger.log_end("Cleanup")


def automation_type():
    return "BT-iOS"


def usage():
    return "llm-evaluation-ios <brightness> <test-app> <model-name> <runs>"


def description():
    return "Measures the performance of On-Device LLMs on iOS"


def __get_model_idx(model_name, device, app):

    if device["friendly_name"] == "iPhone 14 Pro":
        if app == "MLCChat":
            models = [
                "TinyLlama_TinyLlama-1.1B-Chat-v0.5-q4f16_1",
                "Llama-2-7b-chat-hf-q3f16_1",
                "stabilityai_stablelm-zephyr-3b-q4f16_1",
                "stabilityai_stablelm-zephyr-3b-q3f16_1",
                "TinyLlama_TinyLlama-1.1B-Chat-v0.5-q3f16_1",
                "mistralai_Mistral-7B-Instruct-v0.1-q4f16_1",
                "mistralai_Mistral-7B-Instruct-v0.1-q3f16_1",
                "meta-llama_Llama-2-7b-chat-hf-q4f16_1",
                "TinyLlama_TinyLlama-1.1B-Chat-v0.5-q0f32",
            ]
        elif app == "MLCChat++":
            models = [
                "meta-llama_Llama-2-7b-chat-hf-q3f16_1",
                "google_gemma-2b-it-q3f16_1",
                "google_gemma-2b-it-q4f16_1",
            ]
    elif device["friendly_name"] == "iPhone SE":
        if app == "MLCChat":
            models = [
                "TinyLlama_TinyLlama-1.1B-Chat-v0.5-q4f16_1",
                "stabilityai_stablelm-zephyr-3b-q4f16_1",
                "stabilityai_stablelm-zephyr-3b-q3f16_1",
                "TinyLlama_TinyLlama-1.1B-Chat-v0.5-q3f16_1",
                "mistralai_Mistral-7B-Instruct-v0.1-q4f16_1",
                "mistralai_Mistral-7B-Instruct-v0.1-q3f16_1",
            ]
        elif app == "MLCChat++":
            models = [
                "google_gemma-2b-it-q3f16_1",
                "google_gemma-2b-it-q4f16_1",
            ]
    else:
        raise ValueError(
            f"Unknown device with device_friendly_name '{device['friendly_name']}'"
        )

    idx = models.index(model_name)
    if idx == -1:
        sys.exit(f"Error: Unknown model '{model_name}'")

    return idx
