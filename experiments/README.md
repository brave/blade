# MELT PhoneLab

This directory contains the codebase for automating the interaction with phone apps.

## Structure

```bash
├── README.md
├── llm-eval-android.py            # python script for android automation
├── llm-eval-ios.py                # python script for ios automation
├── notebooks                      # contains notebooks for analysing the results.
├── scripts
│   ├── get_android_screenshot.sh  # gets an android screenshot to monitor what is going on the screen.
│   ├── llamacpp_models.txt        # models to run for llama.cpp app
│   ├── mlc_models.txt             # models to run for mlcchat app
│   ├── mlcpp_models.txt           # models to run for mlcchat++ app
│   ├── mobile_run.sh              # runs an automated job on device
│   ├── push_all_models.sh         # push all related models to device
│   ├── run_android.sh             # lower-level script for running a measurement on android devices.
│   └── run_ios.sh                 # lower-level script for running a measurement on android devices.
└── utils                          # contains various utility functions
```

## How to run

In this section, we are taking `scripts/mobile_run.sh` as an example. The rest of the scripts are similar in nature, just iterate over different conversations or hyperparameters.

#### Setup

```bash
pip install -r requirements.txt
```

1. Turn on the device you want to benchmark on: `src/tools/control-device.py -d '<device_name>' --switch on`
2. Pick the app you want to run (e.g. mlc, llama.cpp or LLMFarm)
3. Check that you have compiled and installed the application backend, based on your selection. Applications and instructions on how to build them can be found in `frameworks/**/**/build_scripts`.
4. Check what models you want to run in `{llamacpp,mlc,mlcpp}_models.txt`, based on the app you want to run. Models should be compiled and are expected to reside in `../melt_models_converted`.

**iOS runs:**

In case you are running MLC on iOS, you need to check that the order in `src/tools/experiments/llm-evaluation-ios.py` is reflected on the defined lists in `__get_model_idx()`. <!--TODO: extract into file-->

```bash
DEVICE="iPhone 14 Pro" PLATFORM="ios" CONTEXT_SIZE=1024 MAX_GEN_LEN=256 APP="MLCChat++" REPETITIONS=3 CONVERSATION_TO=5 ./mobile_run.sh
DEVICE="iPhone 14 Pro" PLATFORM="ios" CONTEXT_SIZE=2048 MAX_GEN_LEN=512 APP="LLMFarmEval" REPETITIONS=3 CONVERSATION_TO=5 ./mobile_run.sh
```

**Android runs:**

```bash
DEVICE="Galaxy S23" PLATFORM="android" CONTEXT_SIZE=2048 MAX_GEN_LEN=512 APP="MLCChat++" REPETITIONS=3 CONVERSATION_TO=5 ./mobile_run.sh
DEVICE="Galaxy S23" PLATFORM="android" CONTEXT_SIZE=2048 MAX_GEN_LEN=512 APP="LlamaCpp" REPETITIONS=3 CONVERSATION_TO=5 ./mobile_run.sh
```

Please note that certain hyperparameters can affect the latency of runtime, hit timeouts or lead to OOM errors. This is why one needs to check which hyperparameters work for each model.


5. These generate experiment logs under `experiments/experiment_outputs/` dir.
6. You can analyse these by running the `experiments/notebooks/parse_mobile_runs.ipynb`


## Expected output

For 2 repetitions and 2 conversations, the output should look as follows:


For MLC:
```bash
├── configuration.json                 # The configuration with which the experiment was run
├── measurements_adb.csv               # Available only on android, s/w based measurements
├── measurements_monsoon.csv           # Energy measurements with monsoon
├── measurements_ts.csv                # Setup and iterations timing events
├── melt_measurements
│   ├── measurements_iter0_conv0.csv   # Inference event timings, iteration 0, conversation 0
│   ├── measurements_iter0_conv1.csv   # Inference event timings, iteration 0, conversation 1
│   ├── measurements_iter0.json        # Runtime outputs, iter 0
│   ├── measurements_iter1_conv0.csv   # Inference event timings, iteration 1, conversation 0
│   ├── measurements_iter1_conv1.csv   # Inference event timings, iteration 1, conversation 1
│   └── measurements_iter1.json        # Runtime outputs, iter 1
└── output.txt                         # The output logs of phonelab

```

For llama.cpp:
```bash
├── configuration.json                 # The configuration with which the experiment was run
├── measurements_adb.csv               # Available only on android, s/w based measurements
├── measurements_monsoon.csv           # Energy measurements with monsoon
├── measurements_ts.csv                # Setup and iterations timing events
├── melt_measurements
│   ├── llm_output_iter0_conv0.txt     # llama.cpp script outputs, iteration 0, conversation 0
│   ├── llm_output_iter0_conv1.txt     # llama.cpp script outputs, iteration 0, conversation 1
│   ├── llm_output_iter1_conv0.txt     # llama.cpp script outputs, iteration 0, conversation 0
│   ├── llm_output_iter1_conv1.txt     # llama.cpp script outputs, iteration 1, conversation 1
│   ├── measurements_iter0_conv0.csv   # Prompt start/duration times, iteration 0, conversation 0
│   ├── measurements_iter0_conv0.tsv   # Inference event timings, iteration 0, conversation 0
│   ├── measurements_iter0_conv1.csv   # Prompt start/duration times, iteration 0, conversation 1
│   ├── measurements_iter0_conv1.tsv   # Inference event timings, iteration 0, conversation 1
│   ├── measurements_iter1_conv0.csv   # Prompt start/duration times, iteration 1, conversation 0
│   ├── measurements_iter1_conv0.tsv   # Inference event timings, iteration 1, conversation 0
│   ├── measurements_iter1_conv1.csv   # Prompt start/duration times, iteration 1, conversation 1
│   └── measurements_iter1_conv1.tsv   # Inference event timings, iteration 1, conversation 1
└── output.txt                         # The output logs of phonelab
```