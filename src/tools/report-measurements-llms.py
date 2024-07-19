#!/usr/bin/python

# Note:   Report measurements from an executed on-device LLM experiment.
# Author: Kleomenis Katevas (kkatevas@brave.com), Stefanos Laskaridis (stefanos@brave.com)
# Date:   16/03/2023


import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime

import numpy as np
import pandas as pd
from libs import powerlib, tools
from matplotlib import pyplot as plt


def __get_value_from_string(input_string, sep_after, sep_before):

    idx_to = input_string.rfind(sep_after)

    if idx_to == -1:
        return -1

    idx_from = input_string[:idx_to].rfind(sep_before) + 1

    idx_from = max(0, idx_from)

    return input_string[idx_from:idx_to]


def __parse_datetime(datetime_any):
    # in case date is in string format, convert to epoch

    if isinstance(datetime_any, str):  # e.g., "2024-02-05T15:09:18.386Z"
        dateformat = "%Y-%m-%dT%H:%M:%S.%fZ"
        dt = datetime.strptime(datetime_any, dateformat)
        return dt.timestamp()

    # else
    return datetime_any


def __get_iter_from_filename(filename):
    # e.g., from "path/to/measurements_iter0_conv1.csv" return int(0)

    match = re.search(r"iter(\d+)", filename)
    if match is None:
        sys.exit(
            f"Error: Could not infer iteration from filename '{filename}'.")
    return int(match.group(1))


def __get_conv_from_filename(filename):
    # e.g., from "path/to/measurements_iter0_conv1.csv" return int(1)

    match = re.search(r"conv(\d+)", filename)
    if match is None:
        sys.exit(
            f"Error: Could not infer conversation from filename '{filename}'.")
    return int(match.group(1))


def load_ts_data(filepath):

    if not os.path.isfile(filepath):
        sys.exit(f"Error: Could not read '{filepath}'.")

    df = pd.read_csv(filepath, index_col=0)

    return df


def load_monsoon_data(filepath):

    # load data
    colnames = ["timestamp", "current", "voltage", "unknown"]  # last is empty
    df = pd.read_csv(filepath, names=colnames, header=None, index_col=None)
    df.drop("unknown", axis=1, inplace=True)

    # get monsoon start time
    path = os.path.dirname(filepath)
    start_time = tools.read_value_from_file(os.path.join(path, ".t_monsoon"))
    if start_time is None:
        sys.exit("Error: Could not read start time from file.")
    start_time = float(start_time)

    # fix datetime
    df.timestamp = df.timestamp + start_time

    # compute power
    df["power"] = df["current"] * df["voltage"]  # in mW
    df["power"] /= 1000  # in W

    return df


def load_adb_data(filepath):  # currently unused

    if not os.path.isfile(filepath):
        return None

    # load data
    df = pd.read_csv(filepath, index_col=None)

    # drop nan entries
    df.dropna(inplace=True)

    # convert units
    df["current"] = df["current"] / 1000000  # to mA
    df["current"] = 0 - df["current"]  # to positive
    df["voltage"] = df["voltage"] / 1000  # to V

    return df


def compute_model_performance_metrics(filepath, iteration, mdf):

    # load json file
    with open(filepath, encoding="utf-8") as f:
        metrics = json.load(f)

    records_list = []
    for conversation, metric in enumerate(metrics):

        # [0] since we always save one per file anyway
        model_load_time = metric["modelLoadTime"]

        # properties
        start_time = __parse_datetime(model_load_time["start"])
        duration = model_load_time["duration"]
        end_time = start_time + duration

        # performance
        monsoon_df_trimmed = mdf[
            (mdf.timestamp > start_time) & (mdf.timestamp < end_time)
        ]
        total_energy, total_discharge = powerlib.compute_power_performance(
            monsoon_df_trimmed
        )

        # create Series
        record = {
            "iteration": iteration,
            "conversation": conversation,
            "duration (sec)": duration,
            "energy (mWh)": total_energy,
            "discharge (mAh)": total_discharge,
        }

        records_list.append(record)

    return pd.DataFrame.from_records(records_list)


