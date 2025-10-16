#!/bin/bash

###SBATCH --nodes=1
###SBATCH --ntasks-per-node=1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=08:00:00
#SBATCH --job-name=sandbox_launcher
#SBATCH --account=ohd
#SBATCH --error=log/launcher_%j.err
#SBATCH --output=log/launcher_%j.out
##SBATCH --partition=ursa
#SBATCH --mem=2G
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

#module load python/3.11  # if needed on your HPC
echo "[run_launcher.slurm] Resubmitting sandbox_launcher.py"
python hpc/sandbox_launcher.py
