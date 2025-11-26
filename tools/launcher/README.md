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

