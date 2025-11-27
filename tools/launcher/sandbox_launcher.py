import subprocess
import os, sys
import json
import time
import yaml
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import glob
import numpy as np
import geopandas as gpd
import yaml
import argparse

# ===========================  Inputs ==========================================

sandbox_config_file = "/scratch4/NCEPDEV/ohd/Ahmad.Jan.Khattak/Core/projects/nwm_v4_bm/launcher/basefiles/sandbox_config_base.yaml"
calib_config_file   = "/scratch4/NCEPDEV/ohd/Ahmad.Jan.Khattak/Core/projects/nwm_v4_bm/launcher/basefiles/calib_config_base.yaml"
map_config_file     = "/scratch4/NCEPDEV/ohd/Ahmad.Jan.Khattak/Core/projects/nwm_v4_bm/launcher/models_gages_map.yaml"

use_slurm = True

# ==============================================================================
# Load configuration files
# ==============================================================================
with open(sandbox_config_file, "r") as f:
    base_sandbox_cfg = yaml.safe_load(f)

output_dir = Path(base_sandbox_cfg["general"]["output_dir"])
input_dir  = Path(base_sandbox_cfg["general"]["input_dir"])


with open(map_config_file) as f:
    map_cfg = yaml.safe_load(f)

formulations = map_cfg["formulations"]
mapping      = map_cfg["mapping"]


# ====================== Moels & Gages Mapper  ======================

def get_models_for_gage(gage_id):
    """
    Return all models for a given gage as a flat list.
    """
    gage_formulations = mapping[gage_id]
    models = []
    for fg in gage_formulations:
        models.extend(formulations[fg])

    return models


def model_name_to_dir(model_name):
    """
    Convert model string to a safe directory name (remove T-route, commas, etc.).
    """
    name = model_name.replace("T-route", "")
    name = name.replace(",", "")
    name = name.strip()
    name = name.replace(" ", "_")
    return name.lower()

# ==================================== ==========================================

# === Generate config per gage ===
def generate_config_files_for_gage(model_name, model_dir, gage_id, exp_config_dir, exp_info_dir):
    """Create sandbox + calibration configs for a single model + single gage."""

    # === Read base YAML once ===
    with open(sandbox_config_file, "r") as f:
        sandbox_config = yaml.safe_load(f)

    with open(calib_config_file, "r") as f:
        calib_config = yaml.safe_load(f)

    sandbox_cfg = sandbox_config.copy()

    # --- Determine CPU count based on number of divides ---
    gpkg_path = glob.glob(str(input_dir / f"{gage_id}/data/*.gpkg"))
    div       = gpd.read_file(gpkg_path[0], layer='divides')
    num_cpus  = int(np.ceil(len(div) / 20))

    sandbox_cfg["general"]["output_dir"]    = str(output_dir / model_dir)
    sandbox_cfg["formulation"]["num_procs"] = num_cpus
    sandbox_cfg["formulation"]["models"]    = model_name
    sandbox_cfg["simulation"]["gage_ids"]   = [gage_id]

    # Create directories
    (exp_config_dir / gage_id).mkdir(parents=True, exist_ok=True)
    exp_info_dir.mkdir(parents=True, exist_ok=True)

    sandbox_main  = exp_config_dir / gage_id / f"sandbox_config_{gage_id}.yaml"
    sandbox_val   = exp_config_dir / gage_id / f"sandbox_config_{gage_id}_validation.yaml"
    calib_main    = exp_config_dir / gage_id / f"calib_config_{gage_id}.yaml"
    calib_restart = exp_config_dir / gage_id / f"calib_config_{gage_id}_restart.yaml"

    # Write sandbox main
    with open(sandbox_main, "w") as f:
        yaml.dump(sandbox_cfg, f, default_flow_style=False, sort_keys=False)

    # Write sandbox validation
    sandbox_val_cfg = sandbox_cfg.copy()
    sandbox_val_cfg["simulation"]["task_type"] = "validation"
    with open(sandbox_val, "w") as f:
        yaml.dump(sandbox_val_cfg, f, default_flow_style=False, sort_keys=False)

    # Write calib main
    with open(calib_main, "w") as f:
        yaml.dump(calib_config, f, default_flow_style=False, sort_keys=False)

    # Write calib restart
    calib_restart_cfg = calib_config.copy()
    calib_restart_cfg["general"]["restart"] = True
    with open(calib_restart, "w") as f:
        yaml.dump(calib_restart_cfg, f, default_flow_style=False, sort_keys=False)

    # Run sandbox -conf to generate exp_info.yml
    subprocess.run(["sandbox", "-conf", "-i", sandbox_main, "-j", calib_main])


def get_max_iter(exp_config_dir, gage_id):
    """
    Read the calibration config to determine the total number of iterations.
    """
    f = exp_config_dir / gage_id / f"calib_config_{gage_id}.yaml"

    if not f.exists():
        return 0

    with open(f, "r") as fp:
        cfg = yaml.safe_load(fp)

    return cfg["general"]["iterations"]


def get_current_iteration(exp_info_dir, gage_id, status=False):

    info_file = exp_info_dir / f"info_{gage_id}.yml"

    if not info_file.exists():
        return 0

    with open(info_file, 'r') as file:
        d = yaml.safe_load(file)

    iter_file = glob.glob(str(Path(d["output_dir"]) / "*_worker" / "best_params.txt"))
    
    if not iter_file:
        if not status:
            print(f"INFO: [{gage_id}] No best_params.txt found — assuming iteration 0")
        return 0

    iter_params = pd.read_csv(iter_file[0], header=None)
    current_iter = int(iter_params.values[0].item()) #+ 1 # add one as the iteration in the best_params.txt shows the last completed iteration

    return current_iter


