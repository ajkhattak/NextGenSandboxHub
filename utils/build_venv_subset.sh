#!/usr/bin/env bash
set -euo pipefail

# Load modules
#module load rdhpcs-conda/25.3.1

# Disable conda plugins (faster and avoids conflicts on HPC)
export CONDA_NO_PLUGINS=true

# initialize conda/mamba for non-interactive shell
eval "$(conda shell.bash hook)"

echo "Using SANDBOX_DIR=${SANDBOX_DIR}"


# Configure conda directories
mkdir -p "${SANDBOX_DIR}/rvenv/conda_envs"
mkdir -p "${SANDBOX_DIR}/rvenv/conda_pkgs"

conda config --add envs_dirs "${SANDBOX_DIR}/rvenv/conda_envs"
conda config --add pkgs_dirs "${SANDBOX_DIR}/rvenv/conda_pkgs"


# Install mamba environment manager

if [ ! -d "${SANDBOX_DIR}/rvenv/mamba" ]; then
conda create -y -p "${SANDBOX_DIR}/rvenv/mamba" -c conda-forge mamba
fi

# Enable mamba in this shell

eval "$("${SANDBOX_DIR}/rvenv/mamba/bin/mamba" shell hook --shell bash)"

mamba activate "${SANDBOX_DIR}/rvenv/mamba"

# Create main R environment

if [ ! -d "${SANDBOX_DIR}/rvenv/vevn_subset" ]; then
mamba env create -y -p "${SANDBOX_DIR}/rvenv/vevn_subset" -f "${SANDBOX_DIR}/rgeo_env.yml"
fi

# Activate main environment
mamba activate "${SANDBOX_DIR}/rvenv/vevn_subset"


# Install additional R packages via conda

mamba install -y \
-p "${SANDBOX_DIR}/rvenv/vevn_subset" \
-c conda-forge \
r-rcpp r-gifski r-sourcetools r-rnaturalearth \
r-later r-promises r-httpuv r-shiny r-leaflet \
r-units r-maptiles r-fst r-leaflet.extras r-ncdf4

# Run R dependency installer
Rscript "${SANDBOX_DIR}/src/R/install_load_libs.R"

echo "Environment setup complete."
