#!/usr/bin/python

# Note:   Evaluate the performance of different LLM apps on iOS devices.
# Author: Kleomenis Katevas (kkatevas@brave.com), Stefanos Laskaridis (stefanos@brave.com)
# Date:   02/10/2023

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

from utils.args_utils import parse_common_args, parse_ios_args
from utils.logging import Logger
from utils.utils import (cleanup_local_dir, edit_llmfarm_config,
                         edit_mlc_config, parse_model_args, run_process)

# paths
HOME = os.path.expanduser("~")
CURRENT_FILE_PATH = pathlib.Path(__file__).parent.resolve()
PATH = os.path.join(CURRENT_FILE_PATH, "../src/tools")
MELT_HOME = CURRENT_FILE_PATH / ".." / ".."
IOS_MOUNT = os.path.join(HOME, "ios-mount")
CONVERSATIONS_PATH = os.path.join(MELT_HOME, "src/prompts/input.json")
MODELS_DIR = {
    "com.brave.LLMFarmEval": os.path.join(MELT_HOME, "melt_models_converted"),
    "com.brave.mlc.Chat32": os.path.join(MELT_HOME, "melt_models_converted"),
    "com.brave.mlc.Chat33": os.path.join(MELT_HOME, "melt_models_converted"),
}

APP_IDS = {
    "LLMFarmEval": "com.brave.LLMFarmEval",
    "MLCChat": "com.brave.mlc.Chat32",
    "MLCChat++": "com.brave.mlc.Chat33",
}
logger = None
# load conversations file
path = os.path.dirname(os.path.abspath(__file__))
with open(CONVERSATIONS_PATH, encoding="utf-8") as f:
    conversations = json.load(f)


def run_experiment(
    device, app, runs, output, model, model_args, conversation_from, conversation_to
):

    # create output folder
    os.makedirs(output, exist_ok=True)

    # app id (needed for the mounting)
    app_id = APP_IDS[app]

    # execute the experiment but save the output in a file

    brightness = 50  # not in use anyway

    # # switch the device on
    # run_process(f"{PATH}/control-device.py -d '{device}' --switch on")
    # time.sleep(60 * 1)  # extra wait for the device after booting

    # Make sure we are not in the measuring mode
    run_process(
        f"{PATH}/control-device.py -d '{device}' --measuring stop -o '{output}'",
        capture_output=False,
        check=False,
    )
    time.sleep(1)

    # connect to the device using Bluetooth
    run_process(
        f"{PATH}/control-device.py -d '{device}' --bt connect", capture_output=False
    )
    time.sleep(5)

    # unlock the device to allow enhanced USB communication (and lock it back)
    run_process(f"{PATH}/control-device.py -d '{device}' --screen unlock")
    time.sleep(5)

    run_process(f"{PATH}/control-device.py -d '{device}' --screen lock")
    time.sleep(2)

    # cleanup past measurements
    cleanup(app_id)
    time.sleep(5)

    # copy app data
    app_id = APP_IDS[app]
    if app == "LLMFarmEval":
        copy_llmfarmeval_app_data(
            app_id=app_id,
            model_path=model,
            model_args=model_args,
            conversation_from=conversation_from,
            conversation_to=conversation_to,
        )

    elif app in ["MLCChat", "MLCChat++"]:
        copy_mlc_app_data(
            app_id=app_id,
            model_path=model,
            model_args=model_args,
            conversation_from=conversation_from,
            conversation_to=conversation_to,
        )

    else:
        sys.exit(f"Error: Unknown app '{app}'")

    # enable measuring mode
    run_process(
        f"{PATH}/control-device.py -d '{device}' --measuring start -o '{output}'",
        capture_output=False,
    )
    time.sleep(60 * 1)

    # run experiment
    run_process(
        f"{PATH}/control-device.py -d '{device}' -ee llm-evaluation-ios {brightness} {app} {model} {runs} -o '{output}'",
        capture_output=False,
    )
    time.sleep(10)

    # disable measuring mode
    run_process(
        f"{PATH}/control-device.py -d '{device}' --measuring stop", capture_output=False
    )
    time.sleep(5)

    # retrieve all data
    copy_measurements(app_id, output)

    # disconnect from the device's Bluetooth
    run_process(
        f"{PATH}/control-device.py -d '{device}' --bt disconnect", capture_output=False
    )
    time.sleep(5)

    # # switch the device off
    # run_process(f"{PATH}/control-device.py -d '{device}' --switch off", log_file=f)


def copy_measurements(app_id, output):

    # mount
    try:
        run_process(f"ifuse --documents '{app_id}' {IOS_MOUNT}")
    except subprocess.CalledProcessError:
        sys.exit(f"Error: Unable to mount '{app_id}' to {IOS_MOUNT}")

    # copy
    run_process(f"cp -r {IOS_MOUNT}/melt_measurements '{output}'")
    time.sleep(5)

    # unmount
    run_process(f"fusermount -u {IOS_MOUNT}")
    time.sleep(1)


def compute_total_prompts(conversation_from, conversation_to):
    return sum(
        len(sublist) for sublist in conversations[conversation_from:conversation_to]
    )


