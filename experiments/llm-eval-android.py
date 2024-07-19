#!/usr/bin/python

# Note:   Evaluate the performance of different LLM apps on Android devices.
# Author: Kleomenis Katevas (kkatevas@brave.com), Stefanos Laskaridis (stefanos@brave.com)
# Date:   26/10/2023

import argparse
import json
import os
import pathlib
import sys
import tempfile
import time

from utils.args_utils import parse_android_args, parse_common_args
from utils.logging import Logger
from utils.utils import (cleanup_local_dir, edit_llamacpp_config,
                         edit_mlc_config, parse_model_args, run_process)

# paths
HOME = os.path.expanduser("~")
CURRENT_FILE_PATH = pathlib.Path(__file__).parent.resolve()

MELT_HOME = CURRENT_FILE_PATH / ".." / ".."
PATH = os.path.join(CURRENT_FILE_PATH, "../src/tools")
CONVERSATIONS_PATH = os.path.join(MELT_HOME, "src/prompts/conversations.json")

MLC_EVENTS_ROOT = "/storage/emulated/0/Documents/melt_measurements/"
LLAMACPP_EVENTS_ROOT = "/data/local/tmp/melt_measurements/"
APP_TO_PACKAGE = {"MLCChat": "ai.mlc.mlcchat", "MLCChat++": "ai.mlc.mlcchat32"}

# load conversations file
with open(CONVERSATIONS_PATH, encoding="utf-8") as f:
    conversations = json.load(f)


def filter_conversations(conversations, conversation_from, conversation_to):
    return conversations[conversation_from:conversation_to]


def run_experiment(
    device,
    brightness,
    app,
    runs,
    output,
    model_name,
    model_args,
    conversation_from,
    conversation_to,
    n_threads=1,
):

    # create output folder
    os.makedirs(output, exist_ok=True)

    # total prompts in the given range (from, to)
    filtered_conversations = filter_conversations(
        conversations, conversation_from, conversation_to
    )

    # # switch the device on
    # run_process(f"{PATH}/control-device.py -d '{device}' --switch on")
    # time.sleep(60 * 1)  # wait for device to be available

    # remove all previous logs
    cleanup(app)
    # copy model data and config first
    copy_app_data(
        app,
        model_name=model_name,
        model_args=model_args,
        conversations=filtered_conversations,
    )

    # Make sure we are not in the measuring mode
    run_process(
        f"{PATH}/control-device.py -d '{device}' --measuring stop -o '{output}'",
        capture_output=False,
        check=False,
    )
    time.sleep(1)

    # enable measuring mode
    run_process(
        f"{PATH}/control-device.py -d '{device}' --measuring start -o '{output}'",
        capture_output=False,
    )
    time.sleep(60 * 1)

    # run experiment
    if app in ["MLCChat", "MLCChat++"]:
        # Kill the app first in case it is already running.
        run_process(f"adb shell am force-stop {APP_TO_PACKAGE[app]}")
        run_process(
            f"{PATH}/control-device.py -d '{device}' -ee llm-evaluation-android {brightness} {app} {model_name} {runs} -o '{output}'",
            capture_output=False,
        )
    elif app == "LlamaCpp":
        run_process(
            f"{PATH}/control-device.py -d '{device}' -ee llm-evaluation-android {brightness} {app} {model_name} {runs} {conversation_from} {conversation_to} '{output}' -o '{output}' '{n_threads}'",
            capture_output=False,
        )
    else:
        sys.exit(f"Error: Unknown app '{app}'")
    time.sleep(10)

    # disable measuring mode
    run_process(
        f"{PATH}/control-device.py -d '{device}' --measuring stop", capture_output=False
    )
    time.sleep(5)

    if app in ["MLCChat", "MLCChat++"]:
        src_dir_guest = MLC_EVENTS_ROOT
        # Kill the app again.
        run_process(f"adb shell am force-stop {APP_TO_PACKAGE[app]}")
    elif app == "LlamaCpp":
        src_dir_guest = LLAMACPP_EVENTS_ROOT
    else:
        sys.exit(f"Error: Unknown app '{app}'")

    run_process(f"adb pull {src_dir_guest} '{output}'")
    # # switch the device off
    # run_process(f"{PATH}/control-device.py -d '{device}' --switch off")


