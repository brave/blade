#!/bin/bash

# Note:   Mobile run script for running experiments on iOS or Android.
# Author: Stefanos Laskaridis (stefanos@brave.com)


CONTEXT_SIZE=${CONTEXT_SIZE:-2048}
MAX_GEN_LEN=${MAX_GEN_LEN:-256}
BS=${BS:-1024}
PLATFORM=${PLATFORM:-"ios"}
APP=${APP:-"MLCChat"}
DEVICE=${DEVICE:-"iPhone 14 Pro"}
REPETITIONS=${REPETITIONS:-3}
CONVERSATION_TO=${CONVERSATION_TO:-5}
CPU=${CPU:-0}
N_THREADS=${N_THREADS:-1}

if [ $PLATFORM = "ios" ]; then
    if [ $CPU = 1]; then
        echo -n"(CPU) "
    fi
    echo "Running on iOS"
elif [ $PLATFORM = "android" ]; then
    echo "Running on Android"
else
    echo "Invalid platform: $PLATFORM"
    exit 1
fi
EXECUTABLE="run_${PLATFORM}.sh"

cs=${CONTEXT_SIZE}
mgl=${MAX_GEN_LEN}
bs=${BS}
if [ $APP = "LlamaCpp" ] || [ $APP = "LLMFarmEval" ] ; then
        echo Running "DEVICE=$DEVICE APP=$APP CPU=$CPU N_THREADS=${N_THREADS} MAX_CONTEXT_LEN=$cs MAX_GEN_LEN=$mgl INPUT_TOKEN_BATCHING=$b REPETITIONS=$REPETITIONS CONVERSATION_TO=$CONVERSATION_TO EXPERIMENT_ID="run_cs${cs}_mgl${mgl}_bs${bs}" ./${EXECUTABLE}"
        DEVICE=$DEVICE APP=$APP CPU=$CPU N_THREADS=${N_THREADS} MAX_CONTEXT_LEN=$cs MAX_GEN_LEN=$mgl INPUT_TOKEN_BATCHING=$bs REPETITIONS=$REPETITIONS CONVERSATION_TO=$CONVERSATION_TO EXPERIMENT_ID="run_cs${cs}_mgl${mgl}_bs${bs}" ./${EXECUTABLE}
elif [ $APP = "MLCChat" ] || [ $APP = "MLCChat++" ]; then
        echo Running "DEVICE=$DEVICE APP=$APP MAX_CONTEXT_LEN=$cs MAX_GEN_LEN=$mgl REPETITIONS=$REPETITIONS CONVERSATION_TO=$CONVERSATION_TO EXPERIMENT_ID="run_cs${cs}_mgl${mgl}" ./${EXECUTABLE}"
        DEVICE=$DEVICE APP=$APP MAX_CONTEXT_LEN=$cs MAX_GEN_LEN=$mgl REPETITIONS=$REPETITIONS CONVERSATION_TO=$CONVERSATION_TO EXPERIMENT_ID="run_cs${cs}_mgl${mgl}" ./${EXECUTABLE}
fi