# Next-Generation Framework Sandbox Hub (NextGenSandboxHub)
[NextGen](https://github.com/NOAA-OWP/ngen), Next-Generation Water Resources Modeling Framework, developed by the NOAA's Office of Water Prediction is a standards-based language- and model-agnostic framework, which allows to run a mosaic of surface and subsurface models in a single basin comprised of 10s-100s sub-catchments. 

## Schematic of the NextGenSandboxHub Workflow

<div align="center">
<img src="https://github.com/user-attachments/assets/d06b3cf9-6019-4ebd-86f1-e797b4debbae" style="width:800px; height:400px;"/>
</div>

## Configuration

### <ins>  Step 1. Build Sanbox Workflow
  - `git clone https://github.com/ajkhattak/NextGenSandboxHub && cd NextGenSandboxHub`
  - `git submodule update --init`
  - Run `./utils/build_sandbox.sh` (this will install python env required for the workflow, t-route, and ngen)
  
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
      - run `python <path_to_sandboxhub>/sandbox.py -subset`
      - or open `<path_to_sandboxhub>/src/R/main.R` in RStudio and source on main.R. Note Set file name `infile_config` [here](https://github.com/ajkhattak/NextGenSandboxHub/blob/main/src/R/main.R#L53) 
    
    Either one will install the hydrofabric and several other libraries, and if everything goes well, a basin geopackage will be subsetted and stored under `<input_dir>/<basin_id>/data/gage_<basin_id>.gpkg`

### <ins> Step 4. Forcing Data Download
The workflow uses [CIROH_DL_NextGen](https://github.com/ajkhattak/CIROH_DL_NextGen) forcing_prep tool to donwload atmospheric forcing data. It uses a Python environment (`~/.venv_forcing`) that is created during the workflow setup step (Step 1). To download the forcing data run:
```
   python <path_to_sandboxhub>/sandbox.py -forc
```

====================================================================================
### Note: Steps 5 and 6 require both the ngen and models builds. Please follow the instructions in the [build_models](https://github.com/ajkhattak/NextGenSandboxHub/blob/main/utils/build_models.sh) script to build ngen and models.
====================================================================================

Note: The sandbox workflow assumes that [ngen](https://github.com/NOAA-OWP/ngen) and models including [t-route](https://github.com/NOAA-OWP/t-route) have been built in the Python virtual environment created in Step 1.

### <ins>  Step 5. Generate Configuration and Realization Files
To generate configuratioin and realization files, setup the `formulation` block in the sandbox config file [here](configs/sandbox_config.yaml), and run the following command:
 ```
    python <path_to_sandboxhub>/sandbox.py -conf
 ```

### <ins> Step 6. Run Calibration/Validation Simulations
Setup the `ngen_cal` block in the sandbox config file [here](configs/sandbox_config.yaml), and run the following command, note this depends on all of the above steps:
 ```
    python <path_to_sandboxhub>/sandbox.py -run
 ```

#### Summary
1. Subset divide using hydrofabric
2. Download forcing data
3. Generate configuration files
4. Run Simulations: Using
  ```
    python <path_to_sandboxhub>/sandbox.py option
    OPTIONS = [-subset -forc -conf -run]
  ```
- Option: `-subset` downloads geopackage(s) given a gage ID(s), extracts and locally compute TWI, GIUH, and Nash Cascade parameters; see `divide-attributes` in the gage_<basin_id>.gpkg file
- Option: `-forc` downloads geopackage(s) given a gage ID(s)
- Option: `-conf` generates configuration and realization files for the selected models/basins
- Option: `-run` executes NextGen simulations with and without calibration

Note: These options can be run individually or combined together, for example, `path_to/sandbox.py -subset -conf -run`. The `-subset` is an expensive step, should be run once to get the desired basin geopacakge and associated model parameters.






