#!/usr/bin/env bash

# NextGenSandbox build and runtime profile.
# Copy this file, customize it when needed, and source it in Bash or zsh:
#   cp configs/sandbox_profile.sh sandbox_profile.sh
#   source ./sandbox_profile.sh

if [ -n "${BASH_VERSION:-}" ]; then
    if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
        echo "ERROR: Source this profile instead of executing it:"
        echo "  source ${BASH_SOURCE[0]}"
        exit 1
    fi
    PROFILE_SOURCE="${BASH_SOURCE[0]}"
elif [ -n "${ZSH_VERSION:-}" ]; then
    if [[ "${ZSH_EVAL_CONTEXT:-}" != *:file ]]; then
        echo "ERROR: Source this profile instead of executing it:"
        echo "  source $0"
        exit 1
    fi
    PROFILE_SOURCE="${(%):-%N}"
else
    echo "ERROR: NextGenSandbox profiles support Bash and zsh."
    return 1
fi

PROFILE_DIR="$(cd "$(dirname "$PROFILE_SOURCE")" && pwd -P)"
SANDBOX_PROFILE="$PROFILE_DIR/$(basename "$PROFILE_SOURCE")"

# Profiles kept in the repository root or its configs directory locate the
# checkout automatically. A profile stored elsewhere must set SANDBOX_REPO.
# SANDBOX_REPO="/path/to/NextGenSandbox"
if [ -f "$PROFILE_DIR/scripts/bootstrap/sandbox_env.sh" ]; then
    SANDBOX_REPO="$PROFILE_DIR"
elif [ -f "$PROFILE_DIR/../scripts/bootstrap/sandbox_env.sh" ]; then
    SANDBOX_REPO="$(cd "$PROFILE_DIR/.." && pwd -P)"
else
    SANDBOX_REPO="${SANDBOX_REPO:-}"
fi

if [ ! -f "$SANDBOX_REPO/scripts/bootstrap/sandbox_env.sh" ]; then
    echo "ERROR: NextGenSandbox was not found at: $SANDBOX_REPO"
    echo "Set SANDBOX_REPO in $SANDBOX_PROFILE to the repository path."
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
# export NETCDF_ROOT="$(nf-config --prefix)"
# export BOOST_ROOT="/path/to/boost"

# Use the loaded MPI wrappers by default, replacing unrelated compiler values
# inherited from the parent shell.
if command -v mpicc >/dev/null 2>&1; then
    export CC="$(command -v mpicc)"
fi
if command -v mpicxx >/dev/null 2>&1; then
    export CXX="$(command -v mpicxx)"
elif command -v mpic++ >/dev/null 2>&1; then
    export CXX="$(command -v mpic++)"
fi
if command -v mpifort >/dev/null 2>&1; then
    export FC="$(command -v mpifort)"
elif command -v mpif90 >/dev/null 2>&1; then
    export FC="$(command -v mpif90)"
fi
if [ -n "${FC:-}" ]; then
    export F90="$FC"
    export F77="$FC"
fi
if [ -z "${NETCDF_ROOT:-}" ] && command -v nf-config >/dev/null 2>&1; then
    export NETCDF_ROOT="$(nf-config --prefix)"
fi

# Optional compiler overrides belong after the defaults above.
# export CC="/path/to/compiler"
# export CXX="/path/to/compiler"
# export FC="/path/to/compiler"
# export F90="$FC"
# export F77="$FC"

export SANDBOX_REPO
export SANDBOX_PROFILE
export SANDBOX_BUILD_DIR="${SANDBOX_BUILD_DIR:-$SANDBOX_REPO/build}"
export SANDBOX_CONDARC="$SANDBOX_BUILD_DIR/condarc"

# Load repository paths for this shell/job only. Shell startup files are never
# modified.
source "$SANDBOX_REPO/scripts/bootstrap/sandbox_env.sh"

if [ -x "$SANDBOX_ENV/bin/python" ]; then
    if [ -d "$SANDBOX_ENV/conda-meta" ]; then
        if command -v conda >/dev/null 2>&1; then
            CONDA_COMMAND="conda"
        elif [ -n "${CONDA_EXE:-}" ] && [ -x "$CONDA_EXE" ]; then
            CONDA_COMMAND="$CONDA_EXE"
        else
            echo "ERROR: $SANDBOX_ENV is a Conda environment, but conda is unavailable."
            echo "Load or install conda, then source this profile again."
            return 1
        fi

        CONDA_BASE="$("$CONDA_COMMAND" info --base)"
        if [ -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then
            source "$CONDA_BASE/etc/profile.d/conda.sh"
        fi
        conda activate "$SANDBOX_ENV"
    elif [ -f "$SANDBOX_ENV/bin/activate" ]; then
        source "$SANDBOX_ENV/bin/activate"
    else
        echo "ERROR: Cannot activate the Sandbox environment: $SANDBOX_ENV"
        return 1
    fi
else
    echo "Sandbox environment has not been built for this profile."
    echo "  Run: $SANDBOX_REPO/bootstrap.sh --sandbox"
fi

case ":$PATH:" in
    *":$SANDBOX_ENV/bin:"*) ;;
    *) export PATH="$SANDBOX_ENV/bin:$PATH" ;;
esac
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"

echo "NextGenSandbox profile loaded."
echo "  Repository : $SANDBOX_DIR"
echo "  Build      : $SANDBOX_BUILD_DIR"
echo "  Environment: $SANDBOX_ENV"
