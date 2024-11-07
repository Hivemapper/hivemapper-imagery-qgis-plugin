#!/bin/bash

# Define the target directory for package installation
TARGET_DIR="./extlib"

# Use x86 architecture to install hivemapper-python to the target directory
echo "Installing hivemapper-python to $TARGET_DIR without numpy and scipy..."
arch -x86_64 python3 -m pip install hivemapper-python --target "$TARGET_DIR" --no-cache-dir

# Check if installation succeeded
if [ $? -eq 0 ]; then
    echo "Installation successful. Removing numpy and scipy if they exist."
    # Remove numpy and scipy from the target directory
    rm -rf "$TARGET_DIR"/numpy*
    rm -rf "$TARGET_DIR"/scipy*
else
    echo "Error: hivemapper-python installation failed."
    exit 1
fi

# Modify the __init__.py in bursts directory to add 'from .query import create_bursts'
BURST_INIT="$TARGET_DIR/bursts/__init__.py"
if [ -f "$BURST_INIT" ]; then
    echo "Adding 'from .query import create_bursts' to $BURST_INIT..."
    echo "from .query import create_bursts" >> "$BURST_INIT"
    echo "Modification successful."
else
    echo "Error: $BURST_INIT not found."
fi

echo "Script completed."
