#!/usr/bin/env bash

# Customizable build and runtime profile for NextGenSandbox.
# Source this file; do not execute it:
#   source /path/to/sandbox_profile.sh

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "ERROR: Source this profile instead of executing it:"
    echo "  source ${BASH_SOURCE[0]}"
    exit 1
fi

PROFILE_SOURCE="${BASH_SOURCE[0]}"
PROFILE_DIR="$(cd "$(dirname "$PROFILE_SOURCE")" && pwd)"

# This default works while the profile remains under <repo>/configs. If you
# copy it elsewhere, replace the value with the absolute repository path.
SANDBOX_REPO="${SANDBOX_REPO:-$(cd "$PROFILE_DIR/.." && pwd)}"

if [ ! -f "$SANDBOX_REPO/scripts/bootstrap/sandbox_env.sh" ]; then
    echo "ERROR: NextGenSandbox was not found at: $SANDBOX_REPO"
    echo "Set SANDBOX_REPO in $PROFILE_SOURCE to the repository path."
    return 1
fi

# Customize this section for the compiler/MPI stack on the current system.
# Keep every compiler-dependent build in its own directory.
#
# module --force purge
# module load intel/19.1.3.304
# module load openmpi/4.1.6
# module load sqlite/3.35.5
# module load udunits/2.2.28
# module load cmake/3.20.0
# module load netcdf-fortran/4.5.3
# module load conda/2026.03
#
# export SANDBOX_BUILD_DIR="$SANDBOX_REPO/build/intel"
# export CC="$(command -v mpicc)"
# export CXX="$(command -v mpicxx)"
# export FC="$(command -v mpifort)"
# export F90="$FC"
# export F77="$FC"
# export NETCDF_ROOT="$(nf-config --prefix)"
# export BOOST_ROOT="/path/to/boost"

export SANDBOX_BUILD_DIR="${SANDBOX_BUILD_DIR:-$SANDBOX_REPO/build}"
export SANDBOX_CONDARC="$SANDBOX_BUILD_DIR/condarc"
export SANDBOX_ENV_PERSIST=OFF

# Load repository paths for this shell/job only. This does not edit .bashrc,
# .bash_profile, or .zshrc.
source "$SANDBOX_REPO/scripts/bootstrap/sandbox_env.sh" PERSIST=OFF

if [ -x "$SANDBOX_ENV/bin/python" ]; then
    if command -v conda >/dev/null 2>&1; then
        CONDA_BASE="$(conda info --base)"
        if [ -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then
            source "$CONDA_BASE/etc/profile.d/conda.sh"
        fi
        conda activate "$SANDBOX_ENV"
    elif [ -f "$SANDBOX_ENV/bin/activate" ]; then
        source "$SANDBOX_ENV/bin/activate"
    fi
else
    echo "Sandbox environment has not been built for this profile."
    echo "  Run: $SANDBOX_REPO/bootstrap.sh --sandbox"
fi

export PATH="$SANDBOX_ENV/bin:$PATH"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"

echo "NextGenSandbox profile loaded."
echo "  Repository : $SANDBOX_DIR"
echo "  Build      : $SANDBOX_BUILD_DIR"
echo "  Environment: $SANDBOX_ENV"
