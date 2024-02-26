#!/bin/bash
set -x

#MODEL="mistralai/Mistral-7B-Instruct-v0.2"
MODEL="teknium/OpenHermes-2-Mistral-7B"

# Parse named arguments
while [ "$1" != "" ]; do
    case $1 in
        --model ) shift
                 MODEL=$1
                 ;;
        * )      echo "Invalid argument: $1"
                 exit 1
    esac
    shift
done

# Check if path is provided
if [ -z "$path" ]; then
    echo "No path provided. Use --path to specify the path."
    echo "Using the default value ${MODEL}"
fi

LEGACY=0
BASE=$(basename "$MODEL")
FORMAT="mlpackage"
FLAGS=""
QUANTIZE="float16"

if [[ $LEGACY -eq 1 ]]; then
echo "Legacy mode"
FORMAT="mlmodel"
FLAGS="--legacy"
QUANTIZE="int8"
BASE+="-"
BASE+=${QUANTIZE}
fi

python -m exporters.coreml --model=${MODEL} --feature=text-generation ${FLAGS} --quantize ${QUANTIZE} ${BASE}/
mv ${BASE}/Model.${FORMAT} ./${BASE}.${FORMAT}
rm -rf ${BASE}
