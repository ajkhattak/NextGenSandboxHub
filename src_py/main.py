############################################################################################
# Author  : Ahmad Jan Khattak
# Contact : ahmad.jan@noaa.gov
# Date    : October 11, 2023 
############################################################################################


import os,sys
import subprocess
import pandas as pd
import glob
import shutil
import re
import geopandas as gpd
import csv
import yaml
import multiprocessing
from functools import partial # used for partially applied function which allows to create new functions with arguments
import time
import argparse
import json
from pathlib import Path

import helper
# Note #1: from the command line just run 'python path_to/main.py'
# Note #2: make sure to adjust the following required arguments
# Note #3: several model coupling options are available, the script currently supports a few of them, for full list see
#          below the coupled_models_option


############################# Required Arguments ###################################
### Specify the following four directories (change according to your settings)
# workflow_dir    : points to the base directory of src_py under basin_workflow
# output_dir        : geopackage(s) directory (format output_dir/GAUGE_ID see below)                 
# nc_forcing_dir  : lumped forcings directory (pre-downloaded forcing data for each catchment (.csv or .nc); only need if forcing
#                   directory is outside the structure of the output_dir described below)
# ngen_dir        : nextgen directory path

### Specify the following model options
# simulation_time            : string  | simulation start/end times; format YYYYMMDDHHMM (YYYY, MM, DD, HH, MM)
# model_option               : string  | model option (see available options below)
# surface_runoff_scheme      : string  | surface runoff scheme for CFE and LASAM OPTION=[GIUH, NASH_CASCADE]
# precip_partitioning_scheme : string  | precipitation partitioning scheme for CFE OPTION=[Schaake, Xinanjiang]
# is_netcdf_forcing          : boolean | True if forcing data is in netcdf format
# clean                      : str/lst | Options = all, existing, none (all deletes everything other than data directory, existing deletes
#                                        existing simulation configs, json, and outputs directories
# num_processors_config      : int     | Number of processors for generating config/realiation files
# num_processors_sim         : int     | Number of processors for catchment/geopackage partition for ngen parallel runs
# setup_simulation           : boolean | True to create files for simulaiton;
# rename_existing_simulation : string  | move the existing simulation set (json, configs, outputs dirs) to this directory, e.g. "sim_cfe1.0"

####################################################################################

"""
output_dir:
   - 10244950
     - data
       - Gage_10244950.gpkg
       - forcings
   - 01047000
     - data
       - Gage_01047000.gpkg
       - forcings
"""

"""
coupled_models_options = {
"C"   : "cfe",
"L"   : "lasam",
"NC"  : "nom_cfe",
"NL"  : "nom_lasam",
"NCP" : "nom_cfe_pet",
"NCSS": "nom_cfe_smp_sft",
"NLSS": "nom_lasam_smp_sft",
"NT"  : "nom_topmodel",
"BC"  : "baseline_cfe",
"BL"  : "baseline_lasam"
}
"""

###########################################################################
class colors:
    GREEN = '\033[92m'
    RED   = '\033[91m'
    END   = '\033[0m'

infile  = sys.argv[1]
with open(infile, 'r') as file:
    d = yaml.safe_load(file)

dsim = d['simulations']
workflow_dir               = d["workflow_dir"]
input_dir                  = d["input_dir"]
output_dir                 = Path(d["output_dir"])
ngen_dir                   = dsim["ngen_dir"]
simulation_time            = dsim["simulation_time"]
model_option               = dsim['model_option']
precip_partitioning_scheme = dsim['precip_partitioning_scheme']
surface_runoff_scheme      = dsim['surface_runoff_scheme']
clean                      = dsim.get('clean', "none")
is_routing                 = dsim.get('is_routing', False)
verbosity                  = dsim.get('verbosity', 0)
num_processors_config      = dsim.get('num_processors_config', 1)
num_processors_sim         = dsim.get('num_processors_sim', 1)
setup_simulation           = dsim.get('setup_simulation', True)
rename_existing_simulation = dsim.get('rename_existing_simulation', "")
schema_type                = dsim.get('schema_type', "noaa-owp")


