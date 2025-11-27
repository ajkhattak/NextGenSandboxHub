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


#module load cmake/3.30.2
#module load openmpi/4.1.6
#module load gcc/12.4.0
#module load netcdf-fortran/4.6.1
#module load sqlite/3.46.0
#module load udunits/2.2.28

source /home/Ahmad.Jan.Khattak/.venv_sandbox_py3.11/bin/activate

# Print current node and time info
echo "Running on $(hostname) at $(date)"
echo "SLURM_JOB_ID: $SLURM_JOB_ID"

export LAUNCHER_WALLCLOCK=${SLURM_TIMELIMIT:-5}  # fallback 5 minutes if not set
echo "[submit_launcher.slurm] Max wallclock (minutes) = $LAUNCHER_WALLCLOCK"

#module load python/3.11  # if needed on your HPC
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
