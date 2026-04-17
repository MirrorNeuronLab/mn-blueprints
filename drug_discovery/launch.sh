#!/bin/bash

echo "================================================================="
echo " 🧬 Launching BioTarget Infinite Drug Discovery Loop (Multi-Agent)"
echo "================================================================="

# Run the MirrorNeuron job in detached mode and capture the output
echo "Submitting job..."
OUTPUT=$(/Users/homer/Projects/MirrorNeuron/mn run $(dirname "$0") --no-await)

# Extract job_id
JOB_ID=$(echo "$OUTPUT" | grep -o 'job_id: "[^"]*"' | cut -d'"' -f2)

if [ -z "$JOB_ID" ]; then
    echo "Failed to launch job:"
    echo "$OUTPUT"
    exit 1
fi

# Define the output files
OUT_DIR="/tmp/mirror_neuron_${JOB_ID}"
mkdir -p "$OUT_DIR"

BEST_DRUGS_FILE="${OUT_DIR}/best_drugs.txt"
DOCKING_LOG_FILE="${OUT_DIR}/docking.log"

# Ensure the files exist so they can be easily tailed
touch "$BEST_DRUGS_FILE"
touch "$DOCKING_LOG_FILE"

echo ""
echo " 📂 WINNING DRUGS OUTPUT : $BEST_DRUGS_FILE"
echo " 📝 DOCKING ATTEMPTS LOG : $DOCKING_LOG_FILE"
echo "================================================================="
echo ""
echo "$OUTPUT"
echo ""
echo "================================================================="
echo " ✅ Loop is running in the background!"
echo "    To monitor the discoveries in real-time, use this command:"
echo ""
echo "    tail -f $DOCKING_LOG_FILE $BEST_DRUGS_FILE"
echo "================================================================="
