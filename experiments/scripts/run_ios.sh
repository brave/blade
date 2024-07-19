#!/bin/bash

# Note:   Mobile run script for running experiments on iOS.
# Author: Stefanos Laskaridis (stefanos@brave.com)


DEVICE=${DEVICE:-"iPhone 14 Pro"}

MLC_MODELS=()
while IFS= read -r line; do
    MLC_MODELS+=("$line")
done < mlc_models.txt

MLCPP_MODELS=()
while IFS= read -r line; do
    MLCPP_MODELS+=("$line")
done < mlcpp_models.txt

LLAMACPP_MODELS=()
while IFS= read -r line; do
    LLAMACPP_MODELS+=("$line")
done < llamacpp_models.txt

DEVICES=(
    "iPhone 14 Pro"
    "iPhone SE"
)
APPS=(
    "MLCChat"
    "MLCChat++"
    "LLMFarmEval"
)

REPETITIONS=${REPETITIONS:-3}
CONVERSATION_FROM=${CONVERSATION_FROM:-0}
CONVERSATION_TO=${CONVERSATION_TO:-3}
MAX_GEN_LEN=${MAX_GEN_LEN:-32}
MAX_CONTEXT_LEN=${MAX_CONTEXT_LEN:-512}
PREFILL_CHUNK_SIZE=${PREFILL_CHUNK_SIZE:-512}
PREFILL_CHUNK_SIZE_ARG_STR=""
TEMPERATURE=${TEMPERATURE:-0.9}
TOP_K=${TOP_K:-40}
TOP_P=${TOP_P:-0.95}
REPEAT_PENALTY=${REPEAT_PENALTY:-1.1}
INPUT_TOKEN_BATCHING=${INPUT_TOKEN_BATCHING:-128}

CPU=${CPU:-0}
CPU_ARG=""
if [ $CPU = 1 ]; then
    CPU_ARG="--cpu"
fi

DEVICE_FRIENDLY_NAME=${DEVICE//" "/"_"} # Replace spaces with underscores
EXPERIMENT_ID=${EXPERIMENT_ID:-"$(date +%Y%m%d_%H%M%S)"}
OUTPUT_PATH_ROOT=${OUTPUT_PATH_ROOT:-"../experiment_outputs/${DEVICE_FRIENDLY_NAME}/"}

if [ ! -z APP ]; then
    APPS=("${APP}")
fi

for APP in ${APPS[@]}; do
    if [ $APP = "MLCChat" ];then
        MODELS=("${MLC_MODELS[@]}")
    elif [ $APP = "MLCChat++" ];then
        MODELS=("${MLCPP_MODELS[@]}")
        PREFILL_CHUNK_SIZE_ARG_STR="--prefill-chunk-size ${PREFILL_CHUNK_SIZE}"
    elif [ $APP = "LLMFarmEval" ];then
        MODELS=("${LLAMACPP_MODELS[@]}")
    fi
    for MODEL in ${MODELS[@]}; do
        OUTPUT_PATH="${OUTPUT_PATH_ROOT}/${APP}/${MODEL}/${EXPERIMENT_ID}/"
        echo "Running ${MODEL} on ${APP} on device ${DEVICE}..."
        python ../llm-eval-ios.py \
            -a "${APP}" \
            -o "${OUTPUT_PATH}/" \
            -d "${DEVICE}" \
            -m "${MODEL}" \
            -r ${REPETITIONS} \
            -cf ${CONVERSATION_FROM} -ct ${CONVERSATION_TO} \
            --max-gen-len ${MAX_GEN_LEN} \
            --max-context-size ${MAX_CONTEXT_LEN} \
            --temperature ${TEMPERATURE} \
            --top-k ${TOP_K} \
            --top-p ${TOP_P} \
            ${CPU_ARG} \
            --repeat-penalty ${REPEAT_PENALTY} \
            --input-token-batching ${INPUT_TOKEN_BATCHING} ${PREFILL_CHUNK_SIZE_ARG_STR}
        sleep 5
    done
done