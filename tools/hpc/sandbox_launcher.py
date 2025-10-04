import subprocess
import os
import json
import time
import yaml
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import glob

# ===========================  Inputs ==========================================
gage_ids = ["10011500"]#, "09112500"]
models = ["NOM, CFE, T-route", "PET, CFE, T-route"]  # Adjust model list as needed

main_o_dir = Path("/Users/ahmadjankhattak/Core/projects/nwm_bm_sims/nom_pet_cfe_set4")
exp_config_dir = main_o_dir / "exp_configs"
exp_info_dir   = main_o_dir / "exp_info_dir1"

sandbox_config_file = main_o_dir / "sandbox_basefiles" / "sandbox_config_base.yaml"
calib_config_file   = main_o_dir / "sandbox_basefiles" / "calib_config_base.yaml"

use_slurm = False

# ==================================== ==========================================

meta_data = {}

# === Generate config per gage ===
def generate_config_files_for_gage(gage_id, generate=True):
    # === Read base YAML once ===
    with open(sandbox_config_file, "r") as f:
        sandbox_config = yaml.safe_load(f)

    with open(calib_config_file, "r") as f:
        calib_config = yaml.safe_load(f)

    
    sandbox_cfg = sandbox_config.copy()
    
    sandbox_cfg["formulation"]["models"] = models[0]
    sandbox_cfg["simulation"]["gage_ids"] = [gage_id]
    
    os.makedirs(Path(exp_config_dir) / gage_id , exist_ok=True)
    os.makedirs(exp_info_dir, exist_ok=True)
    
    sandbox_cfg_ofile = exp_config_dir / gage_id / f"sandbox_config_{gage_id}.yaml"
    
    with open(sandbox_cfg_ofile, "w") as out_f:
        yaml.dump(sandbox_cfg, out_f, default_flow_style=False,sort_keys=False)
        
    # calib config files
    calib_cfg = calib_config.copy()
    
    calib_cfg_ofile = exp_config_dir / gage_id /f"calib_config_{gage_id}.yaml"
    calib_cfg_ofile_restart = exp_config_dir / gage_id / f"calib_config_{gage_id}_restart.yaml"
    
    # Write to YAML
    with open(calib_cfg_ofile, "w") as out_f:
        yaml.dump(calib_cfg, out_f, default_flow_style=False,sort_keys=False)
        
    # Write to YAML
    calib_cfg['general']['restart'] = True
    with open(calib_cfg_ofile_restart, "w") as out_f:
        yaml.dump(calib_cfg, out_f, default_flow_style=False,sort_keys=False)
        
    meta_data[gage_id] = {
        "sandbox_file" : sandbox_cfg_ofile,
        "calib_file" : calib_cfg_ofile
    }
    

    if generate:
        subprocess.run([
            "python", "sandbox.py",
            "-conf",
            "-i", sandbox_cfg_ofile,
            "-j", calib_cfg_ofile
        ])


def get_max_iter_for_gage(gage_id):
    DEFAULT_MAX_ITER = -1
    
    calib_cfg_file = exp_config_dir / gage_id / f"calib_config_{gage_id}.yaml"

    if calib_cfg_file.exists():
        with open(calib_cfg_file, "r") as f:
            cfg = yaml.safe_load(f)
        return cfg.get("general", {}).get("iterations", DEFAULT_MAX_ITER)
    return DEFAULT_MAX_ITER



# Total wallclock time in seconds (e.g., 8 hours = 28800)
TOTAL_WALLCLOCK = 240 #8 * 60 * 60

# Time before limit to trigger resubmission (e.g., 2 minutes)
BUFFER_TIME = 2 * 60

start_time = time.time()
end_time = start_time + TOTAL_WALLCLOCK - BUFFER_TIME


def get_current_iteration(gage_id):
    info_file = Path(f"{exp_info_dir}/info_{gage_id}.yml")
    
    if not info_file.exists():
        return 0
    
    with open(info_file, 'r') as file:
        d = yaml.safe_load(file)
    
    iter_file = glob.glob(str(Path(d["output_dir"]) / "*_worker" / "best_params.txt"))
    
    if not iter_file:
        print(f"INFO: [{gage_id}] No best_params.txt found — assuming iteration 0")
        return 0

    iter_params = pd.read_csv(iter_file[0], header=None)
    current_iter = int(iter_params.values[0].item()) + 1 # add one as the iteration in the best_params.txt shows the last completed iteration
    
    return current_iter


