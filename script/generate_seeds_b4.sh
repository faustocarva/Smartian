#!/bin/bash

# Set the current date
DATE=$(date +"%Y-%m-%d_%H-%M")

# Default values
DEFAULT_MODEL="Llama3-70B"
DEFAULT_NUM_SEEDS=10
DEFAULT_NUM_TXS=4
DEFAULT_BACKEND="together"
TEMPERATURES=(0.6)

# Input parameters with defaults
MODEL=${1:-$DEFAULT_MODEL}
BACKEND=${2:-$DEFAULT_BACKEND}
NUM_SEEDS=${3:-$DEFAULT_NUM_SEEDS}
NUM_TXS=${4:-$DEFAULT_NUM_TXS}

# Define the dataset base directory
BASE_DIR="./B4_orig"

# Function to confirm continuation
confirm_continue() {
    read -p "Press Enter to continue or Ctrl+C to abort..." _
}

# Display selected configuration
echo "Configuration:"
echo "Model: $MODEL"
echo "Backend: $BACKEND"
echo "Number of Seeds: $NUM_SEEDS"
echo "Number of Transactions: $NUM_TXS"
echo "Temperatures: ${TEMPERATURES[*]}"
echo "Base Directory: $BASE_DIR"
echo

# Get the total number of temperatures
NUM_TEMPS=${#TEMPERATURES[@]}

# Loop through the temperature settings
for TEMP in "${TEMPERATURES[@]}"; do
    # Define the target directory
    TARGET_DIR="./B4_${MODEL}_${TEMP}_${NUM_SEEDS}_${NUM_TXS}_${DATE}_${BACKEND}"

    # Copy the base directory
    cp -R "$BASE_DIR" "$TARGET_DIR"
    echo "Copied $BASE_DIR to $TARGET_DIR"

    # Process each subdirectory
    for dir in "$TARGET_DIR"/*; do
        echo "Processing $dir"
        poetry run genai4fuzz run_llm "$dir" "$BACKEND" "$MODEL" "$TEMP" "$NUM_SEEDS" "$NUM_TXS"
    done

    # Ask for confirmation only if not the last temperature
    if (( i < NUM_TEMPS - 1 )); then
        confirm_continue
        echo "Proceeding with the next temperature..."
    fi
done

echo "All tasks completed."
