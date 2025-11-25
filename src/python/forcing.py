import os
import sys
import glob
import yaml
from pathlib import Path
import subprocess
import xarray as xr
import pandas as pd
import platform
import json
import time


class ForcingProcessor:
    def __init__(self, config_file):
        self.config_file = config_file
        self.load_config()

        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.get_gpkg_dirs()
        
    def load_config(self):
        with open(self.config_file, 'r') as file:
            self.config = yaml.safe_load(file)

        self.sandbox_dir      = self.config['general'].get('sandbox_dir') #d["sandbox_dir"]
        self.input_dir        = self.config['general'].get('input_dir') #d["input_dir"]
        self.output_dir       = Path(self.config['general'].get('output_dir')) #d["output_dir"])
        self.dsim             = self.config['formulation']
        self.verbosity        = self.dsim.get('verbosity', 0)
        self.dforcing         = self.config['forcings']
        self.forcing_time     = self.dforcing["forcing_time"]
        self.forcing_format   = self.dforcing.get('forcing_format', '.nc')
        self.forcing_venv_dir = self.dforcing.get('forcing_venv_dir', os.path.expanduser("~/.venv_forcing"))

        start_yr = pd.Timestamp(self.forcing_time['start_time']).year
        end_yr   = pd.Timestamp(self.forcing_time['end_time']).year + 1

        forcing_dir      = os.path.join(self.input_dir, "{*}", f'data/forcing/{start_yr}_to_{end_yr}')
        self.forcing_dir = self.dforcing.get("forcing_dir", forcing_dir)

    def download_forcing(self):
        if not os.path.exists(self.config_file):
            sys.exit("Sample forcing yaml file does not exist, provided is " + self.config_file)

        failed = False

        for gpkg in self.gpkg_dirs:
            result = self.forcing_generate_catchment(gpkg)
            if result:
                failed = True

        return failed


    def forcing_generate_catchment(self, dir):
        os.chdir(dir)

        if not os.path.exists(os.path.join(dir, "data")):
            return

        self.gpkg_file = glob.glob(dir + "data/*.gpkg")[0]

        fdir = self.forcing_dir
        if "{*}" in self.forcing_dir:
            fdir = Path(self.forcing_dir.replace("{*}", Path(dir).name))

        forcing_config = self.write_forcing_input_files(forcing_dir=fdir)

        run_cmd = f'python {self.sandbox_dir}/extern/CIROH_DL_NextGen/forcing_prep/generate.py {forcing_config}'

        venv_bin = os.path.join(self.forcing_venv_dir, 'bin')

        if not os.path.exists(venv_bin):
            msg = f"Python venv for forcing does not exist. Provided {self.forcing_venv_dir}"
            sys.exit(msg)

        env = os.environ.copy()
        env['PATH'] = f"{venv_bin}:{env['PATH']}"
        result = subprocess.call(run_cmd, shell=True, env=env)

        if self.forcing_format == ".nc":
            print("Correcting forcing data ...")
            self.forcing_data_correction(fdir)


    def get_gpkg_dirs(self):
        all_dirs = glob.glob(os.path.join(self.input_dir, '*/'), recursive=True)
        assert all_dirs, f"No directories found in the input directory {self.input_dir}."
        self.gpkg_dirs = [
            g for g in all_dirs
            if os.path.exists(os.path.join(g, 'data')) and glob.glob(os.path.join(g, 'data', '*.gpkg'))
        ]


    def write_forcing_input_files(self, forcing_dir):

        forcing_basefile = os.path.join(self.sandbox_dir, "configs/basefiles/config_aorc.yaml")

        if not os.path.exists(forcing_basefile):
            sys.exit(f"Sample forcing yaml file does not exist, provided is {forcing_basefile}")

        with open(forcing_basefile, 'r') as file:
            d = yaml.safe_load(file)


        start_yr = pd.Timestamp(self.forcing_time['start_time']).year
        end_yr   = pd.Timestamp(self.forcing_time['end_time']).year

        if start_yr > end_yr:
            sys.exit(f"end_time ({end_yr})is less than the start_time ({start_yr}")

        if start_yr <= end_yr:
            end_yr = end_yr + 1

        d['gpkg'] = self.gpkg_file
        d["years"] = [start_yr, end_yr]
        d["out_dir"] = os.path.join(os.path.dirname(self.gpkg_file), "forcing")

        out_dir = Path(d['out_dir']) / f'{start_yr}_to_{end_yr}'
        are_identical = out_dir.resolve() == Path(forcing_dir).resolve()

        if not are_identical:
            raise RuntimeError(f"Directory mismatch: out_dir={out_dir} is not the same as forcing_dir={forcing_dir}.")

        if not os.path.exists(d["out_dir"]):
            os.makedirs("data/forcing")

        if self.forcing_format == '.csv':
            d['netcdf'] = False

        with open(os.path.join(d["out_dir"], "config_forcing.yaml"), 'w') as file:
            yaml.dump(d, file, default_flow_style=False, sort_keys=False)

        return os.path.join(d["out_dir"], "config_forcing.yaml")


    def forcing_data_correction(self, fdir):
        nc_file = glob.glob(f"{fdir}/*.nc")
        if len(nc_file) != 1:
            print("Can't correct the forcing data, either file does not exist or more than one files exist. Files found: ", nc_file)
            return

        nc_file = [f for f in nc_file if not "_corrected" in f][0]
        ds = xr.open_dataset(nc_file)
        ds['APCP_surface'].attrs['units'] = 'mm/hr'

        for name in ds.data_vars:
            if ds[name].isnull().any():
                if self.verbosity >= 2:
                    print(f"Missing data: NaNs found in {name}.")
                ds[name] = ds[name].interpolate_na(dim='time', method='nearest')
            elif self.verbosity >= 2:
                print(f"Looks good. No NaNs found in {name}.")
        path = Path(nc_file)
        new_file = Path(fdir) / (path.stem + "_corrected.nc")
        ds.to_netcdf(new_file)