def compute_llamacpp_performance_metrics(
    filepath_csv, filepath_txt, iteration, conversation, monsoon
):

    # this is the measurements equivalent file for LlamaCpp (but in csv format)
    df = load_ts_data(filepath_csv)

    # load txt
    with open(filepath_txt, encoding="utf-8", errors="ignore") as f:
        txt_lines = f.readlines()

    records_list = []
    load_model_list = []

    # Read all relevant timings
    TOTAL_STATS_LINES_PER_PROMPT = 5
    llama_cpp_stats = []
    regex = "llama_print_timings:.*"
    for line in txt_lines:
        if re.match(regex, line):
            llama_cpp_stats.append(line)
    first_idx = (
        len(llama_cpp_stats) // TOTAL_STATS_LINES_PER_PROMPT - (len(df) - 1)
    ) * TOTAL_STATS_LINES_PER_PROMPT

    for start_time, row in df.iterrows():

        # properties
        duration = row.duration
        end_time = start_time + duration

        # performance
        monsoon_df_trimmed = monsoon[
            (monsoon.timestamp > start_time) & (monsoon.timestamp < end_time)
        ]
        total_energy, total_discharge = powerlib.compute_power_performance(
            monsoon_df_trimmed
        )

        if row.state == "load_model":
            load_model_list.append(
                {
                    "iteration": iteration,
                    "conversation": conversation,
                    "duration (sec)": duration,
                    "energy (mWh)": total_energy,
                    "discharge (mAh)": total_discharge,
                }
            )

        else:
            # get prompt index
            prompt_idx = (
                df.index.get_loc(start_time) - 1
            )  # 1st is always 'load_model' event
            real_idx = first_idx + prompt_idx * TOTAL_STATS_LINES_PER_PROMPT

            # get relevant metrics from txt file
            stats = llama_cpp_stats[real_idx: real_idx +
                                    TOTAL_STATS_LINES_PER_PROMPT]

            # example stats:
            # llama_print_timings:        load time =     525.17 ms
            # llama_print_timings:      sample time =       4.28 ms /    21 runs   (    0.20 ms per token,  4909.98 tokens per second)
            # llama_print_timings: prompt eval time =    2501.52 ms /    51 tokens (   49.05 ms per token,    20.39 tokens per second)
            # llama_print_timings:        eval time =    1041.43 ms /    20 runs   (   52.07 ms per token,    19.20 tokens per second)
            # llama_print_timings:       total time =   11653.83 ms
            original_session_tokens = -1  # not available
            input_tokens = int(
                __get_value_from_string(stats[2], "tokens (", "/")
            )  # 51 tokens
            output_tokens = int(
                __get_value_from_string(stats[3], "runs", "/")
            )  # 20 tokens
            prefill_tps = float(
                __get_value_from_string(stats[2], "tokens per second", ",")
            )  # 20.39 tokens per second
            tps = float(
                __get_value_from_string(stats[3], "tokens per second", ",")
            )  # 19.20 tokens per second
            energy_pt = total_energy / output_tokens
            discharge_pt = total_discharge / output_tokens

            records_list.append(
                {
                    "iteration": iteration,
                    "conversation": conversation,
                    "prompt": prompt_idx,
                    "duration (sec)": duration,
                    "original_session_tokens": original_session_tokens,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "prefill_tps": prefill_tps,
                    "tps": tps,
                    "energy_pt (mWh)": energy_pt,
                    "discharge_pt (mAh)": discharge_pt,
                }
            )

    return pd.DataFrame.from_records(load_model_list), pd.DataFrame.from_records(
        records_list
    )


