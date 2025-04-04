# Workflow for Setting Up NextGen Simulations from Scratch to Evaluation

This workflow outlines the steps for setting up a NextGen simulation, including the downloading of required data (hydrofabric, forcing data, etc.), configuration file generation, running calibration, and validation processes. The workflow covers:

- Downloads geopackage(s) for the desired locations given USGS gage ID(s) using [hydrofabric](https://github.com/NOAA-OWP/hydrofabric) subsetter.
- Downloads AORC forcing data using [foricing_prep](https://github.com/ajkhattak/CIROH_DL_NextGen) tool
- Generates model configuration files and ngen realization file using local scripts. In the future, ngen_cal_gen from [ngen-cal](https://github.com/NOAA-OWP/ngen-cal) will be used for generating configuration files.
- Calibration: Performs model calibration (single or multi-model) using [ngen-cal](https://github.com/NOAA-OWP/ngen-cal)
- Validation: Performs model validation using [ngen-cal](https://github.com/NOAA-OWP/ngen-cal)
- Evaluation: Simuated and observed data are stored for model evaluation, along with several key performance metrics.

## Installation

Detailed instructions on how to install, configure, and get the project running.
This should be frequently tested to ensure reliability. Alternatively, link to
a separate [INSTALL](INSTALL.md) document.


### Configuration steps
  - `git clone https://github.com/ajkhattak/basin_workflow && cd basin_workflow`
  - `git submodule update --init`
  - `pip install 'extern/ngen-cal/python/ngen_cal[netcdf]'`
  - `pip install -e ./extern/ngen_cal_plugins`
    
#### Forcing data downloaders
  - Currently supports Nels and Jonathan tools available [here](https://github.com/ajkhattak/CIROH_DL_NextGen)
  - `mkdir ~/.venv_forcing` (preferably in your home directory and don't change the name of the env othewise it needs to be explicitly provided in the config file)
  - `python -m venv ~/.venv_forcing`
  - `source ~/.venv_forcing/bin/activate`
  - `pip install -r extern/CIROH_DL_NextGen/forcing_prep/requirements.txt`

### Setup configuration files
The workflow needs two configuration files, provided [here](https://github.com/ajkhattak/basin_workflow/tree/tnc-dangermond/configs/). Workflow setup and model options and paths need to be adjusted to local settings. Please see the configuration files for further details.

### Running the workflow
```
python <path_to_basin_workflow>/main.py OPTIONS = [-gpkg -forc -conf -run]
```
Note: These options can be run individually or all together by `path_to/main.py -gpkg -conf -run`. The `-gpkg` is an expensive step, should be run once to get the desired basin geopacakge.

- Option: `-gpkg` downloads geopackage(s) given a gage ID(s), computes TWI, GIUH, and Nash parameters, and append them to the geopackage along with other model parameters (from S3 bucket) as `model-attributes`
- Option: `-conf` generates configuration files for the selected models/basins
- Option: `-run` runs NextGen simulations with and without calibration. The workflow uses [ngen-cal](https://github.com/NOAA-OWP/ngen-cal) for calibration


####################################################################
### Instructions for computing Geomorphological Instantaneous Unit Hydrograph (GIUH) and Topographic Wetness Index (TWI)
This set of scripts offers a workflow for establishing basin-scale simulations from the ground up 
and executing them within the NextGen framework.

- R-based scripts, leveraging the [WhiteBox](https://www.whiteboxgeo.com/manual/wbw-user-manual/book/tool_help.html) tool, a geospatial data analysis software,
  are provided for the computation of GIUH and TWI.
  
- Python-based scripts are provided for generating model(s) (standalone and coupled) configuration files and the
  NextGen realization file.


