###############################################################
# Author : Ahmad Jan Khattak [ahmad.jan.khattak@noaa.gov | September 10, 2024]
# Contributor : Sifan A. Koriche [sakoriche@ua.edu | December 18, 2024]

# Clone NextGenSandboxHub repository
# git clone https://github.com/ajkhattak/NextGenSandboxHub && cd NextGenSandboxHub
# Run: BASH_FILE=~/.bash_profile BUILD=ON ./utils/build_sandbox.sh

###############################################################

###### Config #######
BUILD_SANDBOX=${BUILD:-ON}

BASH_FILE="${BASH_FILE:-$HOME/.zshrc}" # <- change this to your local settings or provide it as env variable

echo "$BUILD_SANDBOX"       # empty
echo "$BASH_FILE"           # still defaults to ~/.zshrc


######## PATHS #########

SANDBOX_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SANDBOX_BUILD_DIR="$(dirname "$SANDBOX_DIR")/sandbox_build"
NGEN_DIR="$SANDBOX_BUILD_DIR/ngen"

VENV_SANDBOX_PATH="$SANDBOX_BUILD_DIR/venv/venv_sandbox_py3.11"
VENV_FORCING_PATH="$SANDBOX_BUILD_DIR/venv/venv_forcing"

mkdir -p "$SANDBOX_BUILD_DIR"

echo "Sandbox dir       : $SANDBOX_DIR"
echo "Sandbox build dir : $SANDBOX_BUILD_DIR"
echo "Sandbox VENV      : $VENV_SANDBOX_PATH"
echo "Forcing VENV      : $VENV_FORCING_PATH"

append_if_missing() {
    local line="$1"
    grep -qxF "$line" "$BASH_FILE" || echo "$line" >> "$BASH_FILE"
}

# reload the updated bash profile
source "$BASH_FILE"


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

	pip install -U pip setuptools wheel
        # Optional: safe numba/llvmlite from conda-forge
        conda install -y -c conda-forge numba==0.63 llvmlite
	conda install -y pycares=4.11.0 # need for ngen-cal

	#Save how to activate (use conda activate)
	if ! grep -qxF "export SANDBOX_VENV='$VENV_SANDBOX_PATH'" "$BASH_FILE"; then
            echo "export SANDBOX_VENV='$VENV_SANDBOX_PATH'" >> "$BASH_FILE"
	fi

    else
        # -------------------------------
        # FALLBACK TO VIRTUALENV
        # -------------------------------
	echo "Conda not found -- building sandbox virtual python environment ($VENV_SANDBOX_PATH)"
        mkdir -p "$VENV_SANDBOX_PATH"
        $PYTHON_CMD -m venv "$VENV_SANDBOX_PATH"
        source "$VENV_SANDBOX_PATH/bin/activate"
        pip install -U pip==24.0 "setuptools>=64.0,<69.0" wheel

	if ! grep -qxF "export SANDBOX_VENV='$VENV_SANDBOX_PATH/bin/activate'" "$BASH_FILE"; then
            echo "export SANDBOX_VENV='$VENV_SANDBOX_PATH/bin/activate'" >> "$BASH_FILE"
	fi

    fi

    append_if_missing "export SANDBOX_DIR='$SANDBOX_DIR'"
    append_if_missing "export SANDBOX_BUILD_DIR='$SANDBOX_BUILD_DIR'"
    append_if_missing "export NGEN_DIR='$NGEN_DIR'"
    
    pip install -e .

    git submodule update --init --recursive
    git submodule update --remote extern/ngen-cal
    git submodule update --remote extern/CIROH_DL_NextGen
    git submodule update --remote extern/lstm
    
    pip install 'extern/ngen-cal/python/ngen_cal[netcdf]'
    pip install extern/ngen-cal/python/ngen_conf
    pip install -e ./extern/ngen_cal_plugins

    # also install lstm
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
	echo "Conda detected. Creating conda environment: $VENV_FORCING_PATH"
	source "$(conda info --base)/etc/profile.d/conda.sh"

	conda create -y -p "$VENV_FORCING_PATH" python=3.11

	conda activate "$VENV_FORCING_PATH"

	pip install -U pip==25.0
	pip install -r ./doc/env/requirements_forcing.txt

	conda deactivate

    else
	echo "Conda not found -- building forcing virtual python environment ($VENV_FORCING_PATH)"

	mkdir -p "$VENV_FORCING_PATH"

	$PYTHON_CMD -m venv "$VENV_FORCING_PATH"
	source "$VENV_FORCING_PATH/bin/activate"

	pip install -U pip==25.0
	pip install -r ./doc/env/requirements_forcing.txt

	deactivate
    fi
 
    echo "sourcing bash file"
    source $BASH_FILE
    
    ############################################
    # LSTM
    ############################################
    #VENV_LSTM=~/.venv_lstm

    #mkdir "$VENV_LSTM"
    #$PYTHON_VERSION -m venv "$VENV_LSTM"
    #source "$VENV_LSTM/bin/activate"
    
    #pip install -U pip==24.0
    #pip install -e ./extern/lstm
    #deactivate
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