def copy_llmfarmeval_app_data(
    app_id, model_path, model_args, conversation_from, conversation_to
):

    Logger.get().info("Copying app data to the device...")

    # mount
    try:
        run_process(f"ifuse --documents '{app_id}' {IOS_MOUNT}")
    except subprocess.CalledProcessError:
        sys.exit(f"Error: Unable to mount '{app_id}' to {IOS_MOUNT}")

    # write input.json
    with open(os.path.join(IOS_MOUNT, "input.json"), "w", encoding="utf-8") as f:
        json.dump(
            conversations[conversation_from:conversation_to], f, indent=4)

    # find model name and copy it (can take time depending on the model size)

    # We can pre-copy to the device so that we don't wait that much.
    # Example:
    # model_file_path_host = ~/melt/melt_models_converted/TinyLlama_TinyLlama-1.1B-Chat-v0.5/tinyllama_tinyllama-1.1b-chat-v0.5-q3_k.gguf
    # model_dir_path_host = ~/melt/melt_models_converted/TinyLlama_TinyLlama-1.1B-Chat-v0.5
    # model_file = tinyllama_tinyllama-1.1b-chat-v0.5-q3_k.gguf
    # model_file_path_guest = {IOS_MOUNT}/tinyllama_tinyllama-1.1b-chat-v0.5-q3_k.gguf
    model_file_path_host = os.path.join(MODELS_DIR[app_id], model_path)
    model_dir_path_host = os.path.dirname(model_file_path_host)
    model_file = os.path.basename(model_file_path_host)
    model_file_path_guest = os.path.join(IOS_MOUNT, model_file)

    # File does not exist on the device
    if not os.path.isfile(model_file_path_guest):
        run_process(f"cp {model_file_path_host} {model_file_path_guest}")
    time.sleep(1)

    # copy model config
    model_config_path = os.path.join(model_dir_path_host, "model_config.json")
    run_process(f"cp {model_config_path} {IOS_MOUNT}")
    time.sleep(1)

    model_config_path = os.path.join(IOS_MOUNT, "model_config.json")
    edit_llmfarm_config(model_args, device="ios",
                        model_config_path=model_config_path)

    # unmount
    run_process(f"fusermount -u {IOS_MOUNT}")
    time.sleep(1)

    Logger.get().info("Done!")


def md5sum(file_path):
    hash_mdf = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_mdf.update(chunk)
    return hash_mdf.hexdigest()


def copy_mlc_app_data(
    app_id, model_path, model_args, conversation_from, conversation_to
):

    Logger.get().info("Copying app data to the device...")

    # mount
    try:
        run_process(f"ifuse --documents '{app_id}' {IOS_MOUNT}")
    except subprocess.CalledProcessError:
        sys.exit(f"Error: Unable to mount '{app_id}' to {IOS_MOUNT}")

    model_dir_path_host = os.path.join(MODELS_DIR[app_id], model_path)
    model_dir_path_guest = os.path.join(IOS_MOUNT, model_path)

    if not os.path.isdir(os.path.join(IOS_MOUNT, model_path)):
        # Copy model to device
        run_process(f"cp -r {model_dir_path_host} {model_dir_path_guest}")
        # Flatten the model directory
        run_process(
            f"mv {os.path.join(model_dir_path_host, 'params', '*')} {model_dir_path_guest}"
        )
    else:
        Logger.get().info("Model already exists on the device. Skipping copy ...")

    # write input.json
    with open(os.path.join(IOS_MOUNT, "input.json"), "w", encoding="utf-8") as f:
        json.dump(
            conversations[conversation_from:conversation_to], f, indent=4)
    time.sleep(5)

    model_config_path = os.path.join(
        IOS_MOUNT, model_path, "mlc-chat-config.json")
    edit_mlc_config(model_args, device="ios",
                    model_config_path=model_config_path)

    # unmount
    run_process(f"fusermount -u {IOS_MOUNT}")
    time.sleep(1)

    Logger.get().info("Done!")


def cleanup(app_id):

    # mount
    try:
        run_process(f"ifuse --documents '{app_id}' {IOS_MOUNT}")
    except subprocess.CalledProcessError:
        sys.exit(f"Error: Unable to mount '{app_id}' to {IOS_MOUNT}")

    # remove
    run_process(f"rm -rf {IOS_MOUNT}/*measurements*")
    run_process(f"mkdir -p {IOS_MOUNT}/melt_measurements")
    time.sleep(5)

    # unmount
    run_process(f"fusermount -u {IOS_MOUNT}")
    time.sleep(1)


def unmount():
    Logger.get().info(
        f"Attempting to unmount {IOS_MOUNT} in case mount already exist..."
    )

    try:
        run_process(f"fusermount -u {IOS_MOUNT}")
    except subprocess.CalledProcessError:
        Logger.get().info(f"All good, {IOS_MOUNT} is already unmounted.")
    else:
        Logger.get().info("Done")


def main(args):

    # parse arguments
    device = args.device
    app = args.app
    model = args.model
    conversation_from, conversation_to = args.conversation_from, args.conversation_to
    runs = args.runs
    output = args.output

    model_args = parse_model_args(args)

    # report details
    Logger.get().info("Running experiment with the following arguments:")
    Logger.get().info(json.dumps(vars(args), indent=4))

    # save the configuration
    with open(os.path.join(output, "configuration.json"), "w", encoding="utf-8") as f:
        json.dump(vars(args), f, indent=4)

    # attempt to unmount iOS, in case a mount already exist
    unmount()

    # run experiment
    run_experiment(
        device=device,
        app=app,
        runs=runs,
        output=output,
        model=model,
        model_args=model_args,
        conversation_from=conversation_from,
        conversation_to=conversation_to,
    )


# argument parser
def __parse_arguments(args):

    parser = argparse.ArgumentParser(
        description="Evaluate the performance of different LLM apps on iOS devices."
    )
    parse_ios_args(parser)
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
