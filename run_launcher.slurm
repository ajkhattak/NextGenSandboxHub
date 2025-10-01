#!/bin/bash

#SBATCH --job-name=launcher
#SBATCH --output=logs/%x_%j_%A_%a_%N.out
#SBATCH --error=logs/%x_%j.err
#SBATCH --time=08:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G

# Print current node and time info
echo "Running on $(hostname) at $(date)"
echo "SLURM_JOB_ID: $SLURM_JOB_ID"

module load python/3.11  # if needed on your HPC
echo "[run_launcher.slurm] Resubmitting sandbox_launcher.py"
python sandbox_launcher.py