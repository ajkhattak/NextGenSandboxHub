###############################################################
# Author : Ahmad Jan Khattak [ahmad.jan.khattak@noaa.gov | September 10, 2024]
# Contributor : Sifan A. Koriche [sakoriche@ua.edu | December 18, 2024]

# If running on AWS EC2 instance, run setup_ec2.sh before bulding models to setup the EC2 instance

# Clone NextGenSandboxHub and NextGen GitHub repositories
# Step 1: Clone NextGenSandboxHub
#         - git clone https://github.com/ajkhattak/NextGenSandboxHub && cd NextGenSandboxHub
# Step 2: Setup bash file
#         - Refer to the instructions here: (utils/setup_ec2.sh, line 23)

###############################################################

BUILD_SANDBOX=ON
# if it is desired to change the virtual env name, it will require one more change to
# the sandbox.py file (update the env name there as well)
VENV_SANDBOX=~/.venv_sandbox_py3.11

#####################################################


build_sandbox()
{

    PYTHON_VERSION="python3.11"
    
    # Check if python3.11 is available
    if ! command -v $PYTHON_VERSION &>/dev/null; then
        echo "ErrorMsg: $PYTHON_VERSION is not installed or not in your PATH."
        return 1
    fi
    
    echo "Creating virtual python environment for ngen ($VENV_SANDBOX)"
    mkdir "$VENV_SANDBOX"
    $PYTHON_VERSION -m venv "$VENV_SANDBOX"
    source "$VENV_SANDBOX/bin/activate"
    
    pip install -U pip==24.0
    
    #pip install -r ./utils/requirements.txt
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
    
    deactivate

    ############################################
    # FORCING
    ############################################
    
    VENV_FORCING=~/.venv_forcing

    mkdir "$VENV_FORCING"
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
    VENV_LSTM=~/.venv_lstm

    mkdir "$VENV_LSTM"
    $PYTHON_VERSION -m venv "$VENV_LSTM"
    source "$VENV_LSTM/bin/activate"
    
    pip install -U pip==24.0
    pip install -e ./extern/lstm
    deactivate
}


if [ "$BUILD_SANDBOX" == "ON" ]; then
    echo "Building Python Virtual Environments for NextGen Sandbox"
    build_sandbox
fi