def run_experiment(gage_id, current_iter, use_slurm=False):
    sb_cfg_file = str(exp_config_dir / gage_id / f"sandbox_config_{gage_id}.yaml")
    calib_cfg_file = str(exp_config_dir / gage_id / f"calib_config_{gage_id}.yaml")
    if current_iter > 0:
        calib_cfg_file = str(exp_config_dir / gage_id / f"calib_config_{gage_id}_restart.yaml")

    if use_slurm:
        cmd = [
            "sbatch",
            "--export=ALL,SANDBOX_FILE=" + sb_cfg_file + ",CALIB_FILE=" + calib_cfg_file,
            "run_gage.slurm"
        ]
        print(f"[{gage_id}] Submitting via SLURM: {' '.join(cmd)}")
        subprocess.run(cmd)
        return None  # No process handle returned when using SLURM
    else:
        cmd = ["python", "sandbox.py", "-run", "-i", sb_cfg_file, "-j", calib_cfg_file]
        print(f"[{gage_id}] Running locally: {' '.join(cmd)}")
        return subprocess.Popen(cmd)
    


def main():

    print(f"\n=== Sandbox Launcher Started @ {datetime.now().strftime('%F %T')} ===")

    running_processes = {}
    incomplete_gages = []
    
    # === Launch jobs for gages below MAX_ITER ===
    for gage_id in gage_ids:
        current_iter = get_current_iteration(gage_id)

        if current_iter == 0:
            print(f"[{gage_id}] First run — generating config files...")
            #global MAX_ITER
            #MAX_ITER = generate_config_files_for_gage(gage_id, generate=True)
            generate_config_files_for_gage(gage_id, generate=True)

            if not exp_info_dir.exists():
                raise ValueError("sandbox_launcher is True, but exp_info_dir does not exist...")

        else:
            print(f"[{gage_id}] Skipping config generation (already started)")

        max_iter = get_max_iter_for_gage(gage_id)
        
        if current_iter < max_iter:
            incomplete_gages.append(gage_id)
            proc = run_experiment(gage_id, current_iter)
            running_processes[gage_id] = proc
        else:
            print(f"[{gage_id}] Already completed ({current_iter}/{max_iter})")

    if not running_processes:
        print("\nAll gages already completed. Nothing to run.")
        return

    if not use_slurm:
        # === Wait for wallclock to expire or jobs to finish ===
        while time.time() < end_time and any(proc.poll() is None for proc in running_processes.values()):
            time.sleep(10)
    
        # === wallclock max time reached? Kill remaining jobs ===
        if time.time() >= end_time:
            print("\n Wallclock limit reached — terminating remaining processes...")
            for gage_id, proc in running_processes.items():
                if proc.poll() is None:
                    print(f"[{gage_id}] Terminating...")
                    #proc.terminate()
                    #time.sleep(5)
                    try:
                        proc.wait(timeout=10)
                        proc.terminate()
                    except subprocess.TimeoutExpired:
                        print(f"[{gage_id}] Didn't terminate in time. Killing...")
                        proc.kill()
                        proc.wait()
            running_processes.clear()
    
    
    # === Check progress and resubmit if needed ===
    still_incomplete = []
    for gage_id in gage_ids:
        final_iter = get_current_iteration(gage_id)
        print(f"[{gage_id}] Iteration: {final_iter}/{max_iter}")
        if final_iter < max_iter:
            still_incomplete.append(gage_id)
    
    if still_incomplete:
        print(f"\nResubmitting sandbox_launcher.py via sbatch for: {still_incomplete}")
        if use_slurm:
            subprocess.run(["sbatch", "submit_launcher.slurm"])
        else:
            # For local testing
            os.execvp("python", ["python", "sandbox_launcher.py"])

    else:
        print("\nAll gages completed maximum iterations. Done.")

    print(f"\n=== Launcher Finished at {datetime.now().strftime('%F %T')} ===")

if __name__ == "__main__":
    main()

