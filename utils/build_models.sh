###############################################################
# Author      : Ahmad Jan Khattak [ahmad.jan.khattak@noaa.gov | September 10, 2024]
# Contributor : Sifan A. Koriche [sakoriche@ua.edu | December 18, 2024]

# If running on AWS EC2 instance, run setup_ec2.sh before bulding models to setup the EC2 instance

# Step 1: Clone NextGen
#         - git clone https://github.com/NOAA-OWP/ngen && cd ngen
#         - git submodule update --init --recursive
# Step 2: Setup bash file
#         - Refer to the instructions here: (utils/setup_ec2.sh, line 23)
#         - For a quick reference: set the following environment variables in your bash file
#           export CC=/usr/local/opt/gcc@11/bin/gcc-11
#           export CXX=/usr/local/opt/gcc@11/bin/g++-11
#           export FC=/usr/local/opt/gcc@11/bin/gfortran-11
#           export F90=${FC}  # Alias for Fortran compiler
#           export CFORT=${FC}  # Alias for Fortran compiler
#           export NETCDF_ROOT=/usr/local/opt/netcdf-fortran
#           export PATH="/usr/local/opt/gcc@11/bin:$PATH"
		    

###############################################################
# Set build options below. Turn ON or OFF as needed.
# For first-time setup, build all components in the following order:
#   1. NGEN
#   2. MODELS
#   3. T-ROUTE

BUILD_NGEN=OFF      # Required first
BUILD_MODELS=ON    # Build after NGEN
BUILD_TROUTE=OFF    # Build after MODELS

HF_VERSION=2.2     # provide hydrofabric version

NGEN_DIR=~/Lauren/ngen_NGSH/ngen

# Check if ngen directory exists
if [ ! -d "$NGEN_DIR" ]; then
    echo "Error: ngen directory does not exist: $NGEN_DIR"
    exit 1
fi

# Check if it's a git repository
if [ ! -d "$NGEN_DIR/.git" ]; then
    echo "Error: ngen directory exists but is not a Git repository: $NGEN_DIR"
    exit 1
fi


###############################################################
# Check if current active venv matches the sandbox venv
sandbox_config="./utils/build_sandbox.sh"
if [ -f "$sandbox_config" ]; then
    VENV_SANDBOX=$(grep -E '^VENV_SANDBOX=' "$sandbox_config" | head -n1 | cut -d'=' -f2-)
else
    echo "Error: Config file not found: $config_file"
    exit 1
fi

# Expand the tilde (~) to full path
VENV_SANDBOX=$(eval echo "$VENV_SANDBOX")

if [ "$VIRTUAL_ENV" != "$VENV_SANDBOX" ]; then
    echo "Error: This script must be run inside the sandbox environment:"
    echo "Expected: $VENV_SANDBOX"
    echo "Current : ${VIRTUAL_ENV:-<none>}"
    exit 1
fi
###############################################################


###############################################################

build_ngen()
{
    pushd $NGEN_DIR
	export builddir="cmake_build"
    rm -rf ${builddir}

    cmake -DCMAKE_BUILD_TYPE=Release \
	  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
	  -DNGEN_WITH_BMI_FORTRAN=ON \
	  -DNGEN_WITH_NETCDF=ON \
	  -DNGEN_WITH_SQLITE=ON \
	  -DNGEN_WITH_ROUTING=ON \
	  -DNGEN_WITH_EXTERN_ALL=ON  \
	  -DNGEN_WITH_TESTS=ON \
          -DNGEN_QUIET=ON \
	  -DNGEN_WITH_MPI=ON \
	  -DNetCDF_ROOT=${NETCDF_ROOT}/lib \
	  -B ${builddir} \
	  -S .

    #make -j8 -C ${builddir}
    # run the following if ran into tests timeout issues
    cmake --build cmake_build --target ngen -j8
    popd
}


build_troute()
{
    if [ ${HF_VERSION} == 2.2 ]; then
	pushd $NGEN_DIR/extern
	git clone https://github.com/aaraney/t-route t-route-hf2.2
	cd t-route-hf2.2
	git checkout hf_2_2_support_sans_seans_fork
    else
	pushd $NGEN_DIR/extern/t-route
	git checkout master
	git pull
    fi

    ##hot patch nc config to nf config
    #sed -i 's/nc-config/nf-config/g' src/kernel/reservoir/makefile

    if [[ "$(uname)" == "Darwin" ]]; then
	NETCDF=$(brew --prefix netcdf-fortran)/include LIBRARY_PATH=$(brew --prefix gcc)/lib/gcc/current/:$(brew --prefix)/lib:$LIBRARY_PATH FC=$FC CC=$CC F90=$FC ./compiler.sh no-e
    else
	export NETCDF=${NETCDF_ROOT}/include
	./compiler.sh no-e
    fi

    popd
}



