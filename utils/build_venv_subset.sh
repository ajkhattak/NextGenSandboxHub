#!/usr/bin/env bash
set -euo pipefail

export CONDA_NO_PLUGINS=true
#CONDA_SOLVER=classic # required for macOS
#CONDA_SOLVER=libmamba # already the mamba default

eval "$(conda shell.bash hook)"

mkdir -p "${SANDBOX_BUILD_DIR}/rvenv/conda_envs"
mkdir -p "${SANDBOX_BUILD_DIR}/rvenv/conda_pkgs"
conda config --add envs_dirs "${SANDBOX_BUILD_DIR}/rvenv/conda_envs"
conda config --add pkgs_dirs "${SANDBOX_BUILD_DIR}/rvenv/conda_pkgs"
conda config --set channel_priority strict
conda config --set safety_checks disabled

if [ ! -d "${SANDBOX_BUILD_DIR}/rvenv/mamba" ]; then
  conda create -y -p "${SANDBOX_BUILD_DIR}/rvenv/mamba" -c conda-forge mamba
fi

eval "$("${SANDBOX_BUILD_DIR}/rvenv/mamba/bin/mamba" shell hook --shell bash)"
set +u; mamba activate "${SANDBOX_BUILD_DIR}/rvenv/mamba"; set -u

if [ ! -d "${SANDBOX_BUILD_DIR}/rvenv/venv_subset" ]; then
  # Use lockfile if available (fast), otherwise solve from YAML (slow, first time)
  if [ -f "${SANDBOX_DIR}/utils/venv/venv_subset.lock" ]; then
    echo "Using lockfile — skipping solver"
    conda create -y -p "${SANDBOX_BUILD_DIR}/rvenv/venv_subset" \
      --file "${SANDBOX_DIR}/utils/venv/venv_subset.lock"
  else
    echo "No lockfile found — solving from YAML (this will be slow once)"
    mamba env create -y -p "${SANDBOX_BUILD_DIR}/rvenv/venv_subset" \
      -f "${SANDBOX_DIR}/utils/venv/venv_subset.yaml"
    # Save lockfile for next time
    conda list -p "${SANDBOX_BUILD_DIR}/rvenv/venv_subset" --explicit \
      > "${SANDBOX_DIR}/utils/venv/venv_subset.lock"
  fi
fi

set +u; mamba activate "${SANDBOX_BUILD_DIR}/rvenv/venv_subset"; set -u

Rscript "${SANDBOX_DIR}/src/R/install_load_libs.R"
echo "Environment setup complete."
