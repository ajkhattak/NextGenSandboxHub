###############################################################
# Author      : Ahmad Jan Khattak [ahmad.jan.khattak@noaa.gov | September 10, 2024]
# Contributor : Sifan A. Koriche [sakoriche@ua.edu | December 18, 2024]

# NOTE : See utils/setup_hpc.sh to load the required modules and setup the env for building ngen and models

###############################################################
# Set build options below. Turn ON or OFF as needed.
# For first-time setup, build all components in the following order:
#   1. NGEN
#   2. MODELS
#   3. T-ROUTE

BUILD_NGEN=OFF      # Required first
BUILD_MODELS=ON     # Build after NGEN
BUILD_TROUTE=ON    # Build after MODELS

HF_VERSION=2.2     # provide hydrofabric version

###############################################################
# Check if current active venv matches the sandbox venv
VENV_SANDBOX="$SANDBOX_BUILD_DIR/venv/venv_sandbox_py3.11"

# Expand ~ and/or convert to absolute path
SANDBOX_ENV=$(realpath "$VENV_SANDBOX" 2>/dev/null)

# Convert VIRTUAL_ENV to absolute path too
CURRENT_ENV=$(realpath "$VIRTUAL_ENV" 2>/dev/null)

if [ "$CURRENT_ENV" != "$SANDBOX_ENV" ]; then
    echo "Error: This script must be run inside the sandbox environment:"
    echo "Expected: $SANDBOX_ENV"
    echo "Current : ${CURRENT_ENV:-<none>}"
    exit 1
fi
###############################################################


###############################################################

build_ngen()
{
    pushd $SANDBOX_BUILD_DIR
    git clone https://github.com/NOAA-OWP/ngen
    cd ngen
    git submodule update --init --recursive

    export builddir="cmake_build"
    rm -rf ${builddir}
    cmake -DCMAKE_BUILD_TYPE=Release \
	  -DNGEN_WITH_BMI_FORTRAN=ON \
	  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
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
    cmake --build ${builddir} --target ngen -j8
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
    MAKEFILE_PATH="src/kernel/reservoir/makefile"
    
    # Only patch on Linux
    if [ "$(uname)" = "Linux" ]; then
	# Check if nf-config is available
	if command -v nf-config &>/dev/null; then
            NETCDF_FORTRAN_CONFIG="nf-config"
	else
            echo "Error: nf-config not found on Linux."
            exit 1
	fi

        echo "Patching $MAKEFILE_PATH to use $NETCDF_FORTRAN_CONFIG..."
        sed -i "s/nc-config/$NETCDF_FORTRAN_CONFIG/g" "$MAKEFILE_PATH"

    fi

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

    for model in noah-owp-modular cfe evapotranspiration SoilFreezeThaw SoilMoistureProfiles CASAM snow17 sac-sma; do
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

	if [ "$model" == "sac-sma" ]; then
	    repo_url="https://github.com/NGWPC/sac-sma"
	    dest_dir="extern/${model}/${model}"

	    # Check if repo directory exists
	    if [ -d "$dest_dir/.git" ]; then
		echo "Repository already exists — updating..."
		git -C "$dest_dir" pull --ff-only
	    else
		echo "Cloning repository..."
		git clone "$repo_url" "$dest_dir"
	    fi

	    cp "${dest_dir}/ngen_files/sacbmi.pc.in" "${dest_dir}/ngen_files/CMakeLists.txt" "extern/${model}"

	    cmake -B "${dest_dir}/${builddir}" -S "extern/${model}" -DCMAKE_BUILD_TYPE=Release
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



