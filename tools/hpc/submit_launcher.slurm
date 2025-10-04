#!/bin/bash
#SBATCH --job-name=sandbox_launcher
#SBATCH --output=logs/launcher_%j.out
#SBATCH --error=logs/launcher_%j.err
#SBATCH --time=01:00:00                  # Adjust based on coordination time needed
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --partition=standard
#SBATCH --ntasks=1

# === Load modules or activate your environment ===

# Print current node and time info
echo "Running on $(hostname) at $(date)"
echo "SLURM_JOB_ID: $SLURM_JOB_ID"

module load python/3.11  # if needed on your HPC
echo "[run_launcher.slurm] Resubmitting sandbox_launcher.py"
python sandbox_launcher.py