build_models()
{
    pushd $NGEN_DIR

    export builddir="cmake_build"

    for model in noah-owp-modularx cfex evapotranspirationx SoilFreezeThawx SoilMoistureProfilesx CASAM snow17; do
	rm -rf extern/$model/${builddir}
	if [ "$model" == "noah-owp-modular" ]; then
	    git submodule update --remote extern/${model}/${model}
	    cmake -B extern/${model}/${builddir} -S extern/${model} -DCMAKE_BUILD_TYPE=Release -DNGEN_IS_MAIN_PROJECT=ON
	    make -C extern/${model}/${builddir}
	fi
	if [ "$model" == "cfe" ] || [ "$model" == "SoilFreezeThaw" ] || [ "$model" == "SoilMoistureProfiles" ]; then
	    git submodule update --remote extern/${model}/${model}
	    cmake -B extern/${model}/${model}/${builddir} -S extern/${model}/${model} -DNGEN=ON -DCMAKE_BUILD_TYPE=Release
	    make -C extern/${model}/${model}/${builddir}
	fi
	
	if [ "$model" == "CASAM" ]; then
	    repo_url="https://github.com/NOAA-OWP/LGAR-C"
	    dest_dir="extern/${model}/${model}"

	    # Check if repo directory exists
	    if [ -d "$dest_dir/.git" ]; then
		echo "Repository already exists — updating..."
		git -C "$dest_dir" pull --ff-only
	    else
		echo "Cloning repository..."
		git clone "$repo_url" "$dest_dir"
	    fi
  
	    cmake -B extern/${model}/${model}/${builddir} -S extern/${model}/${model} -DNGEN=ON -DCMAKE_BUILD_TYPE=Release
	    make -C extern/${model}/${model}/${builddir}
	fi

	if [ "$model" == "evapotranspiration" ]; then
	    git submodule update --remote extern/${model}/${model}
	    cmake -B extern/${model}/${model}/${builddir} -S extern/${model}/${model} -DCMAKE_BUILD_TYPE=Release
	    make -C extern/${model}/${model}/${builddir}
	fi

	if [ "$model" == "snow17" ]; then
	    repo_url="https://github.com/NGWPC/snow17"
	    dest_dir="extern/${model}/${model}"

	    # Check if repo directory exists
	    if [ -d "$dest_dir/.git" ]; then
		echo "Repository already exists — updating..."
		git -C "$dest_dir" pull --ff-only
	    else
		echo "Cloning repository..."
		git clone "$repo_url" "$dest_dir"
	    fi

	    cp -r ./extern/iso_c_fortran_bmi "extern/${model}/"

	    cmake -B "${dest_dir}/${builddir}" -S "$dest_dir" -DCMAKE_BUILD_TYPE=Release
	    make -C "${dest_dir}/${builddir}"
	fi

    done

    popd
}


if [ "$BUILD_NGEN" == "ON" ]; then
    echo "NextGen build: ${BUILD_NGEN}"
    build_ngen
fi
if [ "$BUILD_MODELS" == "ON" ]; then
    echo "Models build: ${BUILD_MODELS}"
    build_models
fi
if [ "$BUILD_TROUTE" == "ON" ]; then
    echo "Troute build: ${BUILD_TROUTE}"
    build_troute
fi


#if [ "$model" == "ngen-cal" ] && [ "$BUILD_CALIB" == "ON" ]; then
#    git clone https://github.com/NOAA-OWP/ngen-cal extern/${model}
#    pip install -e extern/${model}/python/ngen_cal
#    # or try installing this way
#    #pip install "git+https://github.com/noaa-owp/ngen-cal@master#egg=ngen_cal&subdirectory=python/ngen_cal"
#    #pip install "git+https://github.com/aaraney/ngen-cal@forcing-hotfix#egg=ngen_cal&subdirectory=python/ngen_cal"
#    #cd ${wkdir}
#fi



