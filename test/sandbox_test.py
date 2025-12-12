############################################################################################
# Author  : Ahmad Jan Khattak
# Contact : ahmad.jan.khattak@noaa.gov
# Date    : December 11, 2025
############################################################################################
# sandbox unit test

import os, sys
import subprocess
import yaml
import argparse
from pathlib import Path
import sandbox
import shutil

sandbox_test_dir = Path(__file__).resolve().parent

sandbox_config   = sandbox_test_dir / "configs" / "sandbox_config.yaml"

with open(sandbox_config, 'r') as file:
    d = yaml.safe_load(file)

# modify values
d["general"]["input_dir"] = str(sandbox_test_dir / "input")
d["general"]["output_dir"] = str(sandbox_test_dir / "output")

d["subsetting"]["hf_gpkg_path"] = "/Users/ahmadjankhattak/Core/input_data/hf2.2_gpkgs/conus_nextgen.gpkg" # <- Set this to your local settings
#d["subsetting"]["dem_input_file"] = "<path_to>/dem.vrt" # <- OPTIONAL: Set this to your local settings

with open(sandbox_config, "w") as f:
    yaml.safe_dump(d, f, sort_keys=False)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("-subset", action='store_true', help="Subset basin (generate .gpkg files)")
        parser.add_argument("-forc",   action='store_true', help="Download forcing data")
        parser.add_argument("-conf",   action='store_true', help="Generate config files")
        parser.add_argument("-run",    action='store_true', help="Run NextGen simulations")
        parser.add_argument("-all",    action='store_true', help="Run all: subset, forc, conf, run")
        parser.add_argument("-clean",    action='store_true', help="Run all: subset, forc, conf, run")
        args = parser.parse_args()
    except SystemExit:
        sys.exit(0)

    # test sandbox -conf
    if args.subset:
        print ("-------------------------------------")
        print ("Running subset step")
        run_conf = f"sandbox -subset -i {sandbox_config}"
        result = subprocess.call(run_conf, shell=True)
    elif args.forc:
        run_conf = f"sandbox -forc -i {sandbox_config}"
        result = subprocess.call(run_conf, shell=True)
    elif args.conf:
        run_conf = f"sandbox -conf -i {sandbox_config}"
        result = subprocess.call(run_conf, shell=True)
    elif args.run:
        run_conf = f"sandbox -run -i {sandbox_config}"
        result = subprocess.call(run_conf, shell=True)
        
    elif args.all:
        print ("-------------------------------------")
        print ("Running subset step")
        run_conf = f"sandbox -subset -i {sandbox_config}"
        result = subprocess.call(run_conf, shell=True)
        
        print ("-------------------------------------")
        print ("Running forcing step")
        run_conf = f"sandbox -forc -i {sandbox_config}"
        result = subprocess.call(run_conf, shell=True)
        
        print ("-------------------------------------")
        print ("Running config generation step")
        run_conf = f"sandbox -conf -i {sandbox_config}"
        result = subprocess.call(run_conf, shell=True)
        
        print ("-------------------------------------")
        print ("Running test simulation")
        run_conf = f"sandbox -run -i {sandbox_config}"
        result = subprocess.call(run_conf, shell=True)

    elif args.clean:
        output_dir = sandbox_test_dir / "output"
        
        if output_dir.exists():
            print(f"Deleting: {output_dir}")
            shutil.rmtree(output_dir)
        else:
            print(f"Directory does not exist: {output_dir}")

    # revert back
    subprocess.run(["git", "checkout", "--", sandbox_config], check=True)
