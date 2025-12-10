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

VENV_SANDBOX="$SANDBOX_BUILD_DIR/venv/venv_sandbox_py3.11"
VENV_FORCING="$SANDBOX_BUILD_DIR/venv/venv_forcing"
PYTHON_VERSION="python3.11"

add_export() {
    local var_name=$1
    local var_value=$2
    local file=$3

    # line we want to add
    local line="export ${var_name}='${var_value}'"

    # check if it already exists
    if ! grep -Fxq "$line" "$file"; then
        echo "$line" >> "$file"
    fi
}

add_export "SANDBOX_DIR" "$SANDBOX_DIR" "$BASH_FILE"
add_export "SANDBOX_BUILD_DIR" "$SANDBOX_BUILD_DIR" "$BASH_FILE"
add_export "NGEN_DIR" "$NGEN_DIR" "$BASH_FILE"
add_export "SANDBOX_VENV" "$VENV_SANDBOX/bin/activate" "$BASH_FILE"


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
    
    echo "Creating virtual python environment for sandbox ($VENV_SANDBOX)"
    mkdir -p "$VENV_SANDBOX"
    $PYTHON_VERSION -m venv "$VENV_SANDBOX"
    source "$VENV_SANDBOX/bin/activate"

    pip install -U pip==24.0 "setuptools>=64.0,<69.0" wheel
    
    pip install -e .

    git submodule update --init
    git submodule update --remote extern/ngen-cal
    git submodule update --remote extern/CIROH_DL_NextGen
    git submodule update --remote extern/lstm
    
    pip install 'extern/ngen-cal/python/ngen_cal[netcdf]'
    pip install extern/ngen-cal/python/ngen_config_gen
    pip install extern/ngen-cal/python/ngen_conf
    pip install hydrotools.events
    pip install -e ./extern/ngen_cal_plugins

    # also install lstm
    pip install -e ./extern/lstm

    echo "Virtual Python Environment Created ($VENV_SANDBOX)"
    deactivate

    ############################################
    # FORCING
    ############################################
    echo "Creating virtual python environment for forcing downloader ($VENV_FORCING)"
    mkdir -p "$VENV_FORCING"
    $PYTHON_VERSION -m venv "$VENV_FORCING"
    source "$VENV_FORCING/bin/activate"
    
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
