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

export wkdir=$(pwd)
export builddir="cmake_build"
cd ${wkdir}

###############################################################
# Set build options below. Turn ON or OFF as needed.
# For first-time setup, build all components in the following order:
#   1. NGEN
#   2. MODELS
#   3. T-ROUTE

BUILD_NGEN=ON      # Required first
BUILD_MODELS=ON    # Build after NGEN
BUILD_TROUTE=ON    # Build after MODELS

HF_VERSION=2.0     # provide hydrofabric version

ngen_dir=/home/Ahmad.Jan.Khattak/Code/ngen

###############################################################

build_ngen()
{
    pushd $ngen_dir

    rm -rf ${builddir}
    cmake -DCMAKE_BUILD_TYPE=Release \
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
    if [ ${HF_VERSION} == 2.0 ]; then
	pushd $ngen_dir/extern
	git clone https://github.com/aaraney/t-route t-route-hf2.0
	cd t-route-hf2.0
	git checkout hf_2_2_support_sans_seans_fork
    else
	pushd $ngen_dir/extern/t-route
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
    pushd $ngen_dir

    for model in noah-owp-modular cfe evapotranspiration SoilFreezeThaw SoilMoistureProfiles LGAR; do
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
	
	if [ "$model" == "LGAR" ]; then
	    git clone https://github.com/NOAA-OWP/LGAR-C extern/${model}/${model}
	    cmake -B extern/${model}/${model}/${builddir} -S extern/${model}/${model} -DNGEN=ON -DCMAKE_BUILD_TYPE=Release
	    make -C extern/${model}/${model}/${builddir}
	fi
	if [ "$model" == "evapotranspiration" ]; then
	    git submodule update --remote extern/${model}/${model}
	    cmake -B extern/${model}/${model}/${builddir} -S extern/${model}/${model} -DCMAKE_BUILD_TYPE=Release
	    make -C extern/${model}/${model}/${builddir}
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



