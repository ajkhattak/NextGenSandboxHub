###############################################################
# Author : Ahmad Jan Khattak [ahmad.jan.khattak@noaa.gov | September 10, 2024]
# Contributor : Sifan A. Koriche [sakoriche@ua.edu | December 18, 2024]

# Clone NextGenSandboxHub repository
# git clone https://github.com/ajkhattak/NextGenSandboxHub && cd NextGenSandboxHub
# Run: ./utils/build_sandbox.sh

###############################################################

BUILD_SANDBOX=ON

BASH_FILE="$HOME/.bash_profile"  # <- change this to your local settings

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Script directory: $SCRIPT_DIR"

SANDBOX_DIR="$(dirname "$SCRIPT_DIR")"
echo "Sandbox directory: $SANDBOX_DIR"

SANDBOX_BUILD_DIR="$(dirname "$SANDBOX_DIR")/sandbox_build"
NGEN_DIR="$SANDBOX_BUILD_DIR/ngen"

mkdir -p "$SANDBOX_BUILD_DIR"
echo "Sandbox build directory: $SANDBOX_BUILD_DIR"

VENV_SANDBOX_PATH="$SANDBOX_BUILD_DIR/venv/venv_sandbox_py3.11"
VENV_FORCING_PATH="$SANDBOX_BUILD_DIR/venv/venv_forcing"
PYTHON_VERSION="python3.11"


# reload the updated bash profile
source "$BASH_FILE"


#####################################################
build_sandbox()
{    
    # Check if python3.11 is available
    if ! command -v $PYTHON_VERSION &>/dev/null; then
        echo "ErrorMsg: $PYTHON_VERSION is not installed or not in your PATH."
        return 1
    fi

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
        $PYTHON_VERSION -m venv "$VENV_SANDBOX_PATH"
        source "$VENV_SANDBOX_PATH/bin/activate"
        pip install -U pip==24.0 "setuptools>=64.0,<69.0" wheel
	#conda install pycares=4.11.0 # needed for ngen-cal

	if ! grep -qxF "export SANDBOX_VENV='$VENV_SANDBOX_PATH/bin/activate'" "$BASH_FILE"; then
            echo "export SANDBOX_VENV='$VENV_SANDBOX_PATH/bin/activate'" >> "$BASH_FILE"
	fi

    fi

    pip install -e .

    git submodule update --init
    git submodule update --remote extern/ngen-cal
    git submodule update --remote extern/CIROH_DL_NextGen
    git submodule update --remote extern/lstm
    
    pip install 'extern/ngen-cal/python/ngen_cal[netcdf]'
    #pip install extern/ngen-cal/python/ngen_config_gen
    pip install extern/ngen-cal/python/ngen_conf
    #pip install hydrotools.events
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
    mkdir -p "$VENV_FORCING_PATH"
    $PYTHON_VERSION -m venv "$VENV_FORCING_PATH"
    source "$VENV_FORCING_PATH/bin/activate"
    
    pip install -U pip==24.0
    pip install -r ./doc/env/requirements_forcing.txt
    # or run the below two steps
    # pip install -r extern/CIROH_DL_NextGen/forcing_prep/requirements.txt
    # pip install zarr==2.18.2
    deactivate

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


if [ "$BUILD_SANDBOX" == "ON" ]; then
    echo "Building Python Virtual Environments for NextGen Sandbox"
    build_sandbox
fi
