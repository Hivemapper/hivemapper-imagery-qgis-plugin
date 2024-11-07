# Define the target directory for package installation
$TARGET_DIR = ".\extlib"

# Use x86 architecture to install hivemapper-python to the target directory
Write-Host "Installing hivemapper-python to $TARGET_DIR without numpy and scipy..."

# Install hivemapper-python to the target directory
# assume python version is correct >=3.9
pip install hivemapper-python --target "$TARGET_DIR" --no-cache-dir

# Check if installation succeeded
if ($LASTEXITCODE -eq 0) {
    Write-Host "Installation successful. Removing numpy and scipy if they exist."
    # Remove numpy and scipy from the target directory
    Remove-Item -Recurse -Force "$TARGET_DIR\numpy*" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "$TARGET_DIR\scipy*" -ErrorAction SilentlyContinue
} else {
    Write-Host "Error: hivemapper-python installation failed."
    exit 1
}

# Modify the __init__.py in bursts directory to add 'from .query import create_bursts'
$BURST_INIT = "$TARGET_DIR\bursts\__init__.py"
if (Test-Path $BURST_INIT) {
    Write-Host "Adding 'from .query import create_bursts' to $BURST_INIT..."
    Add-Content -Path $BURST_INIT -Value "`nfrom .query import create_bursts"
    Write-Host "Modification successful."
} else {
    Write-Host "Error: $BURST_INIT not found."
}

Write-Host "Script completed."
