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
echo "Sandbox VENV      : $SANDBOX_ENV"
echo "Forcing VENV      : $FORCING_ENV"


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

	# Create or update environment
        if [ ! -d "$SANDBOX_ENV" ]; then
	    echo "Creating conda environment at $SANDBOX_ENV"
            conda env create -p "$SANDBOX_ENV" -f utils/venv/venv_sandbox.yaml
        else
	    echo "Updating conda environment at $SANDBOX_ENV"
            conda env update -p "$SANDBOX_ENV" -f utils/venv/venv_sandbox.yaml
        fi

	conda activate "$SANDBOX_ENV"

	# To remove conda env long prefix 
	conda config --set env_prompt '({name})'

	#python -m pip install --upgrade pip --no-cache-dir
	#pip install "setuptools>=64.0,<69.0" wheel
        #conda install -y -c conda-forge numba==0.63 llvmlite
	#conda install -y -c conda-forge pycares=4.11.0 # need for ngen-cal
    else
        # -------------------------------
        # FALLBACK TO VIRTUALENV
        # -------------------------------
	echo "Conda not found -- building sandbox virtual python environment ($SANDBOX_ENV)"
        mkdir -p "$SANDBOX_ENV"
        $PYTHON_CMD -m venv "$SANDBOX_ENV"
        source "$SANDBOX_ENV/bin/activate"
	python -m pip install --upgrade pip --no-cache-dir
	pip install "setuptools>=64.0,<69.0" wheel

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

    echo "Sandbox Python Environment Created ($SANDBOX_ENV)"
    
    if command -v conda &>/dev/null; then
        conda deactivate
    else
        deactivate
    fi

    ############################################
    # FORCING
    ############################################
    echo "Creating virtual python environment for forcing downloader ($FORCING_ENV)"

    if command -v conda >/dev/null 2>&1; then
	source "$(conda info --base)/etc/profile.d/conda.sh"

	if [ ! -d "$FORCING_ENV" ]; then
            echo "Creating conda forcing environment at $FORCING_ENV"
            conda create -y -p "$FORCING_ENV" python=3.11
        fi

	conda activate "$FORCING_ENV"
	python -m pip install --upgrade pip --no-cache-dir
	pip install --no-cache-dir -r ./utils/venv/requirements_forcing.txt

	conda deactivate

    else
	echo "Conda not found -- building forcing virtual python environment ($FORCING_ENV)"

	mkdir -p "$FORCING_ENV"

	$PYTHON_CMD -m venv "$FORCING_ENV"
	source "$FORCING_ENV/bin/activate"
	python -m pip install --upgrade pip --no-cache-dir
	pip install --no-cache-dir -r ./utils/venv/requirements_forcing.txt

	deactivate
    fi

    echo "Forcing environment created successfully ($FORCING_ENV)"
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
