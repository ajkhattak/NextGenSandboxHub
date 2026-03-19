#!/usr/bin/env bash
set -euo pipefail

# Load modules
#module load conda/25.3.1

# Disable conda plugins (faster and avoids conflicts on HPC)
export CONDA_NO_PLUGINS=true

export CONDA_SOLVER=classic

# initialize conda/mamba for non-interactive shell
eval "$(conda shell.bash hook)"

echo "Using SANDBOX_BUILD_DIR=${SANDBOX_BUILD_DIR}"


# Configure conda directories
mkdir -p "${SANDBOX_BUILD_DIR}/rvenv/conda_envs"
mkdir -p "${SANDBOX_BUILD_DIR}/rvenv/conda_pkgs"

conda config --add envs_dirs "${SANDBOX_BUILD_DIR}/rvenv/conda_envs"
conda config --add pkgs_dirs "${SANDBOX_BUILD_DIR}/rvenv/conda_pkgs"


# Install mamba environment manager

if [ ! -d "${SANDBOX_BUILD_DIR}/rvenv/mamba" ]; then
conda create -y -p "${SANDBOX_BUILD_DIR}/rvenv/mamba" -c conda-forge mamba
fi

# Enable mamba in this shell

eval "$("${SANDBOX_BUILD_DIR}/rvenv/mamba/bin/mamba" shell hook --shell bash)"

set +u
mamba activate "${SANDBOX_BUILD_DIR}/rvenv/mamba"
set -u

# Create main R environment

if [ ! -d "${SANDBOX_BUILD_DIR}/rvenv/venv_subset" ]; then
mamba env create -y -p "${SANDBOX_BUILD_DIR}/rvenv/venv_subset" -f "${SANDBOX_DIR}/utils/venv/venv_subset.yaml"
fi

# Activate main environment
set +u
mamba activate "${SANDBOX_BUILD_DIR}/rvenv/venv_subset"
set -u


# Install additional R packages via conda
set +u
mamba install -y \
-p "${SANDBOX_BUILD_DIR}/rvenv/venv_subset" \
-c conda-forge \
r-rcpp r-gifski r-sourcetools r-rnaturalearth \
r-later r-promises r-httpuv r-shiny r-leaflet \
r-units r-maptiles r-fst r-leaflet.extras r-ncdf4
set -u
# Run R dependency installer
Rscript "${SANDBOX_DIR}/src/R/install_load_libs.R"

echo "Environment setup complete."