dforcing = d['forcings']
forcing_dir      = dforcing.get("forcing_dir", "")
forcing_format   = dforcing.get('forcing_format', '.nc')
forcing_source   = dsim.get('forcing_source', "")

is_netcdf_forcing = True
if (forcing_format == '.csv'):
    is_netcdf_forcing = False

dcalib = d['ngen_cal']
ngen_cal_type = dcalib.get('task_type', None)

output_dir.mkdir(parents=True, exist_ok=True)

def process_clean_input_param():
    clean_lst = []
    if (isinstance(clean, str)):
        clean_lst = [clean]
    elif (isinstance(clean, list)):
        clean_lst.extend(clean)
    return clean_lst

clean = process_clean_input_param()


def get_forcing_files(gpkg_dirs, is_corrected=True):

    forcing_files = []

    if forcing_format == ".nc":
        if "{*}" in forcing_dir:
            for g in gpkg_dirs:
                forcing_dir_local = forcing_dir
                fdir = Path(forcing_dir_local.replace("{*}", Path(g).name))

                if not fdir.exists() or not fdir.is_dir():
                    raise ValueError("Forcing directory '{fdir}' does not exist.")
                if (is_corrected):
                    forcing_file = glob.glob(f"{fdir}/*_corrected.nc")[0]
                else:
                    nc_file = glob.glob(f"{fdir}/*.nc")
                    forcing_file = [f for f in nc_file if not "_corrected" in f][0]

                forcing_files.append(forcing_file)
        else:
            if not Path(forcing_dir).exists():
                raise ValueError("Forcing directory '{forcing_dir}' does not exist.")

            if not Path(forcing_dir).is_dir():
                forcing_file = forcing_dir
            else:
                if (is_corrected):
                    forcing_file = glob.glob(f"{forcing_dir}/*_corrected.nc")[0]
                else:
                    nc_file = glob.glob(f"{fdir}/*.nc")
                    forcing_file = [f for f in nc_file if not "_corrected" in f][0]

            forcing_files.append(forcing_file)
    else:
        if "{*}" in forcing_dir:
            for g in gpkg_dirs:
                forcing_dir_local = forcing_dir
                fdir = Path(forcing_dir_local.replace("{*}", Path(g).name))

                if not fdir.exists():
                    raise ValueError("Forcing directory '{fdir}' does not exist.")
                if not fdir.is_dir():
                    raise ValueError("forcing format is .csv, so '{fdir}' should point to a directory and not file.")

                forcing_files.append(fdir)


    return forcing_files

##############################################################################

def generate_catchment_files(dirs):

    i_dir = dirs[0]
    o_dir = dirs[1]
    f_dir = dirs[2]
    
    o_dir.mkdir(parents=True, exist_ok=True)
    os.chdir(o_dir)

    basin_ids = []
    num_cats  = []
    
    if (verbosity >=2):
        print ("***********************************")
        print ("cwd: ", os.getcwd())
        print ("input_dir: ", i_dir)
        print ("output_dir: ", o_dir)
        print ("forcing_dir: ", f_dir)


    gpkg_name = Path(glob.glob(str(i_dir / "data" / "*.gpkg"))[0]).name
    gpkg_dir  = Path(glob.glob(str(i_dir / "data" / "*.gpkg"))[0])
    gpkg_id   = i_dir.name

    filled_dot = '●'

    if verbosity >=1:
        print(filled_dot, gpkg_name, end="")


    gpkg_dir   = os.path.join(i_dir, gpkg_dir)
    config_dir = os.path.join(o_dir,"configs")
    json_dir   = os.path.join(o_dir, "json")
    sim_output_dir = os.path.join(o_dir, "outputs")
    
    helper.create_clean_dirs(output_dir = o_dir, setup_simulation = setup_simulation,
                             rename_existing_simulation = rename_existing_simulation, clean = clean)

    if (not setup_simulation):
        return

    workflow_driver = os.path.join(workflow_dir, "src_py/driver.py")

    routing_file = os.path.join(workflow_dir, "configs/basefiles/config_troute.yaml")

    driver = f'python {workflow_driver} -gpkg {gpkg_dir} -ngen {ngen_dir} -f {f_dir} \
    -o {config_dir} -m {model_option} -p {precip_partitioning_scheme} -r {surface_runoff_scheme} -t \'{simulation_time}\' \
    -netcdf {is_netcdf_forcing} -troute {is_routing} -routfile {routing_file} -json {json_dir} -v {verbosity} \
    -ncal {ngen_cal_type} -sout {sim_output_dir} -schema {schema_type}'
    
    failed = subprocess.call(driver, shell=True)

    if (not failed):
        basin_ids.append(gpkg_id)
        x = gpd.read_file(gpkg_dir, layer="divides")
        num_cats.append(len(x["divide_id"]))

    if verbosity >=1:
        result = "Passed" if not failed else "Failed" 
        print (colors.GREEN + "  %s "%result + colors.END )

    return basin_ids, num_cats


