#!/bin/bash
#SBATCH --job-name=gage_run
#SBATCH --output=logs/gage_%j.out       # Logs go here
#SBATCH --error=logs/gage_%j.err        # Error logs
#SBATCH --time=01:00:00 
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --partition=standard
#SBATCH --ntasks=1

# === Load modules or activate your environment ===
source ~/.venv_sandbox_py3.11/bin/activate


echo "Running gage simulation..."
echo "SANDBOX_FILE = $SANDBOX_FILE"
echo "CALIB_FILE   = $CALIB_FILE"

# === Run your Python simulation ===
python sandbox.py -run -i "$SANDBOX_FILE" -j "$CALIB_FILE"
