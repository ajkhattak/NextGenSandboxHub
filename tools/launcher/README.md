## Sandbox Launcher for Running Large-Scale Experiments on HPC

Running large-scale NextGen experiments often involves 100s of gages, multiple hydrologic formulations, and long-running calibration cycles that must restart automatically 
due to HPC wallclock limits. The Sandbox Launcher provides a fully automated workflow for managing these experiments on high-performance computing (HPC) systems.

The launcher:

- Automatically generates per-gage and per-model configuration files
- Submits each gage–model experiment to SLURM
- Detects completed calibration iterations and resumes incomplete ones
- Organizes outputs into consistent, model-specific directory structures
- Supports flexible model–gage mapping through a YAML configuration file
- Handles validation runs with no additional user intervention
- Ensures reproducibility and reduces manual HPC job management

With a single command, the Sandbox Launcher orchestrates hundreds of experiments, making large-scale calibration and validation workflows efficient, automated, and repeatable.

## Setup
Before starting, it is recommended to copy the entire launcher directory to your desired working location. The path to this directory (<path_to_launcher>) will be referenced in sandbox_launcher.py (see below).
- **Prepare the model–gage mapping file** \
  Create a YAML configuration file that maps models to gages (i.e., which model(s) runs at which location(s)). You can use the following as a template: [models_gages_map.yaml](https://github.com/ajkhattak/NextGenSandboxHub/blob/main/tools/launcher/models_gages_map.yaml)
- **Update base configuration files** \
  Modify the base configuration files located in the launcher directory:
   - launcher/basefiles/sandbox_config_base.yaml
   - launcher/basefiles/calib_config_base.yaml
- **Update SLURM scripts** \
  Adapt the SLURM submission scripts to your system:
   - [submit_gage.slurm](https://github.com/ajkhattak/NextGenSandboxHub/blob/main/tools/launcher/submit_gage.slurm)
   - [submit_launcher.slurm](https://github.com/ajkhattak/NextGenSandboxHub/blob/main/tools/launcher/submit_launcher.slurm)
- **Update paths inside sandbox_launcher.py** \
  Set the following variables to point to your copied launcher directory:
  ```
  sandbox_config_file = "<path_to_launcher>/launcher/basefiles/sandbox_config_base.yaml"
  calib_config_file   = "<path_to_launcher>/launcher/basefiles/calib_config_base.yaml"
  map_config_file     = "<path_to_launcher>/launcher/models_gages_map.yaml"
  ```
## Run
Submit the launcher job with:
```
sbatch launcher/submit_launcher.slurm
```

>*NOTE*: The launcher assumes that all required basin geopackages and forcing data have already been downloaded.