############################### MAIN LOOP #######################################

def main(nproc = 4):
    
    basins_passed = os.path.join(output_dir,"basins_passed.csv")
    
    if (os.path.exists(basins_passed)):
        os.remove(basins_passed)

    forcing_files = get_forcing_files(gpkg_dirs)

    basin_ids = []
    num_cats  = []

    # create a pool of processors using multiprocessing tool
    pool = multiprocessing.Pool(processes=nproc)

    #print ("CPU:", multiprocessing.cpu_count())

    tuple_list = list(zip(gpkg_dirs, output_dirs, forcing_files))

    results = pool.map(generate_catchment_files, tuple_list)

    results = [result for result in results if result is not None]

    # collect results from all processes
    for result in results:
        basin_ids.extend(result[0])
        num_cats.extend(result[1])

    # Write results to CSV
    with open(basins_passed, 'w', newline='') as file:
        dat = zip(basin_ids, num_cats)
        writer = csv.writer(file)
        writer.writerow(['basin_id', 'n_cats'])
        writer.writerows(dat)

    pool.close()
    pool.join()

    return len(num_cats)

if __name__ == "__main__":

    start_time = time.time()
    
    if (verbosity >=2):
        print (simulation_time)

    if (clean[0] == "all"):
        check = input("\nDo you really want to delete all except \'data\' directory? you will lose all ngen output data: ")
        if check.lower() in ["y", "yes"]:
            print ("Deleting all existing simulation data except \'data\' directory.")
        elif check.lower() in ["n", "no"]:
            sys.exit("Quiting...")
    
    ############ CHECKS ###################
    assert (os.path.exists(output_dir))
    assert (os.path.exists(workflow_dir))
    assert (os.path.exists(ngen_dir))
    ######################################

    if (not os.path.exists(os.path.join(workflow_dir, "src_py"))):
        sys.exit("check `workflow_dir`, it should be the parent directory of `src_py` directory")

    all_dirs = glob.glob(os.path.join(input_dir, '*/'), recursive = True)

    # all the directories that have a .gpkg file under input_dir/data/
    gpkg_dirs = [
        Path(g) for g in all_dirs 
        if os.path.exists(os.path.join(g, 'data')) and glob.glob(os.path.join(g, 'data', '*.gpkg'))
    ]

    assert gpkg_dirs, f"No .gpkg files found in the data directory under {input_dir}."
    
    # all output directories with output_dir/cat_id
    output_dirs = [output_dir / Path(g).name for g in gpkg_dirs ]

    success_ncats = main(nproc = num_processors_config)

    end_time = time.time()
    total_time = end_time - start_time # in seconds

    print ("================== SUMMARY ===============================")
    print("| Total time         = %s [sec], %s [min]" % (round(total_time,4), round(total_time/60.,4)))
    print("| Total no of basins = %s "% len(gpkg_dirs))
    print("| Succeeded          = %s "% success_ncats)
    print("| Failed             = %s "% (len(gpkg_dirs)-success_ncats))
    print ("==========================================================")