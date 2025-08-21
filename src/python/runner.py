############################################################################################
# Author  : Ahmad Jan Khattak
# Contact : ahmad.jan@noaa.gov
# Date    : July 5, 2024
############################################################################################


import os
import sys
import pandas as pd
import subprocess
import glob
import yaml
import multiprocessing
import platform
import json
from pathlib import Path
from src.python import configuration

class Runner:
    def __init__(self, config_workflow, config_calib):
        self.os_name = platform.system()
        self.config_workflow = config_workflow
        self.config_calib = config_calib
        self.load_configuration()

        #if self.np_per_basin > 1 and not os.path.exists(f"{self.ngen_dir}/cmake_build/partitionGenerator"):
        #    sys.exit("Partitioning geopackage is requested but partitionGenerator does not exist! Quitting...")

    def run(self):

        self.infile = os.path.join(self.output_dir, "basins_passed.csv")
        self.indata = pd.read_csv(self.infile, dtype=str)

        if self.gage_ids:
            self.indata = self.indata[self.indata['gage_id'].isin(self.gage_ids)]
            self.indata.reset_index(drop=True, inplace=True)

        if self.ngen_cal_type not in ['calibration', 'validation', 'calibvalid', 'restart']:
            print("Running NextGen without calibration ...")
            self.run_ngen_without_calibration()
        else:
            print(f'Running NextGen with task_type {self.ngen_cal_type}')

            pool = multiprocessing.Pool(processes=self.basins_in_par)
            tuple_list = list(zip(self.indata["gage_id"], self.indata['num_divides']))
            tuple_list = list(zip(self.indata["gage_id"], self.indata['num_divides']))
            results = pool.map(self.run_ngen_with_calibration, tuple_list)
            pool.close()
            pool.join()


    def load_configuration(self):
        with open(self.config_workflow, 'r') as file:
            self.config = yaml.safe_load(file)

        self.sandbox_dir = self.config["sandbox_dir"]
        self.input_dir = self.config["input_dir"]
        self.output_dir = Path(self.config["output_dir"])

        dformul = self.config['formulation']
        self.ngen_dir = dformul["ngen_dir"]
        self.np_per_basin = int(dformul.get('np_per_basin', 1))
        self.basins_in_par = int(dformul.get('basins_in_par', 1))
        self.np_per_basin_adaptive = int(dformul.get('np_per_basin_adaptive', True))

        dsim = self.config['simulation']
        self.ngen_cal_type = dsim.get('task_type', 'control')
        self.calibration_time = pd.NaT
        self.validation_time = pd.NaT

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

        gage_ids = dsim.get('gage_ids', None)
        gage_ids = gage_ids or []  # Default to empty list [] if None

        # If it's a single string, convert to list
        if isinstance(gage_ids, str):
            self.gage_ids = [gage_ids]
        elif not isinstance(gage_ids, list):
            raise TypeError(f"gage_ids must be a string, list, or None, but got {type(self.gage_ids).__name__}")
        
    def run_ngen_without_calibration(self):
        #infile = os.path.join(self.output_dir, "basins_passed.csv")
        #indata = pd.read_csv(infile, dtype=str)
        ngen_exe = os.path.join(self.ngen_dir, "cmake_build/ngen")

        for id, ncats in zip(indata["gage_id"], indata['num_divides']):
            ncats = int(ncats)
            o_dir = self.output_dir / id
            i_dir = Path(self.input_dir) / id
            os.chdir(o_dir)
            print("cwd: ", os.getcwd())
            print("input_dir: ", i_dir)
            print("output_dir: ", o_dir)

            gpkg_file = Path(glob.glob(str(i_dir / "data" / "*.gpkg"))[0])
            gpkg_name = gpkg_file.stem
            np_per_basin_local = self.np_per_basin
            file_par = ""
            if np_per_basin_local > 1:
                np_per_basin_local, file_par = self.generate_partition_basin_file(ncats, gpkg_file)

            print(f"Running basin {id} on cores {np_per_basin_local} ********", flush=True)
            realization = glob.glob("json/realization_*.json")
            assert len(realization) == 1
            realization = realization[0]

            run_cmd = f'{ngen_exe} {gpkg_file} all {gpkg_file} all {realization}'
            if np_per_basin_local > 1:
                run_cmd = f'mpirun -np {np_per_basin_local} {ngen_exe} {gpkg_file} all {gpkg_file} all {realization} {file_par}'

            if self.os_name == "Darwin":
                run_cmd = f'PYTHONEXECUTABLE=$(which python) {run_cmd}'

            print(f"Run command: {run_cmd}", flush=True)
            result = subprocess.call(run_cmd, shell=True)

    def run_ngen_with_calibration(self, basin):
        id, ncats = basin
        ncats = int(ncats)
        o_dir = self.output_dir / id
        i_dir = Path(self.input_dir) / id
        os.chdir(o_dir)
        print("cwd: ", os.getcwd())
        print("input_dir: ", i_dir)
        print("output_dir: ", o_dir)

        gpkg_file = Path(glob.glob(str(i_dir / "data" / "*.gpkg"))[0])
        gpkg_name = gpkg_file.stem
        np_per_basin_local = self.np_per_basin
        file_par = ""
        if np_per_basin_local > 1:
            np_per_basin_local, file_par = self.generate_partition_basin_file(ncats, gpkg_file)
            file_par = os.path.join(o_dir, file_par)

        print(f"Running basin {id} on cores {np_per_basin_local} ********", flush=True)

        if self.ngen_cal_type in ['calibration', 'calibvalid', 'restart']:
            start_time = pd.Timestamp(self.calibration_time['start_time']).strftime("%Y%m%d%H%M")
            troute_output_file = os.path.join("./troute_output_{}.nc".format(start_time))

            ngen_cal_type_calib_restart = 'calibration'
            if (self.ngen_cal_type == 'restart'):
                ngen_cal_type_calib_restart = 'restart'

            restart_dir = self.restart_dir.replace("{*}", id)

            ConfigGen = configuration.ConfigurationCalib(gpkg_file = gpkg_file,
                                                        output_dir = o_dir,
                                                        ngen_dir = self.ngen_dir,
                                                        realization_file_par = file_par,
                                                        troute_output_file = troute_output_file,
                                                        ngen_cal_type=ngen_cal_type_calib_restart,
                                                        simulation_time=self.calibration_time,
                                                        evaluation_time=self.calib_eval_time,
                                                        ngen_cal_basefile=self.config_calib,
                                                        restart_dir=restart_dir,
                                                        num_proc=np_per_basin_local)
            
            ConfigGen.write_calib_input_files()
            
            
            run_command = "python -m ngen.cal configs/ngen-cal_calib_config.yaml"
            result = subprocess.call(run_command, shell=True)

        if self.ngen_cal_type in ['validation', 'calibvalid']:

            start_time = pd.Timestamp(self.validation_time['start_time']).strftime("%Y%m%d%H%M")
            troute_output_file = os.path.join("./troute_output_{}.nc".format(start_time))
            ConfigGen = configuration.ConfigurationCalib(gpkg_file = gpkg_file,
                                                        output_dir = o_dir,
                                                        ngen_dir = self.ngen_dir,
                                                        realization_file_par = file_par,
                                                        troute_output_file = troute_output_file,
                                                        ngen_cal_type='validation',
                                                        simulation_time=self.validation_time,
                                                        evaluation_time=self.valid_eval_time,
                                                        ngen_cal_basefile=self.config_calib,
                                                        restart_dir=self.restart_dir,
                                                        num_proc=np_per_basin_local)
            
            ConfigGen.write_calib_input_files()
            run_command = f"python {self.sandbox_dir}/src/python/validation.py configs/ngen-cal_valid_config.yaml"
            result = subprocess.call(run_command, shell=True)

    

    def generate_partition_basin_file(self, ncats, gpkg_file):
        np_per_basin_local = self.np_per_basin
        #json_dir = "json"

        if ncats <= np_per_basin_local:
            np_per_basin_local = ncats
        elif self.np_per_basin_adaptive:
            np_per_basin_local = min(int(ncats / np_per_basin_local), 20)

        fpar = " "
        if np_per_basin_local > 1:
            #fpar = os.path.join(json_dir, f"partitions_{np_per_basin_local}.json")
            #partition = f"{self.ngen_dir}/cmake_build/partitionGenerator {gpkg_file} {gpkg_file} {fpar} {np_per_basin_local} \"\" \"\" "
            fpar = os.path.join("configs", f"partitions_{np_per_basin_local}.json")
            partitions = f"python {self.sandbox_dir}/utils/python/local_only_partitions.py {gpkg_file} {np_per_basin_local} {os.getcwd()}/configs"
            print ("PP ", partitions)
            result = subprocess.call(partitions, shell=True)

        return np_per_basin_local, fpar

