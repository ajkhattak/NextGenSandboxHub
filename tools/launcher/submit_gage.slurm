#!/bin/bash

#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --time=08:00:00
#SBATCH --job-name=gage
#SBATCH --account=ohd
#SBATCH --error=log/gage_%j.err
#SBATCH --output=log/gage_%j.out
##SBATCH --partition=ursa
#SBATCH --mem=16G
##SBATCH --exclusive

##SBATCH --cpus-per-task=1

echo "Allocated CPUs: $SLURM_CPUS_PER_TASK"
# === Load modules or activate your environment ===

module load cmake/3.30.2
module load openmpi/4.1.6
module load gcc/12.4.0
module load netcdf-fortran/4.6.1
module load sqlite/3.46.0
module load udunits/2.2.28

source /home/Ahmad.Jan.Khattak/.venv_sandbox_py3.11/bin/activate

echo "Running gage simulation..."
echo "SANDBOX_FILE = $SANDBOX_FILE"
echo "CALIB_FILE   = $CALIB_FILE"

# === Run your Python simulation ===
#python /home/Ahmad.Jan.Khattak/Code/NextGenSandboxHub/sandbox.py -run -i "$SANDBOX_FILE" -j "$CALIB_FILE"
sandbox -run -i "$SANDBOX_FILE" -j "$CALIB_FILE"