def get_num_cpus(exp_info_dir, gage_id):
    """
    Extract num_cpus from the info file generated during sandbox -conf.
    """
    info_file = exp_info_dir / f"info_{gage_id}.yml"

    if not info_file.exists():
        return 1
    
    with open(info_file, "r") as file:
        d = yaml.safe_load(file)

    return int(d["num_cpus"])


def check_validation_exists(exp_info_dir, gage_id, status=False):
    """
    Return True if validation output already exists for this gage.
    """

    info_file = exp_info_dir / f"info_{gage_id}.yml"

    if not info_file.exists():
        return False  # Validation doesn't exist

    with open(info_file, "r") as f:
        d = yaml.safe_load(f)

    # Validation output lives in output_sim_obs/
    validation_file = glob.glob(
        str(Path(d["output_dir"]) / "*_worker" / "output_sim_obs" / "sim_obs_validation.csv")
    )

    if validation_file:
        if not status:
            print(f"INFO: [{gage_id}] Validation output found — skipping validation run.")
        return True
    
    return False

# ====================== SLURM Submission ======================

def run_experiment(model_name, model_dir, gage_id, exp_config_dir, exp_info_dir, current_iter):
    """
    Submit the calibration/validation or restart job.
    """

    sandbox_main = exp_config_dir / gage_id / f"sandbox_config_{gage_id}.yaml"
    sandbox_val  = exp_config_dir / gage_id / f"sandbox_config_{gage_id}_validation.yaml"

    calib_main    = exp_config_dir / gage_id / f"calib_config_{gage_id}.yaml"
    calib_restart = exp_config_dir / gage_id / f"calib_config_{gage_id}_restart.yaml"

    calib_file = calib_main if current_iter == 0 else calib_restart

    max_iter    = get_max_iter(exp_config_dir, gage_id)
    sb_cfg_file = str(sandbox_main) if current_iter < max_iter else str(sandbox_val)

    num_cpus = get_num_cpus(exp_info_dir, gage_id)
    job_name = f"{model_dir}_{gage_id}"

    cmd = [
        "sbatch",
        f"--cpus-per-task={num_cpus}",
        f"--ntasks-per-node={num_cpus}",
        f"--job-name={job_name}",
        "--export=ALL,"
        f"SANDBOX_FILE={sb_cfg_file},"
        f"CALIB_FILE={calib_file}",
        "launcher/submit_gage.slurm"
    ]

    # # Skip submission if validation exists — job is fully complete
    validation_exists = check_validation_exists(exp_info_dir, gage_id)
    
    if validation_exists:
        return

    print(f"[{gage_id}] Submitting: {' '.join(cmd)}")
    subprocess.run(cmd)


# ====================== Check Experiments Status ======================
def check_status():
    """
    Print calibration/validation runs status for all gages and all models.
    """

    print("\n============================ STATUS REPORT ==============================")
    # Table header
    header = f"{'Gage':<12} {'Formulation':<30} {'Calib (cur/max)':<18} {'Validation':<4}"
    print(header)
    print("-" * len(header))
    for gage_id in mapping.keys():
        models_for_gage = get_models_for_gage(gage_id)

        for model_name in models_for_gage:
            model_dir      = model_name_to_dir(model_name)
            exp_info_dir   = output_dir / model_dir / base_sandbox_cfg["sandbox_launcher"]["exp_info_dir"]
            exp_config_dir = output_dir / model_dir / "configs"

            current_iter = get_current_iteration(exp_info_dir, gage_id, status=True)
            max_iter     = get_max_iter(exp_config_dir, gage_id)

            validation_exists = check_validation_exists(exp_info_dir, gage_id, status=True)
            valid_flag = "YES" if validation_exists else "NO"
            print(f"{gage_id:<12} {model_name:<30} {f'{current_iter}/{max_iter}':<18} {valid_flag:<4}")

    print("-" * len(header))
    print("======================== STATUS REPORT COMPLETE ==========================")


# ==============================================================================
# Main function loops over all models x all gages
# ==============================================================================
def runner():
    
    running_processes = {}

    for gage_id in mapping.keys():

        print(f"--------------------------------")
        print(f"###  Processing Gage: {gage_id}")

        models_for_gage = get_models_for_gage(gage_id)

        for m_idx, model_name in enumerate(models_for_gage):

            print(f"\n--- Model {m_idx+1}/{len(models_for_gage)} | {model_name} ---")
            
            model_dir = model_name_to_dir(model_name)
    
            exp_info_dir   = output_dir / model_dir / base_sandbox_cfg["sandbox_launcher"]["exp_info_dir"]
            exp_config_dir = output_dir / model_dir / "configs"

            current_iter = get_current_iteration(exp_info_dir, gage_id)
            max_iter     = get_max_iter(exp_config_dir, gage_id)

            if current_iter == 0:
                print(f"[{gage_id}] First time setup — generating configs...")
                generate_config_files_for_gage(model_name, model_dir, gage_id, exp_config_dir, exp_info_dir)


            if current_iter <= max_iter:
                run_experiment(model_name, model_dir, gage_id, exp_config_dir, exp_info_dir, current_iter)
            else:
                print(f"[{gage_id}] Completed iterations ({current_iter}/{max_iter})")

        print(f"\n--- Finished Model: {model_name} ---\n")

    print("\n=== Launcher Finished ===\n")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-status",
                        action="store_true",
                        help="Print calibration/validation status for all gages and models without submitting jobs."
                        )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    print(f"\n=== Sandbox Launcher Started @ {datetime.now()} ===")

    # STATUS MODE
    if args.status:
        check_status()
        sys.exit(0)


    # ---------------------------------------
    # NORMAL EXECUTION MODE
    # ---------------------------------------
    runner()

