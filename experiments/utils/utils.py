# Note:   Utility functions for running processes and editing model configs.
# Author: Stefanos Laskaridis (stefanos@brave.com)


import json
import os
import shutil
import subprocess

from .logging import Logger

NUMBER_REGEX = "[0-9]+(\\.[0-9]*)?"


def parse_model_args(args):
    model_args = {
        "max_gen_len": args.max_gen_len,
        "max_context_size": args.max_context_size,
        "prefill_chunk_size": args.prefill_chunk_size,
        "input_token_batching": args.input_token_batching,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "top_k": args.top_k,
        "repeat_penalty": args.repeat_penalty,
    }

    if hasattr(args, "cpu"):
        model_args["use_metal"] = not args.cpu

    if hasattr(args, "n_threads") and args.n_threads is not None:
        model_args["n_threads"] = args.n_threads

    return model_args


def run_process(command, capture_output=True, check=True):
    Logger.get().info(f"Running command: {command}")
    if capture_output:
        try:
            p = subprocess.run(
                command, capture_output=True, shell=True, check=check, text=True
            )
        except subprocess.CalledProcessError as e:
            Logger.get().error(f"Command failed: {e}")
            if e.stdout:
                Logger.get().error(f"stdout: {e.stdout}")
            if e.stderr:
                Logger.get().error(f"sterr: {e.stderr}")
            raise e
        if p.stdout:
            Logger.get().info(f"{p.stdout}")
        if p.stderr:
            Logger.get().info(f"{p.stderr}")
    else:
        with open(Logger.logfile, "a", buffering=1, encoding="utf-8") as f:
            subprocess.run(
                command, stdout=f, stderr=f, shell=True, check=check, text=True
            )


def edit_mlc_config(model_args, device, model_config_path):
    if device == "android":
        command_wrapper = 'adb shell "{command}"'
    elif device == "ios":
        command_wrapper = "{command}"

    for model_arg, value in model_args.items():
        if value is not None:
            if model_arg == "max_context_size":
                src_regex = f'(\\"sliding_window_size\\": | \\"context_window_size\\": ){NUMBER_REGEX}(,)?'
                dst_regex = f"\\1{value}\\3"
            elif model_arg == "prefill_chunk_size":
                src_regex = f'(\\"prefill_chunk_size\\": ){NUMBER_REGEX}(,)?'
                dst_regex = f"\\1{value}\\3"
            elif model_arg == "repeat_penalty":
                src_regex = f'(\\"repetition_penalty\\": ){NUMBER_REGEX}(,)?'
                dst_regex = f"\\1{value}\\3"
            elif model_arg in ["max_gen_len", "temperature", "top_p"]:
                src_regex = f'\\"{model_arg}\\": {NUMBER_REGEX}(,)?'
                dst_regex = f'\\"{model_arg}\\": {value}\\2'
            else:
                Logger.get().info(
                    f"Invalid model arg {model_arg}, omitting ...")
                continue
            run_process(
                command_wrapper.format(
                    command=f"sed -i -r 's/{src_regex}/{dst_regex}/' {model_config_path}"
                )
            )


def edit_llamacpp_config(model_args, device, model_config_path):
    assert device == "android"
    for model_arg, value in model_args.items():
        if value is not None:
            if model_arg == "max_context_size":
                src_regex = f"(-c ){NUMBER_REGEX}"
                dst_regex = f"\\1{value}"
            elif model_arg == "max_gen_len":
                src_regex = f"(-n ){NUMBER_REGEX}"
                dst_regex = f"\\1{value}"
            elif model_arg == "input_token_batching":
                src_regex = f"(-b ){NUMBER_REGEX}"
                dst_regex = f"\\1{value}"
            elif model_arg == "temperature":
                src_regex = f"(--temp ){NUMBER_REGEX}"
                dst_regex = f"\\1{value}"
            elif model_arg == "top_p":
                src_regex = f"(--top-p ){NUMBER_REGEX}"
                dst_regex = f"\\1{value}"
            elif model_arg == "top_k":
                src_regex = f"(--top-k ){NUMBER_REGEX}"
                dst_regex = f"\\1{value}"
            elif model_arg == "repeat_penalty":
                src_regex = f"(--repeat-penalty ){NUMBER_REGEX}"
                dst_regex = f"\\1{value}"
            else:
                Logger.get().info(
                    f"Invalid model arg {model_arg}, omitting ...")
                continue
        run_process(
            f"adb shell \"sed -i -r 's/{src_regex}/{dst_regex}/' {model_config_path}\""
        )


def edit_llmfarm_config(model_args, device, model_config_path):
    assert device == "ios"
    with open(model_config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    for model_arg, value in model_args.items():
        if value is not None:
            if model_arg == "max_context_size":
                if config["generation"].get("max_window_size", None) is not None:
                    config["generation"]["max_window_size"] = value
                else:
                    config["generation"]["sliding_window"] = value
            elif model_arg == "max_gen_len":
                config["generation"]["max_gen_len"] = value
            elif model_arg == "input_token_batching":
                config["sampling"]["n_batch"] = value
            elif model_arg == "repeat_penalty":
                config["sampling"]["repetition_penalty"] = value
            elif model_arg in [
                "max_gen_len",
                "temperature",
                "top_p",
                "top_k",
            ]:
                config["sampling"][model_arg] = value
            elif model_arg in [
                "use_metal",
                "n_threads",
            ]:
                config["generation"][model_arg] = value
            else:
                Logger.get().info(
                    f"Invalid model arg {model_arg}, omitting ...")
                continue
    with open(model_config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


def cleanup_local_dir(output):
    # clean output folder if exists
    path_existed = os.path.exists(output)
    if path_existed:
        # This needs to be a print as the logger has not been initialised yet
        print(f"Previous measurements found. Deleting ...")
        shutil.rmtree(output)

    # create output folder
    os.makedirs(output, exist_ok=True)

    return path_existed