def compute_inference_performance_metrics(app, filepath, iteration, mdf):

    # load json file
    with open(filepath, encoding="utf-8") as f:
        conversations = json.load(f)

    # dirty fix for different json formats
    record_label = "questionRecords"
    if record_label not in conversations[0].keys():
        record_label = "chatRecords"

    records_list = []

    for conversation_idx, conversation in enumerate(conversations):

        # read timing data (if available)
        melt_measurements_path = os.path.dirname(filepath)
        timing_filepath = os.path.join(
            melt_measurements_path,
            f"measurements_iter{iteration}_timing_conv{conversation_idx}.csv",
        )
        if os.path.isfile(timing_filepath):
            dft = pd.read_csv(timing_filepath, sep=",")
        else:
            dft = None

        for prompt_idx, prompt in enumerate(conversation[record_label]):

            # properties
            start_time = __parse_datetime(prompt["time"]["start"])
            duration = prompt["time"]["duration"]
            end_time = start_time + duration
            original_session_tokens = prompt["original_session_tokens"]
            input_tokens = prompt["input_tokens"]
            output_tokens = prompt["output_tokens"]

            if output_tokens == 0:
                tps = -1

            else:

                if app == "LLMFarmEval":
                    # this is llamacpp, so get it from the timing data

                    if dft is None:
                        sys.exit(
                            f"Error: Could not find timing data for iteration {iteration} and conversation {conversation_idx}."
                        )

                    # get the relevant timings
                    timings = dft.iloc[prompt_idx]

                    input_tokens = timings.n_p_eval
                    output_tokens = timings.n_eval
                    prefill_tps = 1e3 / timings.t_p_eval_ms * timings.n_p_eval
                    tps = 1e3 / timings.t_eval_ms * timings.n_eval

                elif app.startswith("MLCChat"):

                    if len(prompt["runtimeStats"]) == 0:

                        micro_filepath = filepath.replace(
                            ".json", f"_conv{conversation_idx}.csv"
                        )
                        micro_df = pd.read_csv(
                            micro_filepath, header=None, names=["event", "timestamp"]
                        )

                        prefill_start = micro_df[
                            micro_df.event == f"prefill.{prompt_idx}.start"
                        ]
                        prefill_end = micro_df[
                            micro_df.event == f"prefill.{prompt_idx}.end"
                        ]

                        generation_start = micro_df[
                            micro_df.event == f"generate.{prompt_idx}.start"
                        ]
                        generation_end = micro_df[
                            micro_df.event == f"generate.{prompt_idx}.end"
                        ]
                        try:
                            prefill_duration = (
                                prefill_end.timestamp.values[0]
                                - prefill_start.timestamp.values[0]
                            ) * 1e-9
                            generation_duration = (
                                generation_end.timestamp.values[0]
                                - generation_start.timestamp.values[0]
                            ) * 1e-9
                        except IndexError as e:
                            print(e)
                            print(f"{prompt_idx=}, {len(conversations)=}")
                            print(micro_df)
                            exit(1)

                        tps = output_tokens / generation_duration
                        prefill_tps = input_tokens / prefill_duration

                    else:  # read from the extra info
                        runtime_stats = json.loads(prompt["runtimeStats"])
                        prefill_tps = runtime_stats["prefill"]["throughput"]
                        if prefill_tps:
                            prefill_tps = float(prefill_tps.split()[0])
                        else:
                            prefill_tps = input_tokens / duration
                        tps_s = runtime_stats["decode"]["throughput"]
                        if tps_s:
                            tps = float(tps_s.split()[0])
                        else:  # Fallback, but this is wrong.
                            tps = output_tokens / duration

            # performance
            monsoon_df_trimmed = mdf[
                (mdf.timestamp > start_time) & (mdf.timestamp < end_time)
            ]
            total_energy, total_discharge = powerlib.compute_power_performance(
                monsoon_df_trimmed
            )

            if output_tokens == 0:
                energy_pt = -1
                discharge_pt = -1
            else:
                energy_pt = total_energy / output_tokens
                discharge_pt = total_discharge / output_tokens

            # create Series
            record = {
                "iteration": iteration,
                "conversation": conversation_idx,
                "prompt": prompt_idx,
                "duration (sec)": duration,
                "original_session_tokens": original_session_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "prefill_tps": prefill_tps,
                "tps": tps,
                "energy_pt (mWh)": energy_pt,
                "discharge_pt (mAh)": discharge_pt,
            }

            records_list.append(record)

    return pd.DataFrame.from_records(records_list)


def filter_dfs(df, entries):

    if df is None:
        return None

    dfs = []
    for _, entry in entries.iterrows():

        # trim df by row.time_start and row.time_end
        df_slice = df[
            (df.timestamp > entry.time_start) & (df.timestamp < entry.time_end)
        ]

        if len(df_slice) != 0:
            dfs.append(df_slice)

    return pd.concat(dfs)


def plot_performance(df, y, yaxis, title, filename):

    ax = df.plot(x="timestamp", y=y, title=title)
    ax.set_xlabel("Time")
    ax.set_ylabel(yaxis)

    # save
    ax.figure.savefig(filename)
    ax.figure.clf()


