############################################################################################
# Author  : Ahmad Jan Khattak
# Contact : ahmad.jan.khattak@noaa.gov
# Date    : July 5, 2024
############################################################################################

import os
import sys
import pandas as pd
import subprocess
import glob
import yaml
import platform
import json
from pathlib import Path
import shutil
from src.python import configuration

class Runner:
    def __init__(self, sandbox_dir, config_workflow, config_calib
                 ):
        self.os_name         = platform.system()
        self.sandbox_dir     = Path(sandbox_dir)
        self.config_workflow = config_workflow
        self.config_calib    = config_calib

        self.load_configuration()

        #if self.np_per_basin > 1 and not os.path.exists(f"{self.ngen_dir}/cmake_build/partitionGenerator"):
        #    sys.exit("Partitioning geopackage is requested but partitionGenerator does not exist! Quitting...")

        # Check whether `mpirun` exists on the system; if exists, then it assumes that ngen was built with MPI=ON
        self.mpirun_exists = shutil.which("mpirun") is not None


    def load_configuration(self):
        with open(self.config_workflow, 'r') as file:
            self.config = yaml.safe_load(file)

        self.input_dir    = self.config['general'].get('input_dir')
        self.output_dir   = Path(self.config['general'].get('output_dir'))

        dformul = self.config['formulation']
        self.ngen_dir     = Path(os.environ.get("NGEN_DIR"))
        self.formulation  = dformul['models'].upper()
        self.num_procs    = int(dformul.get('num_procs', 1))

        dsim = self.config['simulation']
        self.ngen_cal_type    = dsim.get('task_type', 'control')
        self.calibration_time = pd.NaT
        self.validation_time  = pd.NaT

        if self.ngen_cal_type in ['calibration', 'calibvalid', 'restart']:
            if "calibration_time" not in dsim or not isinstance(dsim["calibration_time"], dict):
                raise ValueError("calibration_time is not provided or is not a valid dictionary.")

            if "calib_eval_time" not in dsim or not isinstance(dsim["calib_eval_time"], dict):
                raise ValueError("calib_eval_time is not provided or is not a valid dictionary.")

            self.calibration_time = dsim["calibration_time"]
            self.calib_eval_time  = dsim["calib_eval_time"]

        if self.ngen_cal_type in ['validation', 'calibvalid']:
            if "calibration_time" not in dsim or not isinstance(dsim["calibration_time"], dict):
                raise ValueError("calibration_time is not provided or is not a valid dictionary.")

            if "calib_eval_time" not in dsim or not isinstance(dsim["calib_eval_time"], dict):
                raise ValueError("calib_eval_time is not provided or is not a valid dictionary.")
            
            self.validation_time = dsim["validation_time"]
            self.valid_eval_time = dsim["valid_eval_time"]

        self.restart_dir = "./"
        if self.ngen_cal_type == 'restart':
            self.restart_dir = dsim.get('restart_dir')
            if self.restart_dir is None:
                raise ValueError("ngen_cal_type is restart, however, restart_dir is None. It must be set to a valid directory.")
            if not self.restart_dir:
                raise FileNotFoundError(f"restart_dir does not exist, provided {self.restart_dir}.")

        # Get gages IDs
        self.gage_ids, self.num_divides = self.load_gage_ids(dsim.get("gage_ids_input"))

        self.sim_name_suffix = dsim.get('sim_name_suffix') or None

        densemble = dsim.get('ensemble') or None

        if (densemble):
            self.ensemble_enabled = bool(densemble.get('enabled'))
            self.ensemble_size    = int(densemble.get('members') or 1)
            self.ensemble_models  = densemble.get('models')
            if self.ensemble_enabled:
                assert self.ensemble_size > 1, (
                    "Ensemble size must be greater than 1 when ensemble is enabled"
                )
            else:
                self.ensemble_size    = 1
                self.ensemble_models  = []
        else:
            self.ensemble_enabled = False
            self.ensemble_size    = 1
            self.ensemble_models  = []

    def load_gage_ids(self, gage_ids_input):
        num_cats = -99
        if gage_ids_input is None:
            raise TypeError("gage_ids_input must be a CSV path, a string ID, or a list of IDs")

        # Case 1: CSV file path
        if isinstance(gage_ids_input, str) and gage_ids_input.lower().endswith(".csv"):
            path = Path(gage_ids_input)

            if not path.is_file():
                raise FileNotFoundError(f"gage_ids file not found: {path}")

            df = pd.read_csv(path, dtype=str)

            if 'gage_id' not in df.columns:
                raise ValueError("CSV must contain a 'gage_id' column")

            return df['gage_id'].tolist(), df['num_divides'].tolist()

        # Case 2: single gage ID as string
        if isinstance(gage_ids_input, str):
            return [gage_ids_input], [num_cats]

        # Case 3: list / tuple / set
        if isinstance(gage_ids_input, (list, tuple, set)):
            return [str(x) for x in gage_ids_input], [num_cats for x in gage_ids_input]

        raise TypeError("gage_ids_input must be a CSV path, a string ID, or a list of IDs")

    def run(self):

        if "LSTM" in self.formulation:
            print("Running LSTM in NextGen ...")
            self.run_ngen_without_calibration()
        elif self.ngen_cal_type not in ['calibration', 'validation', 'calibvalid', 'restart']:
            print("Running NextGen without calibration ...")
            self.run_ngen_without_calibration()
        else:
            print(f'Running NextGen with task_type {self.ngen_cal_type}')

            for tp in zip(self.gage_ids, self.num_divides):
                self.run_ngen_with_calibration(tp)


    def run_ngen_without_calibration(self):
        ngen_exe = os.path.join(self.ngen_dir, "cmake_build/ngen")


        for id, ncats in zip(self.gage_ids, self.num_divides):
            
            ncats = int(ncats)
            o_dir = self.output_dir / id
            if self.sim_name_suffix:
                o_dir = self.output_dir / f"{id}_{self.sim_name_suffix}"

            i_dir = Path(self.input_dir) / id
            os.chdir(o_dir)
            print("cwd: ", os.getcwd())
            print("input_dir: ", i_dir)
            print("output_dir: ", o_dir)

            gpkg_file = Path(glob.glob(str(i_dir / "data" / "*.gpkg"))[0])
            gpkg_name = gpkg_file.stem

            print(f"Running basin {id} on cores {self.num_procs} ********", flush=True)
            realization = glob.glob(str( o_dir / "configs" / "realization_*.json"))

            assert len(realization) == 1
            realization = realization[0]

            # defaults to serial run no-mpi mode
            run_cmd = f'{ngen_exe} {gpkg_file} all {gpkg_file} all {realization}'

            if self.mpirun_exists:
                # mpirun exists so run with MPI

                if self.num_procs > 1:
                    file_par = self.generate_partition_basin_file(ncats, gpkg_file)
                    file_par = os.path.join(o_dir, file_par)
                    run_cmd  = (
                        f"mpirun -np {self.num_procs} "
                        f"{ngen_exe} {gpkg_file} all {gpkg_file} all {realization} {file_par}"
                        )
                else:
                    # single-process MPI mode
                    run_cmd = (
                        f"mpirun -np 1 "
                        f"{ngen_exe} {gpkg_file} all {gpkg_file} all {realization}"
                        )


            if self.os_name == "Darwin":
                run_cmd = f'PYTHONEXECUTABLE=$(which python) {run_cmd}'

            print(f"Run command: {run_cmd}", flush=True)
            result = subprocess.call(run_cmd, shell=True)

    def run_ngen_with_calibration(self, basin):
        id, ncats = basin
        ncats = int(ncats)
        o_dir = self.output_dir / id

        if self.sim_name_suffix:
            o_dir = self.output_dir / f"{id}_{self.sim_name_suffix}"

        i_dir = Path(self.input_dir) / id
        os.chdir(o_dir)
        print("cwd: ", os.getcwd())
        print("input_dir: ", i_dir)
        print("output_dir: ", o_dir)

        gpkg_file = Path(glob.glob(str(i_dir / "data" / "*.gpkg"))[0])
        gpkg_name = gpkg_file.stem

        file_par = ""
        if self.num_procs > 1:
            file_par = self.generate_partition_basin_file(ncats, gpkg_file)
            file_par = os.path.join(o_dir, file_par)

        print(f"Running basin {id} on cores {self.num_procs} ********", flush=True)

        if self.ngen_cal_type in ['calibration', 'calibvalid', 'restart']:
            start_time = pd.Timestamp(self.calibration_time['start_time']).strftime("%Y%m%d%H%M")
            troute_output_file = os.path.join("./troute_output_{}.nc".format(start_time))

            ngen_cal_type_calib_restart = 'calibration'
            if (self.ngen_cal_type == 'restart'):
                ngen_cal_type_calib_restart = 'restart'

            restart_dir = self.restart_dir.replace("{*}", id)

            ConfigGen = configuration.ConfigurationCalib(
                gpkg_file            = gpkg_file,
                output_dir           = o_dir,
                ngen_dir             = self.ngen_dir,
                sandbox_dir          = self.sandbox_dir,
                realization_file_par = file_par,
                troute_output_file   = troute_output_file,
                ngen_cal_type        = ngen_cal_type_calib_restart,
                formulation          = self.formulation,
                simulation_time      = self.calibration_time,
                evaluation_time      = self.calib_eval_time,
                ngen_cal_basefile    = self.config_calib,
                restart_dir          = restart_dir,
                num_proc             = self.num_procs,
                ensemble_enabled     = self.ensemble_enabled,
                ensemble_size        = self.ensemble_size,
                ensemble_models      = self.ensemble_models
            )
            
            ConfigGen.write_calib_input_files()

            run_command = "python -m ngen.cal configs/ngen-cal_calib_config.yaml"
            result = subprocess.call(run_command, shell=True)

        if self.ngen_cal_type in ['validation', 'calibvalid']:

            start_time = pd.Timestamp(self.validation_time['start_time']).strftime("%Y%m%d%H%M")
            troute_output_file = os.path.join("./troute_output_{}.nc".format(start_time))

            ConfigGen = configuration.ConfigurationCalib(
                gpkg_file            = gpkg_file,
                output_dir           = o_dir,
                ngen_dir             = self.ngen_dir,
                sandbox_dir          = self.sandbox_dir,
                realization_file_par = file_par,
                troute_output_file   = troute_output_file,
                ngen_cal_type        = 'validation',
                formulation          = self.formulation,
                simulation_time      = self.validation_time,
                evaluation_time      = self.valid_eval_time,
                ngen_cal_basefile    = self.config_calib,
                restart_dir          = self.restart_dir,
                num_proc             = self.num_procs,
                ensemble_enabled     = self.ensemble_enabled,
                ensemble_size        = self.ensemble_size,
                ensemble_models      = self.ensemble_models
            )
            
            ConfigGen.write_calib_input_files()

            run_command = f"python {self.sandbox_dir}/src/python/validation.py -config configs/ngen-cal_valid_config.yaml"

            if self.ensemble_enabled:
                run_command = (
                    f"python {self.sandbox_dir}/src/python/validation.py "
                    f"-config configs/ngen-cal_valid_config.yaml "
                    f"-routing configs/troute_config.yaml"
                )

            result = subprocess.call(run_command, shell=True)

    

    def generate_partition_basin_file(self, ncats, gpkg_file):

        fpar = " "
        if self.num_procs > 1:
            #fpar = os.path.join(json_dir, f"partitions_{num_procs_local}.json")
            #partition = f"{self.ngen_dir}/cmake_build/partitionGenerator {gpkg_file} {gpkg_file} {fpar} {num_procs_local} \"\" \"\" "
            fpar = os.path.join("configs", f"partitions_{self.num_procs}.json")
            partitions = f"python {self.sandbox_dir}/utils/python/local_only_partitions.py {gpkg_file} {self.num_procs} {os.getcwd()}/configs"
            result = subprocess.call(partitions, shell=True)

        return fpar

