############################################################################################
# Author  : Ahmad Jan Khattak
# Contact : ahmad.jan@noaa.gov
# Date    : October 11, 2023 
############################################################################################


import os
import sys
import subprocess
import pandas as pd
import glob
import shutil
import re
import geopandas as gpd
import csv
import yaml
import multiprocessing
from functools import partial
import time
import argparse
import json
from pathlib import Path

from src.python import helper
from src.python import generate

class Driver:
    def __init__(self, infile):
        self.colors = helper.colors()

        self.config_workflow = infile
        with open(infile, 'r') as file:
            d = yaml.safe_load(file)

        self.workflow_dir = d["workflow_dir"]
        self.input_dir = d["input_dir"]
        self.output_dir = Path(d["output_dir"])
        
        dformul = d['formulation']
        self.ngen_dir = dformul["ngen_dir"]
        self.formulation = dformul['models']
        self.surface_runoff_scheme = dformul['surface_runoff_scheme']
        self.clean = self.process_clean_input_param(dformul.get('clean', "none"))
        self.verbosity = dformul.get('verbosity', 0)
        self.basins_in_par = dformul.get('basins_in_par', 1)
        self.setup_simulation = dformul.get('setup_simulation', True)
        self.rename_existing_simulation = dformul.get('rename_existing_simulation', "")
        self.schema_type = dformul.get('schema_type', "noaa-owp")

        dforcing = d['forcings']
        self.forcing_dir = dforcing.get("forcing_dir", "None")
        self.forcing_format = dforcing.get('forcing_format', '.nc')

        self.is_netcdf_forcing = True
        if self.forcing_format == '.csv':
            self.is_netcdf_forcing = False

        dsim = d['simulation']
        self.ngen_cal_type = dsim.get('task_type', None)
        
        if self.ngen_cal_type == 'calibration' or self.ngen_cal_type == 'calibvalid':
            self.simulation_time = dsim["calibration_time"]
            self.calib_eval_time = dsim["calib_eval_time"]

        elif self.ngen_cal_type == 'validation':
            self.simulation_time = dsim["validation_time"]
            self.valid_eval_time = dsim["valid_eval_time"]
    
    def process_clean_input_param(self, clean):
        clean_lst = []
        if isinstance(clean, str):
            clean_lst = [clean]
        elif isinstance(clean, list):
            clean_lst.extend(clean)
        return clean_lst

    def get_forcing_files(self, gpkg_dirs, is_corrected=True):
        forcing_files = []

        if self.forcing_format == ".nc":
            if "{*}" in self.forcing_dir:
                for g in gpkg_dirs:
                    forcing_dir_local = self.forcing_dir
                    fdir = Path(forcing_dir_local.replace("{*}", Path(g).name))

                    if not fdir.exists() or not fdir.is_dir():
                        raise ValueError("Forcing directory '{fdir}' does not exist.")
                    if is_corrected:
                        forcing_file = glob.glob(f"{fdir}/*_corrected.nc")[0]
                    else:
                        nc_file = glob.glob(f"{fdir}/*.nc")
                        forcing_file = [f for f in nc_file if not "_corrected" in f][0]

                    forcing_files.append(forcing_file)
            else:
                if not Path(self.forcing_dir).exists():
                    raise ValueError("Forcing directory '{self.forcing_dir}' does not exist.")

                if not Path(self.forcing_dir).is_dir():
                    forcing_file = self.forcing_dir
                else:
                    if is_corrected:
                        forcing_file = glob.glob(f"{self.forcing_dir}/*_corrected.nc")[0]
                    else:
                        nc_file = glob.glob(f"{fdir}/*.nc")
                        forcing_file = [f for f in nc_file if not "_corrected" in f][0]

                forcing_files.append(forcing_file)
        else:
            if "{*}" in self.forcing_dir:
                for g in gpkg_dirs:
                    forcing_dir_local = self.forcing_dir
                    fdir = Path(forcing_dir_local.replace("{*}", Path(g).name))

                    if not fdir.exists():
                        raise ValueError("Forcing directory '{fdir}' does not exist.")
                    if not fdir.is_dir():
                        raise ValueError("forcing format is .csv, so '{fdir}' should point to a directory and not file.")

                    forcing_files.append(fdir)

        return forcing_files

    def generate_catchment_files(self, dirs):
        i_dir = dirs[0]
        o_dir = dirs[1]
        f_dir = dirs[2]
        print ("gen_ ", dirs)
        o_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(o_dir)

        basin_ids = []
        num_cats = []

        if self.verbosity >= 2:
            print("***********************************")
            print("cwd: ", os.getcwd())
            print("input_dir: ", i_dir)
            print("output_dir: ", o_dir)
            print("forcing_dir: ", f_dir)

        gpkg_name = Path(glob.glob(str(i_dir / "data" / "*.gpkg"))[0]).name
        gpkg_dir = Path(glob.glob(str(i_dir / "data" / "*.gpkg"))[0])
        gpkg_id = i_dir.name

        filled_dot = '●'

        if self.verbosity >= 1:
            print(filled_dot, gpkg_name, end="")

        gpkg_dir = os.path.join(i_dir, gpkg_dir)
        #config_dir = os.path.join(o_dir, "configs")
        #json_dir = os.path.join(o_dir, "json")
        #sim_output_dir = os.path.join(o_dir, "outputs")

        helper.create_clean_dirs(output_dir=o_dir,
                                 setup_simulation=self.setup_simulation,
                                 rename_existing_simulation=self.rename_existing_simulation,
                                 clean=self.clean)

        if not self.setup_simulation:
            return

        # Call generate files
        driver_ = generate.Generate(workflow_dir = self.workflow_dir,
                                     gpkg_file = gpkg_dir,
                                     forcing_dir = f_dir,
                                     ngen_dir = self.ngen_dir,
                                     sim_time = self.simulation_time,
                                     formulation = self.formulation,
                                     output_dir = o_dir,
                                     forcing_format = self.forcing_format,
                                     ngen_cal_type = self.ngen_cal_type,
                                     schema = self.schema_type)

        failed = False
        if not failed:
            basin_ids.append(gpkg_id)
            x = gpd.read_file(gpkg_dir, layer="divides")
            num_cats.append(len(x["divide_id"]))

        if self.verbosity >= 1:
            result = "Passed" if not failed else "Failed"
            print(self.colors.GREEN + "  %s " % result + self.colors.END)

        return basin_ids, num_cats
        #quit()
        """
        driver = f'python {workflow_driver -gpkg {gpkg_dir} -ngen {self.ngen_dir} -f {f_dir} \
        -o {config_dir} -m {self.model_option} -p {self.precip_partitioning_scheme} -r {self.surface_runoff_scheme} -t \'{self.simulation_time}\' \
        -netcdf {self.is_netcdf_forcing} -troute {self.is_routing} -routfile {routing_file} -json {json_dir} -v {self.verbosity} \
        -ncal {self.ngen_cal_type} -sout {sim_output_dir} -schema {self.schema_type}'
        
        failed = subprocess.call(driver, shell=True)
        
        if not failed:
            basin_ids.append(gpkg_id)
            x = gpd.read_file(gpkg_dir, layer="divides")
            num_cats.append(len(x["divide_id"]))

        if self.verbosity >= 1:
            result = "Passed" if not failed else "Failed"
            print(self.colors.GREEN + "  %s " % result + self.colors.END)

        return basin_ids, num_cats
        """
    def main(self, nproc=4):
        basins_passed = os.path.join(self.output_dir, "basins_passed.csv")

        if os.path.exists(basins_passed):
            os.remove(basins_passed)

        forcing_files = self.get_forcing_files(self.gpkg_dirs)

        basin_ids = []
        num_cats = []

        pool = multiprocessing.Pool(processes=nproc)
        tuple_list = list(zip(self.gpkg_dirs, self.output_dirs, forcing_files))
        results = pool.map(self.generate_catchment_files, tuple_list)
        results = [result for result in results if result is not None]

        for result in results:
            basin_ids.extend(result[0])
            num_cats.extend(result[1])

        with open(basins_passed, 'w', newline='') as file:
            dat = zip(basin_ids, num_cats)
            writer = csv.writer(file)
            writer.writerow(['basin_id', 'n_cats'])
            writer.writerows(dat)

        pool.close()
        pool.join()

        return len(num_cats)

    def run(self):
        start_time = time.time()

        if self.verbosity >= 2:
            print(self.simulation_time)

        if self.clean[0] == "all":
            check = input("\nDo you really want to delete all except \'data\' directory? you will lose all ngen output data: ")
            if check.lower() in ["y", "yes"]:
                print("Deleting all existing simulation data except \'data\' directory.")
            elif check.lower() in ["n", "no"]:
                sys.exit("Quiting...")

        assert os.path.exists(self.output_dir)
        assert os.path.exists(self.workflow_dir)
        assert os.path.exists(self.ngen_dir)

        if not os.path.exists(os.path.join(self.workflow_dir, "src/python")):
            sys.exit("check `workflow_dir`, it should be the parent directory of `src/python` directory")

        all_dirs = glob.glob(os.path.join(self.input_dir, '*/'), recursive=True)
        self.gpkg_dirs = [Path(g) for g in all_dirs if os.path.exists(os.path.join(g, 'data')) and glob.glob(os.path.join(g, 'data', '*.gpkg'))]
        assert self.gpkg_dirs, f"No .gpkg files found in the data directory under {self.input_dir}."

        
        self.output_dirs = [self.output_dir / Path(g).name for g in self.gpkg_dirs]
        success_ncats = self.main(nproc=self.basins_in_par)
        
        end_time = time.time()
        total_time = end_time - start_time

        print("================== SUMMARY ===============================")
        print("| Total time         = %s [sec], %s [min]" % (round(total_time, 4), round(total_time / 60., 4)))
        print("| Total no of basins = %s " % len(self.gpkg_dirs))
        print("| Succeeded          = %s " % success_ncats)
        print("| Failed             = %s " % (len(self.gpkg_dirs) - success_ncats))
        print("==========================================================")