def plot_annotated_performance_metrics(
    conv_data, df, dft, mdf, app, path, no_legend=False
):

    # Colormap
    cmap = plt.get_cmap("twilight")
    vspace = np.linspace(0, 1, 10)
    colors = cmap(vspace)

    # fontsize
    plt.rcParams.update({"font.size": 16})

    # apply rolling mean to smooth the power signal
    mdf = mdf.rolling(window=500).mean()
    mdf.dropna(inplace=True)

    # will use this for x-axis
    x_offset = mdf["timestamp"].min()
    mdf["timestamp_reset"] = mdf["timestamp"] - x_offset

    # init plot
    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(10, 5))

    # grey line (all except prompts and load_model)
    other_events = []
    last_event = mdf.timestamp.min()

    # plot load_model event
    if app == "LLMFarmEval":
        load_model_label = "load_model"
    elif app == "MLCChat":
        load_model_label = "reload.0"
    else:
        sys.exit(f"Error: Unsupported app '{app}'.")
    load_model_start = (
        df.loc[load_model_label + ".start"].values[0] /
        1_000_000_000 - x_offset
    )
    load_model_end = (
        df.loc[load_model_label + ".end"].values[0] / 1_000_000_000 - x_offset
    )
    ax.fill_between(
        mdf["timestamp_reset"],
        mdf["power"],
        where=(mdf.timestamp_reset >= load_model_start)
        & (mdf.timestamp_reset <= load_model_end),
        alpha=0.6,
        color=colors[3],
        hatch="X",
        linewidth=0.1,
    )
    plt.plot(
        mdf[
            (mdf.timestamp_reset > load_model_start)
            & (mdf.timestamp_reset < load_model_end)
        ].timestamp_reset,
        mdf[
            (mdf.timestamp_reset > load_model_start)
            & (mdf.timestamp_reset < load_model_end)
        ].power,
        label="load model",
        color=colors[3],
        linewidth=0.5,
    )
    other_events.append((last_event, load_model_start))
    last_event = load_model_end

    # choose the plot that will be presented in detail
    detailed_prompt_ids = [
        len(conv_data["questionRecords"]) - 1]  # last prompt
    # detailed_prompt_ids = list(range(len(conv_data['questionRecords'])))  # all prompts

    # plot prompt annotations (expect for the detailed ones)
    for idx, prompt in enumerate(conv_data["questionRecords"]):

        start = prompt["time"]["start"] - x_offset
        end = start + prompt["time"]["duration"]

        # store for other events
        other_events.append((last_event, start))
        last_event = end

        # ignore chosen prompt (will be annotated separately)
        if idx in detailed_prompt_ids:
            continue

        # highlight
        ax.fill_between(
            mdf["timestamp_reset"],
            mdf["power"],
            where=(mdf.timestamp_reset >= start) & (
                mdf.timestamp_reset <= end),
            alpha=0.8,
            color=colors[1],
            hatch="x",
        )
        legend_label = "previous inferences" if idx == 0 else None
        plt.plot(
            mdf[
                (mdf.timestamp_reset > start) & (mdf.timestamp_reset < end)
            ].timestamp_reset,
            mdf[(mdf.timestamp_reset > start) & (
                mdf.timestamp_reset < end)].power,
            label=legend_label,
            color=colors[1],
            linewidth=0.5,
        )

        # add label
        label = f"{prompt['output_tokens']} tokens"
        ax.text(
            start,
            mdf[(mdf.timestamp_reset > start) & (
                mdf.timestamp_reset < end)].power.max()
            * 1.1,
            label,
            rotation=45,
            fontsize=8,
        )

    # store for other events
    other_events.append((last_event, mdf.timestamp.max()))

    # plot the detailed annotations
    for idx, detailed_prompt_id in enumerate(detailed_prompt_ids):
        prompt = conv_data["questionRecords"][detailed_prompt_id]
        start = prompt["time"]["start"]
        end = start + prompt["time"]["duration"]
        start_ns = start * 1_000_000_000
        end_ns = end * 1_000_000_000

        # only keep generate events
        df_last = df[(df.value > start_ns) & (df.value < end_ns)]

        # add prefill events
        if app == "LLMFarmEval":

            # get the relevant timings
            timings = dft.iloc[detailed_prompt_id]
            input_tokens = timings.n_p_eval
            prefill_tps = 1e3 / timings.t_p_eval_ms * timings.n_p_eval

            prefill_start = (
                df_last.loc[f"generate.{detailed_prompt_id}.start"].value
                / 1_000_000_000
                - x_offset
            )
            prefill_end = prefill_start + (1 / prefill_tps * input_tokens)

        elif app == "MLCChat":

            prefill_start = (
                df.loc[f"prefill.{detailed_prompt_id}.start"].value /
                1_000_000_000
                - x_offset
            )
            prefill_end = (
                df.loc[f"prefill.{detailed_prompt_id}.end"].value /
                1_000_000_000
                - x_offset
            )

        else:
            sys.exit(f"Error: Unsupported app '{app}'.")
        color = colors[-3]
        ax.fill_between(
            mdf["timestamp_reset"],
            mdf["power"],
            where=(mdf.timestamp_reset >= prefill_start)
            & (mdf.timestamp_reset <= prefill_end),
            alpha=0.8,
            color=color,
            hatch="//",
        )
        legend_label = "prefill" if idx == 0 else None
        plt.plot(
            mdf[
                (mdf.timestamp_reset > prefill_start)
                & (mdf.timestamp_reset < prefill_end)
            ].timestamp_reset,
            mdf[
                (mdf.timestamp_reset > prefill_start)
                & (mdf.timestamp_reset < prefill_end)
            ].power,
            label=legend_label,
            color=color,
            linewidth=0.5,
        )

        # decode/generate events
        if app == "LLMFarmEval":

            start_generate = prefill_end

            df_last_llm_sample = df_last[df_last.index.str.contains(
                "llm_sample")]
            df_last_llm_sample = df_last_llm_sample[
                df_last_llm_sample.index.str.endswith("end")
            ]
            end_generate = df_last_llm_sample.iloc[-1].value / \
                1_000_000_000 - x_offset

        elif app == "MLCChat":

            df_last_llmfarm = df_last[df_last.index.str.contains("decode")]
            all_start = df_last_llmfarm[df_last_llmfarm.index.str.endswith(
                "start")]
            all_end = df_last_llmfarm[df_last_llmfarm.index.str.endswith(
                "end")]
            start_generate = all_start.iloc[0].value / 1_000_000_000 - x_offset
            end_generate = all_end.iloc[-1].value / 1_000_000_000 - x_offset

        color = colors[
            -2
        ]  # if idx % 2 == 0 else colors[-1]  # quick hack, will be improved
        ax.fill_between(
            mdf["timestamp_reset"],
            mdf["power"],
            where=(mdf.timestamp_reset >= start_generate)
            & (mdf.timestamp_reset <= end_generate),
            alpha=0.8,
            color=color,
            hatch="-",
        )
        legend_label = "generate" if idx == 0 else None
        plt.plot(
            mdf[
                (mdf.timestamp_reset > start_generate)
                & (mdf.timestamp_reset < end_generate)
            ].timestamp_reset,
            mdf[
                (mdf.timestamp_reset > start_generate)
                & (mdf.timestamp_reset < end_generate)
            ].power,
            label=legend_label,
            color=color,
            linewidth=0.5,
        )

    # add label
    label = f"{prompt['output_tokens']} tokens"
    ax.text(
        start - x_offset,
        mdf[
            (mdf.timestamp_reset > start_generate)
            & (mdf.timestamp_reset < end_generate)
        ].power.max()
        * 1.1,
        label,
        rotation=45,
        fontsize=8,
    )

    # plot other events
    for idx, (start_other_event, end_other_event) in enumerate(other_events):
        mdf_slice = mdf[
            (mdf.timestamp_reset > start_other_event)
            & (mdf.timestamp_reset < end_other_event)
        ]
        label = "background" if idx == 0 else None
        ax.fill_between(
            mdf_slice.timestamp_reset, mdf_slice.power, alpha=0.8, color="grey"
        )
        plt.plot(
            mdf_slice.timestamp_reset,
            mdf_slice.power,
            label=label,
            color="grey",
            linewidth=0.5,
        )

    # show legend
    ax.legend(loc="upper center", ncol=3)
    if no_legend:
        ax.legend().remove()

    # ax.set_title("Power consumption over time")
    ax.set_xlabel("Time (sec)")
    ax.set_ylabel("Power (W)")
    ax.set_ylim(0, 15.5)

    # save
    filename = os.path.join(path, "plot_annotated_performance.pdf")
    fig.savefig(filename, bbox_inches="tight")
    fig.clf()


