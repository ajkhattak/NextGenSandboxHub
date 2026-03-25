###############################################################
# Author : Ahmad Jan Khattak [ahmad.jan.khattak@noaa.gov | September 10, 2024]
# Contributor : Sifan A. Koriche [sakoriche@ua.edu | December 18, 2024]

# Clone NextGenSandboxHub repository
# git clone https://github.com/ajkhattak/NextGenSandboxHub && cd NextGenSandboxHub
# Run: BASH_FILE=~/.bash_profile BUILD=ON ./utils/build_sandbox.sh

###############################################################

###### Config #######
BUILD_SANDBOX=${BUILD:-ON}

mkdir -p "$SANDBOX_BUILD_DIR"

echo "Sandbox dir       : $SANDBOX_DIR"
echo "Sandbox build dir : $SANDBOX_BUILD_DIR"
echo "Sandbox VENV      : $VENV_SANDBOX_PATH"
echo "Forcing VENV      : $VENV_FORCING_PATH"


############################################
# NEEDED WHEN HOME DIR HAS LIMITED STORAGE QUOTA (HPC SETTINGS)
############################################
export SCRATCH_BASE="$SANDBOX_BUILD_DIR"
mkdir -p "$SCRATCH_BASE/tmp" "$SCRATCH_BASE/pip_cache"

export TMPDIR="$SCRATCH_BASE/tmp"
export TEMP="$SCRATCH_BASE/tmp"
export TMP="$SCRATCH_BASE/tmp"
export PIP_CACHE_DIR="$SCRATCH_BASE/pip_cache"

#####################################################
build_sandbox()
{

    # FIND PYTHON >= 3.11
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            if "$cmd" -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" &>/dev/null; then
                PYTHON_CMD="$cmd"
                break
            fi
        fi
    done

    if [ -z "$PYTHON_CMD" ]; then
        echo "ErrorMsg: Python >= 3.11 is required and not found in PATH."
        return 1
    fi

    PY_VERSION=$("$PYTHON_CMD" -c "import sys; print(sys.version.split()[0])")
    echo "Using Python: $PYTHON_CMD ($PY_VERSION)"


    # -------------------------------
    # USE CONDA IF AVAILABLE
    # -------------------------------
    if command -v conda &>/dev/null; then
        echo "Conda detected — building sandbox with conda"
        source "$(conda info --base)/etc/profile.d/conda.sh"

        # Create conda environment if it doesn't exist
        if [ ! -d "$VENV_SANDBOX_PATH" ]; then
            echo "Creating conda environment at $VENV_SANDBOX_PATH"
            conda create -y -p "$VENV_SANDBOX_PATH" python=3.11
        fi

	conda activate "$VENV_SANDBOX_PATH"

	# To remove conda env long prefix 
	conda config --set env_prompt '({name})'

	python -m pip install --upgrade pip --no-cache-dir
	pip install "setuptools>=64.0,<69.0" wheel
        # Optional: safe numba/llvmlite from conda-forge
        conda install -y -c conda-forge numba==0.63 llvmlite
	conda install -y pycares=4.11.0 # need for ngen-cal

	#Save how to activate (use conda activate)
	if ! grep -qxF "export SANDBOX_VENV='$VENV_SANDBOX_PATH'" "$TARGET_FILE"; then
            echo "export SANDBOX_VENV='$VENV_SANDBOX_PATH'" >> "$TARGET_FILE"
	fi

    else
        # -------------------------------
        # FALLBACK TO VIRTUALENV
        # -------------------------------
	echo "Conda not found -- building sandbox virtual python environment ($VENV_SANDBOX_PATH)"
        mkdir -p "$VENV_SANDBOX_PATH"
        $PYTHON_CMD -m venv "$VENV_SANDBOX_PATH"
        source "$VENV_SANDBOX_PATH/bin/activate"
	python -m pip install --upgrade pip --no-cache-dir
	pip install "setuptools>=64.0,<69.0" wheel

	if ! grep -qxF "export SANDBOX_VENV='$VENV_SANDBOX_PATH/bin/activate'" "$TARGET_FILE"; then
            echo "export SANDBOX_VENV='$VENV_SANDBOX_PATH/bin/activate'" >> "$TARGET_FILE"
	fi

    fi
    
    pip install -e .

    git submodule update --init --recursive
    git submodule update --remote extern/ngen-cal
    git submodule update --remote extern/CIROH_DL_NextGen
    git submodule update --remote extern/lstm
    
    pip install --no-cache-dir 'extern/ngen-cal/python/ngen_cal[netcdf]'
    pip install --no-cache-dir extern/ngen-cal/python/ngen_conf
    pip install -e ./extern/ngen_cal_plugins
    pip install -e ./extern/lstm

    echo "Sandbox Python Environment Created ($VENV_SANDBOX_PATH)"
    
    if command -v conda &>/dev/null; then
        conda deactivate
    else
        deactivate
    fi

    ############################################
    # FORCING
    ############################################
    echo "Creating virtual python environment for forcing downloader ($VENV_FORCING_PATH)"

    if command -v conda >/dev/null 2>&1; then
	source "$(conda info --base)/etc/profile.d/conda.sh"

	if [ ! -d "$VENV_FORCING_PATH" ]; then
            echo "Creating conda forcing environment at $VENV_FORCING_PATH"
            conda create -y -p "$VENV_FORCING_PATH" python=3.11
        fi

	conda activate "$VENV_FORCING_PATH"
	python -m pip install --upgrade pip --no-cache-dir
	pip install --no-cache-dir -r ./doc/env/requirements_forcing.txt

	conda deactivate

    else
	echo "Conda not found -- building forcing virtual python environment ($VENV_FORCING_PATH)"

	mkdir -p "$VENV_FORCING_PATH"

	$PYTHON_CMD -m venv "$VENV_FORCING_PATH"
	source "$VENV_FORCING_PATH/bin/activate"
	python -m pip install --upgrade pip --no-cache-dir
	pip install --no-cache-dir -r ./doc/env/requirements_forcing.txt

	deactivate
    fi

    echo "Forcing environment created successfully ($VENV_FORCING_PATH)"
}


############################################
# ENTRY POINT
############################################
if [[ "$BUILD_SANDBOX" == "ON" ]]; then
    echo "=== Building NextGen Sandbox ==="
    build_sandbox
else
    echo "BUILD=OFF — skipping"
fi