def compute_total_prompts(filtered_conversations):
    return sum(len(sublist) for sublist in filtered_conversations)


def copy_app_data(app, model_name, model_args, conversations=None):

    Logger.get().info("Copying app data to the device...")
    target_file = None
    app_path = ""
    if app in ["MLCChat", "MLCChat++"]:
        app_path = f"/storage/emulated/0/Android/data/{APP_TO_PACKAGE[app]}/files/"
        target_file = "input.json"
        fq_target = os.path.join(app_path, target_file)
        # copy conversations
        if conversations:
            with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
                # Persist to json file
                src_filename = f.name
                json.dump(conversations, f, indent=4)
            # push to device
            run_process(f"adb push {src_filename} {fq_target}")
    elif app == "LlamaCpp":
        pass  # no-op, handled by expect script
    else:
        sys.exit(f"Error: Unknown app '{app}'")

    # change model config as needed
    if app in ["MLCChat", "MLCChat++"]:
        model_config_path = os.path.join(
            app_path, model_name, "mlc-chat-config.json")
        edit_mlc_config(
            model_args, device="android", model_config_path=model_config_path
        )
    elif app == "LlamaCpp":
        app_path = "/data/local/tmp/"
        model_dir = os.path.dirname(os.path.join(app_path, model_name))
        model_config_path = os.path.join(model_dir, "llama_main_args.txt")
        edit_llamacpp_config(
            model_args, device="android", model_config_path=model_config_path
        )

    # create results folder
    if app in ["MLCChat", "MLCChat++"]:
        run_process(f'adb shell "mkdir -p {MLC_EVENTS_ROOT}"')
    elif app == "LlamaCpp":
        run_process(f'adb shell "mkdir -p {LLAMACPP_EVENTS_ROOT}"')

    Logger.get().info("Done!")


def cleanup(app):
    Logger.get().info("Deleting previous measurements ...")
    if app in ["MLCChat", "MLCChat++"]:
        run_process(f'adb shell "rm -rf {MLC_EVENTS_ROOT}"')
    elif app == "LlamaCpp":
        run_process(f'adb shell "rm -rf {LLAMACPP_EVENTS_ROOT}"')
    Logger.get().info("Done!")


def main(args):

    # parse arguments
    device = args.device
    brightness = args.brightness
    app = args.app
    model_name = args.model
    conversation_from, conversation_to = args.conversation_from, args.conversation_to
    runs = args.runs
    output = args.output
    n_threads = args.n_threads

    model_args = parse_model_args(args)

    # report details
    Logger.get().info("Running experiment with the following arguments:")
    Logger.get().info(json.dumps(vars(args), indent=4))

    # save the configuration
    with open(os.path.join(output, "configuration.json"), "w", encoding="utf-8") as f:
        json.dump(vars(args), f, indent=4)

    # run experiment
    run_experiment(
        device=device,
        brightness=brightness,
        app=app,
        runs=runs,
        output=output,
        model_name=model_name,
        model_args=model_args,
        conversation_from=conversation_from,
        conversation_to=conversation_to,
        n_threads=n_threads,
    )


# argument parser
def __parse_arguments(args):

    parser = argparse.ArgumentParser(
        description="Evaluate the performance of different LLM apps on Android devices."
    )

    parse_android_args(parser)
    parse_common_args(parser)
    parsed = parser.parse_args(args)

    return parsed


if __name__ == "__main__":
    # parse args
    arguments = __parse_arguments(sys.argv[1:])
    cleanup_local_dir(arguments.output)
    Logger.setup_logging(
        loglevel=arguments.loglevel,
        logfile=os.path.join(arguments.output, "output.txt"),
    )
    main(arguments)
