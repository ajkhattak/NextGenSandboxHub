# Getting Started with NextGen Sandbox: Build, Configure, and Run

Detailed instructions on how to install, configure, and get the NGSandboxHub running.

### <ins>  Step 1. Build Sandbox Workflow
  1. Clone the repository (if not already done):
     ```
     git clone https://github.com/ajkhattak/NextGenSandboxHub && cd NextGenSandboxHub
     ```
  2. Ensure Python 3.11 is available:
     - Local machine: check Python version.
     - HPC system: load a compatible Python module, e.g., Python ≥ 3.11. For an example HPC setup, see [setup_hpc.sh](https://github.com/ajkhattak/NextGenSandboxHub/blob/main/utils/setup_hpc.sh)
  3. Build the Sandbox workflow:
     ```
     ./utils/build_sandbox.sh
     ```

>**NOTE:** The script installs a python env named `.venv_sandbox_py3.11` (see utils/build_sandbox.sh [here](https://github.com/ajkhattak/NextGenSandboxHub/blob/main/utils/build_sandbox.sh#L18)). This environment MUST be activated before performing any of the following steps.
  
### <ins>  Step 2. Hydrofabric Installation
Ensure R and Rtools are already installed before proceeding. There are two ways to install the required packages:
  #### Option 1: Using RStudio
  1. Open RStudio
  2. Load and run the installation script by sourcing it:
     - Open `<path_to_sandboxhub>/src/R/install_load_libs.R` in RStudio.
     - Click Source to execute the script.
     - Alternatively, run the following command in the RStudio Console:
       ```
       source("~/<path_to_sandboxhub>/src/R/install_load_libs.R")
       ```
  #### Option 2: Using the Command Line
  Run the following command in a terminal or command prompt:
  ```
   Rscript <path_to_sandboxhub>/src/R/install_load_libs.R
  ```

### <ins> Step 3. Hydrofabric Subsetting
  - Dependency: Step 2
  - Download domain (CONUS or oCONUS) from [lynker-spatial](https://www.lynker-spatial.com/data?path=hydrofabric%2Fv2.2%2F), for instance conus/conus_nextgen.gpkg
  - open `<path_to_sandboxhub>/configs/sandbox_config.yaml` [here](configs/sandbox_config.yaml) and adjust sandbox_dir, input_dir, output_dir, and subsetting according to your local settings
  - Now there are two options to proceed:
      - run `sandbox -subset`
      - or open `<path_to_sandboxhub>/src/R/main.R` in RStudio and source on main.R. Note Set file name `infile_config` [here](https://github.com/ajkhattak/NextGenSandboxHub/blob/main/src/R/main.R#L53) 
    
    Either one will install the hydrofabric and several other libraries, and if everything goes well, a basin geopackage will be subsetted and stored under `<input_dir>/<basin_id>/data/gage_<basin_id>.gpkg`

### <ins> Step 4. Forcing Data Download
The workflow uses [CIROH_DL_NextGen](https://github.com/ajkhattak/CIROH_DL_NextGen) forcing_prep tool to donwload atmospheric forcing data. It uses a Python environment (`~/.venv_forcing`) that is created during the workflow setup step (Step 1). To download the forcing data run:
```
   sandbox -forc
```

>===============================================================================
>### Note: Steps 5 and 6 require both the ngen and models builds. Please follow the instructions in the [build_models](https://github.com/ajkhattak/NextGenSandboxHub/blob/main/utils/build_models.sh) script to build ngen and models.
>================================================================================

> **Note:** The sandbox workflow assumes that [ngen](https://github.com/NOAA-OWP/ngen) and models including [t-route](https://github.com/NOAA-OWP/t-route) have been built in the Python virtual environment created in Step 1.

### <ins>  Step 5. Generate Configuration and Realization Files
Setup the sandbox config file [here](configs/sandbox_config.yaml), especially the `formulation` and `simulation` blocks, then run:
 ```
    sandbox -conf
 ```
For non-default input files, use
 ```
    sandbox -conf -i <sandbox_config_filename.yaml> -j <calib_config_filename.yaml>
 ```
### <ins> Step 6. Run Calibration/Validation Simulations
Run the following command — assuming you have already set up the sandbox configuration file [here](configs/sandbox_config.yaml) and calibration configuration file [here](configs/calib_config.yaml), and have successfully completed the steps above.
 ```
    sandbox -run
 ```
For non-default input files, use
 ```
    sandbox -run -i <sandbox_config_filename.yaml> -j <calib_config_filename.yaml>
 ```
#### Summary
1. Subset divide using hydrofabric
2. Download forcing data
3. Generate configuration files
4. Run Simulations: Using
  ```
    sandbox option
    OPTIONS = [-subset -forc -conf -run]
  ```
- Option: `-subset` downloads geopackage(s) given a gage ID(s), extracts and locally compute TWI, GIUH, and Nash Cascade parameters; see `divide-attributes` in the gage_<basin_id>.gpkg file
- Option: `-forc` downloads geopackage(s) given a gage ID(s)
- Option: `-conf` generates configuration and realization files for the selected models/basins
- Option: `-run` executes NextGen simulations with and without calibration

Note: These options can be run individually or combined together, for example, `sandbox -subset -conf -run`. The `-subset` is an expensive step, should be run once to get the desired basin geopacakge and associated model parameters.
