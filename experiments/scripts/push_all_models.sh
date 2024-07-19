#!/bin/bash

# Note:   Script to push models to Android or iOS.
# Author: Stefanos Laskaridis (stefanos@brave.com)


PLATFORM=${PLATFORM:-"android"}
FRAMEWORK=${FRAMEWORK:-"mlc"}
LLAMACPP_PATH=${LLAMACPP_PATH:-"../../../frameworks/llama.cpp/llama.cpp/"}
MLC_PATH=${MLC_PATH:-"../../../frameworks/MLC/mlc-llm/"}

MLC_MODELS=()
while IFS= read -r line; do
    MLC_MODELS+=("$line")
done < mlc_models.txt

LLAMACPP_MODELS=()
while IFS= read -r line; do
    MODEL_DIR=$(dirname "$line")
    LLAMACPP_MODELS+=("$MODEL_DIR")
done < llamacpp_models.txt

echo 'Assuming models reside in MELT path on host machine (default=$MELT_ROOT/melt_models_converted/)'
if [ $FRAMEWORK = "mlc" ];then
    MODELS=("${MLC_MODELS[@]}")
elif [ $FRAMEWORK = "llamacpp" ];then
    MODELS=("${LLAMACPP_MODELS[@]}")
fi
echo "Pushing ${FRAMEWORK} models to ${PLATFORM}. Models: ${MODELS[@]}"
if [ $PLATFORM = "android" ]; then
    if [ $FRAMEWORK = "mlc" ];then
        pushd ${MLC_PATH}/build_scripts
        ./push_android_models.sh "${MLC_MODELS[@]}"
        popd
    elif [ $FRAMEWORK = "llamacpp" ];then
        pushd ${LLAMACPP_PATH}/build_scripts
        ./push_android_models.sh "${LLAMACPP_MODELS[@]}"
        popd
    fi
elif [ $PLATFORM = "ios" ]; then
    if [ $FRAMEWORK = "mlc" ];then
        pushd ${MLC_PATH}/build_scripts
        ./push_ios_models.sh "${MLC_MODELS[@]}"
        popd
    elif [ $FRAMEWORK = "llamacpp" ];then
        pushd ${LLAMACPP_PATH}/build_scripts
        ./push_ios_models.sh "${LLAMACPP_MODELS[@]}"
        popd
    fi
fi