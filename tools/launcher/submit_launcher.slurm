#!/bin/bash

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:05:00
#SBATCH --job-name=sandbox_launcher
#SBATCH --account=ohd
#SBATCH --error=log/launcher_%j.err
#SBATCH --output=log/launcher_%j.out
##SBATCH --partition=ursa
#SBATCH --mem=2G
#SBATCH --requeue
##SBATCH --exclusive



# -------------------------------
# User-defined wallclock
# -------------------------------
# Set SLURM_TIMELIMIT in seconds to match #SBATCH --time
# User MUST edit this variable to match the requested time
SLURM_TIMELIMIT=$((5*60))  # 5 minutes in seconds

# Check that the variable is set
if [ -z "$SLURM_TIMELIMIT" ]; then
    echo "ERROR: SLURM_TIMELIMIT is not set. Please set it in the script."
    exit 1
fi

export LAUNCHER_WALLCLOCK=$SLURM_TIMELIMIT
# convert to minutes
export LAUNCHER_WALLCLOCK_MIN=$(( LAUNCHER_WALLCLOCK / 60 ))
echo "Launcher wallclock (minutes): $LAUNCHER_WALLCLOCK_MIN"

# ----------------------------------------------------
#SANDBOX_PACKAGE_PATH=$(python -c "import sandbox, os; print(os.path.dirname(sandbox.__file__))")
#source "${SANDBOX_PACKAGE_PATH}/.venv/venv_sandbox_py3.11/bin/activate"
#echo "sss: ${SANDBOX_PACKAGE_PATH}"
unset PYTHONPATH
source /scratch4/NCEPDEV/ohd/Ahmad.Jan.Khattak/Code/NextGenSandboxHub/.venv/venv_sandbox_py3.11/bin/activate

# Print current node and time info
echo "Running on $(hostname) at $(date)"
echo "SLURM_JOB_ID: $SLURM_JOB_ID"

# Debug info
echo "LL Python executable: $(which python)"
python -c "import numpy; print('LL NumPy version:', numpy.__version__)"
python -c "import sqlite3; print('LL sqlite3 version:', sqlite3.sqlite_version)"


# ----------------------------------------------------
echo "[submit_launcher.slurm] (Re)Submitting sandbox_launcher.py"
python launcher/sandbox_launcher.py
exit_code=$?

echo "[submit_launcher] Python exit code = $exit_code"

# ----------------------------------------------------
# 99 means: "requeue me, work still incomplete"
# ----------------------------------------------------
if [ $exit_code -eq 99 ]; then
    echo "[submit_launcher] Requeue requested, requeueing job"
    scontrol requeue $SLURM_JOB_ID
    exit 0
fi

# Normal termination
echo "[submit_launcher] Completed with exit code $exit_code"
exit $exit_code