def compute_detailed_performance_metrics(
    filepath, iteration, conversation, mdf, csv_sep=","
):

    df = pd.read_csv(filepath, index_col=0, names=["value"], sep=csv_sep)

    data = []

    df_start = df[df.index.str.endswith("start")]
    for index, row in df_start.iterrows():

        start = row.value
        stage = str(index).replace(".start", "")
        end_key = str(index).replace("start", "end")

        # Note: might crash if end_key does not exist (should never happen in practice)
        end = df[df.index == end_key].value.values[0]

        duration = end - start

        # monsoon
        start_time = start / 1_000_000_000  # to sec
        end_time = end / 1_000_000_000  # to sec
        monsoon_df_trimmed = mdf[
            (mdf.timestamp > start_time) & (mdf.timestamp < end_time)
        ]
        total_energy, total_discharge = powerlib.compute_power_performance(
            monsoon_df_trimmed
        )

        data.append(
            {
                "iteration": iteration,
                "conversation": conversation,
                "stage": stage,
                "duration (ns)": duration,
                "energy (mWh)": total_energy,
                "discharge (mAh)": total_discharge,
            }
        )

    # save
    odf = pd.DataFrame(data)
    return odf


def main(args):

    # get arguments
    path = args.path

    # load configuration file
    with open(os.path.join(path, "configuration.json"), encoding="utf-8") as f:
        configuration = json.load(f)

    # read data
    ts = load_ts_data(os.path.join(path, "measurements_ts.csv"))
    if ts is None:
        sys.exit("Error: Could not read 'measurements_ts.csv'.")

    try:
        monsoon = load_monsoon_data(
            os.path.join(path, "measurements_monsoon.csv"))
    except FileNotFoundError:
        print("Error: Could not read 'measurements_monsoon.csv'.")
        exit(1)

    # if requested, plot annotated figures
    if args.include_annotated_figures:

        # params
        iteration = 0
        conversation = 0
        overhead_sec = 1

        app = configuration["app"]

        if app == "LlamaCpp":
            # load relevant measurements file
            filepath = os.path.join(
                path,
                "melt_measurements",
                f"measurements_iter{iteration}_conv{conversation}.csv",
            )
            data = pd.read_csv(filepath, index_col=0, sep=",")

            # load relevant micro tsv file
            filepath = os.path.join(
                path,
                "melt_measurements",
                f"measurements_iter{iteration}_conv{conversation}.tsv",
            )
            df = pd.read_csv(filepath, index_col=0, names=["value"], sep=" ")

            # sort index by column ("value")
            df = df.sort_values(by="value")

        else:
            # load relevant measurements file
            filepath = os.path.join(
                path, "melt_measurements", f"measurements_iter{iteration}.json"
            )
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)

            # load relevant micro csv file
            filepath = os.path.join(
                path,
                "melt_measurements",
                f"measurements_iter{iteration}_conv{conversation}.csv",
            )
            df = pd.read_csv(filepath, index_col=0, names=["value"], sep=",")

            # sort index by column ("value")
            df = df.sort_values(by="value")

            # get timestamp - overhead_sec
            time_start = data[conversation]["modelLoadTime"]["start"] - overhead_sec
            last_prompt = len(data[conversation]["questionRecords"]) - 1
            time_end = (
                data[conversation]["questionRecords"][last_prompt]["time"]["start"]
                + data[conversation]["questionRecords"][last_prompt]["time"]["duration"]
                + overhead_sec
            )

        # read timing file
        timing_filepath = os.path.join(
            path,
            "melt_measurements",
            f"measurements_iter{iteration}_timing_conv{conversation}.csv",
        )
        if os.path.isfile(timing_filepath):
            dft = pd.read_csv(timing_filepath, sep=",")
        else:
            dft = None

        # trim monsoon data
        mdf_trimmed = monsoon[
            (monsoon.timestamp > time_start) & (
                monsoon.timestamp < (time_end + 5))
        ]

        # plot annotated figures
        plot_annotated_performance_metrics(
            data[conversation], df, dft, mdf_trimmed, app, path, args.no_legend
        )

    # Additional Performance Metrics
    model_perf_metrics_list = []
    inf_perf_metrics_list = []
    detailed_metrics_list = []

    # only for LLamaCpp
    if configuration["app"] == "LlamaCpp":

        # per csv file (regardless iteration/conversation)
        for filepath_csv in glob.glob(
            os.path.join(path, "melt_measurements",
                         "measurements_iter[0-9]*.csv")
        ):
            # infer iteration/conversation number from filepath
            iteration = __get_iter_from_filename(filepath_csv)
            conversation = __get_conv_from_filename(filepath_csv)

            # compute the model and inf metrics
            filepath_txt = filepath_csv.replace("measurements_", "llm_output_").replace(
                ".csv", ".txt"
            )
            model_perf_metrics, inf_perf_metrics = compute_llamacpp_performance_metrics(
                filepath_csv, filepath_txt, iteration, conversation, monsoon
            )
            model_perf_metrics_list.append(model_perf_metrics)
            inf_perf_metrics_list.append(inf_perf_metrics)

            # detailed metrics (tsv file in case of LlamaCpp)
            try:
                filepath_tsv = filepath_csv.replace(
                    ".csv", ".tsv"
                )  # find the equivalent tsv file
                detailed_metrics_list.append(
                    compute_detailed_performance_metrics(
                        filepath_tsv, iteration, conversation, monsoon, csv_sep=" "
                    )
                )
            except FileNotFoundError:
                print(
                    f"Warning: Could not find detailed measurements for iteration {iteration} and conversation {conversation}."
                )

    # for LLMFarmEval (iOS) and MLCChat (both iOS and Android)
    else:

        # per json file (per iteration basically)
        for filepath_json in glob.glob(
            os.path.join(path, "melt_measurements",
                         "measurements_iter[0-9].json")
        ):

            # infer iteration number from filepath_json
            iteration = __get_iter_from_filename(filepath_json)

            # compute the model and inf metrics
            model_perf_metrics_list.append(
                compute_model_performance_metrics(
                    filepath_json, iteration, monsoon)
            )
            inf_perf_metrics_list.append(
                compute_inference_performance_metrics(
                    configuration["app"], filepath_json, iteration, monsoon
                )
            )

            # per detailed metric for particular iteration
            for filepath in glob.glob(
                os.path.join(
                    path,
                    "melt_measurements",
                    f"measurements_iter{iteration}_conv[0-9]*.csv",
                )
            ):
                conversation = __get_conv_from_filename(filepath)
                detailed_metrics_list.append(
                    compute_detailed_performance_metrics(
                        filepath, iteration, conversation, monsoon
                    )
                )

    # merge metrics
    try:
        df_model_perf = pd.concat(model_perf_metrics_list, ignore_index=True)
    except ValueError:
        with open(os.path.join(path, "output.txt")) as f:
            lines = f.readlines()
        for line in lines:
            if "Warning: Timeout reached while waiting for await event." in line:
                print("Timeout reached!!")
        exit(1)

    df_inf_perf = pd.concat(inf_perf_metrics_list, ignore_index=True)
    if len(detailed_metrics_list) > 0:
        df_detailed_perf = pd.concat(detailed_metrics_list, ignore_index=True)
    else:
        df_detailed_perf = pd.DataFrame()

    # save
    df_model_perf.to_csv(
        os.path.join(path, "results_model_load_performance.csv"), index=False
    )
    df_inf_perf.to_csv(
        os.path.join(path, "results_model_inference_measurements.csv"), index=False
    )
    df_detailed_perf.to_csv(
        os.path.join(path, "results_detailed_measurements.csv"), index=False
    )


# argument parser
def __parse_arguments(args):

    parser = argparse.ArgumentParser(
        description="Report measurements from an executed on-device LLM experiment."
    )

    parser.add_argument(
        "-p", "--path", default="measurements", help="Data path of executed experiment."
    )

    parser.add_argument(
        "-iaf",
        "--include-annotated-figures",
        action="store_true",
        help="Optionally, include annotated figures in the results.",
    )

    parser.add_argument(
        "--no-legend",
        action="store_true",
        help="Do not show the legend in the annotated plot.",
    )

    parsed = parser.parse_args(args)
    return parsed


if __name__ == "__main__":

    # parse args
    arguments = __parse_arguments(sys.argv[1:])
    main(arguments)
