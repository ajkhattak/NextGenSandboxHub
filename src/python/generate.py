############################################################################################
# Author  : Ahmad Jan Khattak
# Contact : ahmad.jan.khattak@noaa.gov
# Date    : October 11, 2023 
############################################################################################

# driver of the script, generates configuration files and realization files by calling
# the respective scripts

import os
import sys
import subprocess
from pathlib import Path
import argparse
import json

from src.python import configuration
from src.python import realization

class Generate:
    def __init__(self, sandbox_dir, gpkg_file, forcing_dir, ngen_dir,
                 sim_time, formulation, formulations_supported, output_dir,
                 forcing_format, ngen_cal_type, schema, domain):
        
        self.sandbox_dir = sandbox_dir
        self.gpkg_file   = gpkg_file
        self.forcing_dir = forcing_dir
        self.ngen_dir    = ngen_dir
        self.output_dir  = output_dir
        self.schema      = schema
        self.verbosity   = 1
        self.domain      = domain

        self.simulation_time = sim_time
        self.formulation_in  = formulation.replace(" ", "") # remove space if any
        self.forcing_format  = forcing_format
        self.ngen_cal_type   = ngen_cal_type

        
        if not os.path.exists(self.gpkg_file):
            sys.exit(f'The gpkg file does not exist: ', self.gpkg_file)

        if not os.path.exists(self.forcing_dir):
            sys.exit(f'The forcing directory does not exist: ', self.forcing_dir)

        self.formulations_supported = formulations_supported
        formulation_in_lower       = self.formulation_in.lower()

        # Check if T-ROUTE is present (case-insensitive)
        has_troute = "t-route" in formulation_in_lower

        formulation_test = formulation_in_lower if has_troute else f"{self.formulation_in},T-ROUTE"

        if formulation_test.upper() in formulations_supported:
            self.formulation = formulation_test.upper()
        else:
            raise ValueError(
                f"\nUnsupported formulation: {self.formulation_in} \n"
                f"Supported: {self.formulations_supported} \n"
                "[INFO]: Formulations that omit T-ROUTE are allowed, as it is appended automatically; however, all other formulation components must be specified exactly as supported."
            )

        if self.verbosity >= 3:
            print("*******************************************")
            print(self.colors.BLUE)
            print("Running (from driver.py):\n", generate_config_files)
            print("Model option provided: ", args.models_option)
            print("Generating configuration files for model(s) option: ", self.coupled_models_options[args.models_option])
            print(self.colors.ENDC)
            print("*******************************************")

        ConfigGen = configuration.ConfigurationGenerator(sandbox_dir = self.sandbox_dir,
                                                         gpkg_file   = self.gpkg_file,
                                                         forcing_dir = self.forcing_dir,
                                                         output_dir  = self.output_dir,
                                                         ngen_dir    = self.ngen_dir,
                                                         formulation = self.formulation,
                                                         simulation_time = self.simulation_time,
                                                         verbosity     = 1,
                                                         ngen_cal_type = self.ngen_cal_type,
                                                         schema_type   = self.schema)

        if self.verbosity >= 3:
            print("Running (from driver.py): \n ", generate_realization_file)
            print(self.colors.ENDC)
            
        if "NOM" in self.formulation:
            ConfigGen.write_nom_input_files()

        if "PET" in self.formulation:
            ConfigGen.write_pet_input_files()

        if "CFE" in self.formulation:
            ConfigGen.write_cfe_input_files()

        if "TOPMODEL" in self.formulation:
            ConfigGen.write_topmodel_input_files()

        if "CASAM" in self.formulation:
            ConfigGen.write_lasam_input_files()

        if "SFT" in self.formulation:
            ConfigGen.write_sft_input_files()

        if "SNOW17" in self.formulation:
            ConfigGen.write_snow17_input_files()

        if "LSTM" in self.formulation:
            ConfigGen.write_lstm_input_files()

        if "SAC-SMA" in self.formulation:
            ConfigGen.write_sacsma_input_files()

        if "SMP" in self.formulation:
            
            if "CFE" in self.formulation:
                ConfigGen.write_smp_input_files(cfe_coupled=True, lasam_coupled=False)
            elif "LASAM" in self.formulation:
                ConfigGen.write_smp_input_files(cfe_coupled=False, lasam_coupled=True)

        if "t-route" in self.formulation.lower():
            ConfigGen.write_troute_input_files()
        
        result = False
        if result:
            sys.exit("config files could not be generated, check the options provided!")

        if self.verbosity >= 3:
            print("*******************************************")
            print(self.colors.GREEN)
            print("Generating realization file ...")
            
        RealGen = realization.RealizationGenerator(ngen_dir = self.ngen_dir,
                                                   forcing_dir = self.forcing_dir,
                                                   output_dir = self.output_dir,
                                                   formulation = self.formulation,
                                                   simulation_time = self.simulation_time,
                                                   forcing_format = self.forcing_format,
                                                   verbosity = 1,
                                                   ngen_cal_type = self.ngen_cal_type,
                                                   domain = self.domain)

        RealGen.write_realization_file()

                
    class colors:
        BLUE = '\33[34m'
        BLACK = '\33[30m'
        RED = '\33[31m'
        CYAN = '\033[96m'
        GREEN = '\033[32m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'
