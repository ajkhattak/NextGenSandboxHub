############################################################################################
# Author  : Ahmad Jan Khattak
# Contact : ahmad.jan.khattak@noaa.gov
# Date    : September 28, 2023
############################################################################################

"""
The script generates realization files for a given model coupling option
 - inputs  : see main function for inputs (taken as arguments)
 - outputs : writes nextgen realization file for the basin
"""


import os
import sys
import glob
import json
import argparse
import shutil
import json

class RealizationGenerator:
    def __init__(self, ngen_dir, forcing_dir,  output_dir, formulation,
                 simulation_time, forcing_format, verbosity, ngen_cal_type,
                 domain):
        
        self.ngen_dir    = ngen_dir
        self.forcing_dir = forcing_dir
        self.output_dir  = output_dir
        self.formulation = formulation
        self.simulation_time = simulation_time
        self.config_dir      = os.path.join(output_dir,"configs")
        self.forcing_format  = forcing_format
        self.verbosity       = verbosity
        self.ngen_cal_type   = ngen_cal_type
        self.lib_files       = self.get_lib_files()
        self.domain          = domain.lower()
        
        realization_name = self.formulation.replace(",","_").lower()
        self.realization_file = os.path.join(self.output_dir,"json",f"realization_{realization_name}.json")
        
        if "CFE-S" in self.formulation:
            surface_water_partitioning_scheme = "Schaake"
        elif "CFE-X" in self.formulation:
            surface_water_partitioning_scheme = "Xinanjiang"

        if not os.path.exists(self.forcing_dir):
            sys.exit(f"Forcing directory does not exist: {self.forcing_dir}")

        cfe_dir = os.path.join(self.output_dir, "configs", "cfe")
        if 'CFE-S' in self.formulation and not os.path.exists(cfe_dir):
            print(f"CFE config files directory does not exist. {cfe_dir}")
            sys.exit(0)

        sft_dir = os.path.join(self.output_dir, "configs", "sft")
        if 'SFT' in self.formulation and not os.path.exists(sft_dir):
            print(f"SFT config files directory does not exist. {sft_dir}")
            sys.exit(0)

        smp_dir = os.path.join(self.output_dir, "configs", "smp")
        if 'SMP' in self.formulation and not os.path.exists(smp_dir):
            print(f"SMP config files directory does not exist. {smp_dir}")
            sys.exit(0)

        lasam_dir = os.path.join(self.output_dir, "configs", "lasam")
        if 'LASAM' in self.formulation and not os.path.exists(lasam_dir):
            print(f"LASAM config files directory does not exist. {lasam_dir}")
            sys.exit(0)
            
    
    def get_lib_files(self):
        lib_files = {}
        extern_path = os.path.join(self.ngen_dir, 'extern')
        models = os.listdir(extern_path)
        platform = sys.platform
        ext = "lib*.so" if "linux" in platform else "lib*.dylib"

        for m in models:
            if m in ['SoilFreezeThaw', 'cfe', 'SoilMoistureProfiles', 'LASAM', 'sloth', 'evapotranspiration', 'noah-owp-modular', 'topmodel']:
                path_m = os.path.join(os.path.join(extern_path, m), "cmake_build") if m in ['sloth', 'noah-owp-modular', 'topmodel'] else os.path.join(os.path.join(extern_path, m, m), "cmake_build")
                if os.path.exists(path_m):
                    exe_m = glob.glob(os.path.join(path_m, ext))
                    if exe_m:
                        exe_m = exe_m[0].split('extern')
                        exe_m = exe_m[1].split('.')
                        lib_files[m] = os.path.join(self.ngen_dir, 'extern' + str(exe_m[0]))
                    else:
                        lib_files[m] = ""
        return lib_files

    def get_pet_block(self, var_names_map=False):
        block = {
            "name": "bmi_c",
            "params": {
                "name": "bmi_c",
                "model_type_name": "PET",
                "library_file": self.lib_files['evapotranspiration'],
                "forcing_file": "",
                "init_config": os.path.join(self.config_dir, 'pet/pet_config_{{id}}.txt'),
                "allow_exceed_end_time": "true",
                "main_output_variable": "water_potential_evaporation_flux",
                "registration_function": "register_bmi_pet",
                "uses_forcing_file": "false"
            }
        }
        
        # AORC forcing names
        if (self.domain == "conus" and var_names_map):
            block['params']['variables_names_map'] = {
                "PRCPNONC": "APCP_surface",
                "Q2": "SPFH_2maboveground",
                "SFCTMP": "TMP_2maboveground",
                "UU": "UGRD_10maboveground",
                "VV": "VGRD_10maboveground",
                "LWDN": "DLWRF_surface",
                "SOLDN": "DSWRF_surface",
                "SFCPRS": "PRES_surface"
            }
        elif (var_names_map):
              block['params']['variables_names_map'] = {
                  "PRCPNONC": "atmosphere_water__liquid_equivalent_precipitation_rate",
                  "Q2": "atmosphere_air_water~vapor__relative_saturation",
                  "SFCTMP": "land_surface_air__temperature",
                  "LWDN": "land_surface_radiation~incoming~longwave__energy_flux",
                  "SOLDN": "land_surface_radiation~incoming~shortwave__energy_flux",
                  "UU": "land_surface_wind__x_component_of_velocity",
                  "VV": "land_surface_wind__y_component_of_velocity",
                  "SFCPRS": "land_surface_air__pressure"
              }
        
        return block

    def get_noah_owp_modular_block(self):
        block = {
            "name": "bmi_fortran",
            "params": {
                "name": "bmi_fortran",
                "model_type_name": "NoahOWP",
                "main_output_variable": "QINSUR",
                "library_file": self.lib_files['noah-owp-modular'],
                "init_config": os.path.join(self.config_dir, 'noahowp/noahowp_config_{{id}}.input'),
                "allow_exceed_end_time": True,
                "fixed_time_step": False,
                "uses_forcing_file": False,
                "variables_names_map": {
                    "PRCPNONC": "atmosphere_water__liquid_equivalent_precipitation_rate",
                    "Q2": "atmosphere_air_water~vapor__relative_saturation",
                    "SFCTMP": "land_surface_air__temperature",
                    "LWDN": "land_surface_radiation~incoming~longwave__energy_flux",
                    "SOLDN": "land_surface_radiation~incoming~shortwave__energy_flux",
                    "UU": "land_surface_wind__x_component_of_velocity",
                    "VV": "land_surface_wind__y_component_of_velocity",
                    "SFCPRS": "land_surface_air__pressure"
                }
            }
        }

        # AORC names (details at the end of file)
        if (self.domain == "conus"):
            block['params']['variables_names_map'] = {
                "PRCPNONC": "APCP_surface",
                "Q2": "SPFH_2maboveground",
                "SFCTMP": "TMP_2maboveground",
                "UU": "UGRD_10maboveground",
                "VV": "VGRD_10maboveground",
                "LWDN": "DLWRF_surface",
                "SOLDN": "DSWRF_surface",
                "SFCPRS": "PRES_surface"
            }

        return block

    def get_cfe_block(self, cfe_standalone=False):
        block = {
            "name": "bmi_c",
            "params": {
                "name": "bmi_c",
                "model_type_name": "CFE",
                "main_output_variable": "Q_OUT",
                "library_file": self.lib_files['cfe'],
                "init_config": os.path.join(self.config_dir, 'cfe/cfe_config_{{id}}.txt'),
                "allow_exceed_end_time": True,
                "fixed_time_step": False,
                "uses_forcing_file": False,
                "variables_names_map": {
                    "atmosphere_water__liquid_equivalent_precipitation_rate": "APCP_surface",
                    "water_potential_evaporation_flux": "water_potential_evaporation_flux"
                },
                "registration_function": "register_bmi_cfe"
            }
        }
        if cfe_standalone:
            sub_map = {
                "ice_fraction_schaake": "ice_fraction_schaake",
                "ice_fraction_xinanjiang": "ice_fraction_xinanjiang",
                "soil_moisture_profile": "soil_moisture_profile"
            }
            block["params"]["variables_names_map"].update(sub_map)
        if "NOM" in self.formulation and not "PET" in self.formulation:
            block["params"]["variables_names_map"]["water_potential_evaporation_flux"] = "EVAPOTRANS"
        if "NOM" in self.formulation:
            block["params"]["variables_names_map"]["atmosphere_water__liquid_equivalent_precipitation_rate"] = "QINSUR"
        return block

    def get_topmodel_block(self):
        block = {
            "name": "bmi_c",
            "params": {
                "name": "bmi_c",
                "model_type_name": "TOPMODEL",
                "main_output_variable": "Qout",
                "library_file": self.lib_files['topmodel'],
                "init_config": os.path.join(self.config_dir, 'topmodel/topmod_{{id}}.run'),
                "allow_exceed_end_time": True,
                "fixed_time_step": False,
                "uses_forcing_file": False,
                "variables_names_map": {
                    "atmosphere_water__liquid_equivalent_precipitation_rate": "QINSUR",
                    "water_potential_evaporation_flux": "EVAPOTRANS"
                },
                "registration_function": "register_bmi_topmodel"
            }
        }
        return block

    def get_sft_block(self):
        block = {
            "name": "bmi_c++",
            "params": {
                "name": "bmi_c++",
                "model_type_name": "SFT",
                "main_output_variable": "num_cells",
                "library_file": self.lib_files['SoilFreezeThaw'],
                "init_config": os.path.join(self.config_dir, 'sft/sft_config_{{id}}.txt'),
                "allow_exceed_end_time": True,
                "uses_forcing_file": False,
                "variables_names_map": {
                    "ground_temperature": "TGS"
                }
            }
        }
        return block

    def get_smp_block(self):
        block = {
            "name": "bmi_c++",
            "params": {
                "name": "bmi_c++",
                "model_type_name": "SMP",
                "main_output_variable": "soil_water_table",
                "library_file": self.lib_files['SoilMoistureProfiles'],
                "init_config": os.path.join(self.config_dir, 'smp/smp_config_{{id}}.txt'),
                "allow_exceed_end_time": True,
                "uses_forcing_file": False,
                "variables_names_map": {
                    "soil_storage": "SOIL_STORAGE",
                    "soil_storage_change": "SOIL_STORAGE_CHANGE"
                }
            }
        }
        if self.coupled_models in ["nom_cfe_smp_sft", "cfe_smp", "nom_cfe_smp"]:
            name_map = {
                "soil_storage": "SOIL_STORAGE",
                "soil_storage_change": "SOIL_STORAGE_CHANGE"
            }
        elif self.coupled_models == "nom_lasam_smp_sft":
            name_map = {
                "soil_storage": "sloth_soil_storage",
                "soil_storage_change": "sloth_soil_storage_change",
                "soil_moisture_wetting_fronts": "soil_moisture_wetting_fronts",
                "soil_depth_wetting_fronts": "soil_depth_wetting_fronts",
                "num_wetting_fronts": "soil_num_wetting_fronts"
            }
        else:
            print("coupled_models name should be nom_cfe_smp_sft or nom_lasam_smp_sft, provided is ", self.coupled_models)
            quit()
        block["params"]["variables_names_map"] = name_map
        return block

    def get_lasam_block(self):
        #note the model_type_name should be LGAR as this name is currently supported by ngen-cal for calibration
        block = {
            "name": "bmi_c++",
            "params": {
                "name": "bmi_c++",
                "model_type_name": "LGAR",
                "main_output_variable": "precipitation_rate",
                "library_file": self.lib_files['LASAM'],
                "init_config": os.path.join(self.config_dir, 'lasam/lasam_config_{{id}}.txt'),
                "allow_exceed_end_time": True,
                "uses_forcing_file": False,
                "variables_names_map": {
                    "precipitation_rate": "APCP_surface",
                    "potential_evapotranspiration_rate": "water_potential_evaporation_flux"
                }
            }
        }
        
        if "NOM" in self.formulation:
            block["params"]["variables_names_map"]["precipitation_rate"] = "QINSUR"
        if "PET" not in self.formulation:
            block["params"]["variables_names_map"]["potential_evapotranspiration_rate"] = "EVAPOTRANS"

        return block

    def get_sloth_block(self):
        block = {
            "name": "bmi_c++",
            "params": {
                "name": "bmi_c++",
                "model_type_name": "SLOTH",
                "main_output_variable": "z",
                "library_file": self.lib_files['sloth'],
                "init_config": '/dev/null',
                "allow_exceed_end_time": True,
                "fixed_time_step": False,
                "uses_forcing_file": False,
            }
        }
        params = {}
        if "CFE" in self.formulation and not "SFT" in self.formulation:
            params = {
                "ice_fraction_schaake(1,double,m,node)": 0.0,
                "ice_fraction_xinanjiang(1,double,1,node)": 0.0,
                "soil_moisture_profile(1,double,1,node)": 0.0
            }
        elif "LASAM" in self.formulation and not "SFT" in self.formulation:
            params = {
                "soil_temperature_profile(1,double,K,node)": 275.15
            }
        elif "SMP" in self.formuation and not "TOPMODEL" in self.formulation and not "LASAM" in self.formulation:
            params = {
                "soil_moisture_wetting_fronts(1,double,1,node)": 0.0,
                "soil_depth_wetting_fronts(1,double,1,node)": 0.0,
                "num_wetting_fronts(1,int,1,node)": 1.0,
                "Qb_topmodel(1,double,1,node)": 0.0,
                "Qv_topmodel(1,double,1,node)": 0.0,
                "global_deficit(1,double,1,node)": 0.0
            }
        elif "SMP" in self.formulation and "LASAM" in self.formulation:
            params = {
                "sloth_soil_storage(1,double,m,node)": 1.0E-10,
                "sloth_soil_storage_change(1,double,m,node)": 0.0,
                "Qb_topmodel(1,double,1,node)": 0.0,
                "Qv_topmodel(1,double,1,node)": 0.0,
                "global_deficit(1,double,1,node)": 0.0
            }
        else:
            msg = "coupled_models name should be nom_cfe, or nom_cfe_smp_sft or nom_lasam_smp_sft, provided is " + self.coupled_models
            sys.exit(msg)
        block["params"]["model_params"] = params
        return block

    def get_jinjabmi_unit_conversion_block(self):
        block_jinjabmi = {
            "name": "bmi_python",
            "params": {
                "model_type_name": "jinjabmi",
                "python_type": "jinjabmi.Jinja",
                "init_config": os.path.join(self.config_dir, "jinjabmi/baseline_support.yml"),
                "allow_exceed_end_time": True,
                "main_output_variable": "actual_ET_input",
                "uses_forcing_file": False,
                "variables_names_map": {
                    "actual_ET_input": "ACTUAL_ET",
                    "direct_runoff_input": "DIRECT_RUNOFF",
                    "giuh_runoff_input": "GIUH_RUNOFF",
                    "soil_storage_input": "SOIL_STORAGE",
                    "catchment_area_input": "sloth_catchment_area",
                    "deep_gw_to_channel_flux_input": "DEEP_GW_TO_CHANNEL_FLUX",
                    "soil_to_gw_flux_input": "SOIL_TO_GW_FLUX",
                    "giuh_runoff_input": "GIUH_RUNOFF"
                }
            }
        }

        block_unit_conversion = {
            "name": "bmi_c++",
            "params": {
                "model_type_name": "bmi_c++_sloth",
                "library_file": self.lib_files['sloth'],
                "init_config": "/dev/null",
                "allow_exceed_end_time": True,
                "main_output_variable": "nwm_ponded_depth",
                "uses_forcing_file": False,
                "model_params": {
                    "nwm_ponded_depth(1,double,mm,node,nwm_ponded_depth_output)": 0.0,
                    "ACTUAL_ET_mm(1,double,mm,node,ACTUAL_ET)": 0.0
                }
            }
        }

        return [block_jinjabmi, block_unit_conversion]

    def write_realization_file(self):

        root = {
            "time": {
                "start_time": self.simulation_time["start_time"],
                "end_time": self.simulation_time["end_time"],
                "output_interval": 3600
            },
            "global": {
                "formulations": "to_be_filled_in",
                "forcing": {
                    "file_pattern": ".*{{id}}.*.csv",
                    "path": self.forcing_dir,
                    "provider": "CsvPerFeature"
                }
            }
        }

        if self.ngen_cal_type not in ['calibration', 'validation', 'calibvalid', 'restart']:
            root["output_root"] = os.path.join(self.output_dir, "outputs","div")

        if self.forcing_format == ".nc":
            root["global"]["forcing"] = {
                "path": self.forcing_dir,
                "provider": "NetCDF"
            }

        if "t-route" in self.formulation.lower():
            root["routing"] = {
                "t_route_config_file_with_path": os.path.join(self.config_dir, "troute_config.yaml")
            }

        global_block = {
            "name": "bmi_multi",
            "params": {
                "name": "bmi_multi",
                "model_type_name": "",
                "init_config": "",
                "allow_exceed_end_time": False,
                "fixed_time_step": False,
                "uses_forcing_file": False
            }
        }

        model_type_name = ""
        main_output_variable = ""
        modules = []

        model_type_name = self.formulation.replace(",","_")
        
        if ("CFE" in self.formulation)  and ("PET" in self.formulation):
            #model_type_name = "CFE"
            main_output_variable = "Q_OUT"
            
            modules = [self.get_sloth_block(), self.get_pet_block(var_names_map=True), self.get_cfe_block()]
                
            output_variables = ["RAIN_RATE", "DIRECT_RUNOFF", "INFILTRATION_EXCESS", "NASH_LATERAL_RUNOFF",
                               "DEEP_GW_TO_CHANNEL_FLUX", "SOIL_TO_GW_FLUX", "Q_OUT", "SOIL_STORAGE", "POTENTIAL_ET", "ACTUAL_ET"]
            output_header_fields = ["rain_rate", "direct_runoff", "infiltration_excess", "nash_lateral_runoff",
                                   "deep_gw_to_channel_flux", "soil_to_gw_flux", "q_out", "soil_storage", "PET", "AET"]
        elif "NOM" in self.formulation and "CFE" in self.formulation:
            #model_type_name = "NOM_CFE"
            main_output_variable = "Q_OUT"
            modules = [self.get_sloth_block(), self.get_noah_owp_modular_block(), self.get_cfe_block()]
            output_variables = ["RAIN_RATE", "DIRECT_RUNOFF", "GIUH_RUNOFF", "INFILTRATION_EXCESS", "NASH_LATERAL_RUNOFF",
                               "DEEP_GW_TO_CHANNEL_FLUX", "SOIL_TO_GW_FLUX", "Q_OUT", "SOIL_STORAGE", "POTENTIAL_ET", "ACTUAL_ET"]
            output_header_fields = ["rain_rate", "direct_runoff", "giuh_runoff", "infiltration_excess", "nash_lateral_runoff",
                                   "deep_gw_to_channel_flux", "soil_to_gw_flux", "q_out", "soil_storage", "PET", "AET"]
        elif "NOM" in self.formulation and "CFE" in self.formulation and "PET" in formulation:
            #model_type_name = "NOM_CFE_PET"
            main_output_variable = "Q_OUT"
            modules = [self.get_sloth_block(), self.get_noah_owp_modular_block(), self.get_pet_block(), self.get_cfe_block()]
            output_variables = ["RAIN_RATE", "DIRECT_RUNOFF", "GIUH_RUNOFF", "INFILTRATION_EXCESS", "NASH_LATERAL_RUNOFF",
                               "DEEP_GW_TO_CHANNEL_FLUX", "SOIL_TO_GW_FLUX", "Q_OUT", "SOIL_STORAGE", "POTENTIAL_ET", "ACTUAL_ET"]
            output_header_fields = ["rain_rate", "direct_runoff", "giuh_runoff", "infiltration_excess", "nash_lateral_runoff",
                                   "deep_gw_to_channel_flux", "soil_to_gw_flux", "q_out", "soil_storage", "PET", "AET"]
        elif "NOM" in self.formulation and "LASAM" in self.formulation:
            #model_type_name = "NOM_LASAM"
            main_output_variable = "total_discharge"
            modules = [self.get_sloth_block(), self.get_noah_owp_modular_block(), self.get_lasam_block()]
            output_variables = ["TGS", "precipitation", "potential_evapotranspiration", "actual_evapotranspiration",
                               "soil_storage", "surface_runoff", "giuh_runoff", "groundwater_to_stream_recharge", "percolation",
                               "total_discharge", "infiltration"]
            output_header_fields = ["ground_temperature", "rain_rate", "PET_rate", "actual_ET", "soil_storage", "direct_runoff",
                                   "giuh_runoff", "deep_gw_to_channel_flux", "soil_to_gw_flux", "q_out", "infiltration"]
        elif "PET" in self.formulation and "LASAM" in self.formulation:
            #model_type_name = "PET_LASAM"
            main_output_variable = "total_discharge"
            modules = [self.get_sloth_block(), self.get_pet_block(), self.get_lasam_block()]
            output_variables = ["precipitation", "potential_evapotranspiration", "actual_evapotranspiration",
                               "soil_storage", "surface_runoff", "giuh_runoff", "groundwater_to_stream_recharge", "percolation",
                               "total_discharge", "infiltration"]
            output_header_fields = ["rain_rate", "PET_rate", "actual_ET", "soil_storage", "direct_runoff", "giuh_runoff",
                                   "deep_gw_to_channel_flux", "soil_to_gw_flux", "q_out", "infiltration"]
        elif "NOM" in self.formulation and "TOPMODEL" in self.formulation:
            #model_type_name = "NOM_TOPMODEL"
            main_output_variable = "Qout"
            modules = [self.get_noah_owp_modular_block(), self.get_topmodel_block()]
            output_variables = ["Qout", "soil_water__domain_volume_deficit", "land_surface_water__runoff_mass_flux"]
            output_header_fields = ["qout", "soil_deficit", "direct_runoff"]

        elif "NOM" in self.formulation and "CFE" in self.formulation and "SMP" in self.formulation and "SFT" in self.formulation:
            #model_type_name = "NOM_CFE_SMP_SFT"
            main_output_variable = "Q_OUT"
            modules = [self.get_sloth_block(), self.get_noah_owp_modular_block(), self.get_cfe_block(), self.get_smp_block(), self.get_sft_block()]
            output_variables = ["soil_ice_fraction", "TGS", "RAIN_RATE", "DIRECT_RUNOFF", "GIUH_RUNOFF", "NASH_LATERAL_RUNOFF",
                               "DEEP_GW_TO_CHANNEL_FLUX", "Q_OUT", "SOIL_STORAGE", "POTENTIAL_ET", "ACTUAL_ET", "soil_moisture_fraction", "ice_fraction_schaake"]
            output_header_fields = ["soil_ice_fraction", "ground_temperature", "rain_rate", "direct_runoff", "giuh_runoff", "nash_lateral_runoff",
                                   "deep_gw_to_channel_flux", "q_out", "soil_storage", "PET", "AET", "soil_moisture_fraction", "ice_fraction_schaake"]
            if self.precip_partitioning_scheme == "Xinanjiang":
                output_variables[-1] = "ice_fraction_xinanjiang"
                output_header_fields[-1] = "ice_fraction_xinanjiang"
        elif "NOM" in self.formulation and "LASAM" in self.formulation and "SMP" in self.formulation and "SFT" in self.formulation:
            #model_type_name = "NOM_LASAM_SMP_SFT"
            main_output_variable = "total_discharge"
            modules = [self.get_sloth_block(), self.get_noah_owp_modular_block(), self.get_lasam_block(), self.get_smp_block(), self.get_sft_block()]
            output_variables = ["soil_ice_fraction", "TGS", "precipitation", "potential_evapotranspiration", "actual_evapotranspiration",
                               "soil_storage", "surface_runoff", "giuh_runoff", "groundwater_to_stream_recharge", "percolation", "total_discharge",
                               "infiltration", "soil_moisture_fraction"]
            output_header_fields = ["soil_ice_fraction", "ground_temperature", "rain_rate", "PET_rate", "actual_ET",
                                   "soil_storage", "direct_runoff", "giuh_runoff", "deep_gw_to_channel_flux", "soil_to_gw_flux", "q_out",
                                   "infiltration", "soil_moisture_fraction"]


        assert len(output_variables) == len(output_header_fields)

        global_block["params"]["model_type_name"] = model_type_name
        global_block["params"]["main_output_variable"] = main_output_variable
        global_block["params"]["output_variables"] = output_variables
        global_block["params"]["output_header_fields"] = output_header_fields
        global_block["params"]["modules"] = modules

        root["global"]["formulations"] = [global_block]

        with open(self.realization_file, 'w') as outfile:
            json.dump(root, outfile, indent=4, separators=(", ", ": "), sort_keys=False)



#############################################################################
# module for NOAH-OWP-Modular (NOM) block in the nextgen realization file 
# @param config_dir : input directory of the NOM config files
# @param model_exe : path to NOM executable
# Units and different forcing variables names and their mapping
# Nels script (AORC)         Jason Ducker script    NoahOWP BMI forcing vars names
# APCP_surface [kg/m2/sec]   <-> RAINRATE [mm/sec] <-> PRCPNONC [mm/sec]
# DLWRF_surface [W m-2]      <-> LWDOWN [W m-2]    <-> LWDN [W m-2]
# DSWRF_surface [W m-2]      <-> SWDOWN [W m-2]    <-> SOLDN [W m-2]
# TMP_2maboveground [K]      <-> T2D [K]           <-> SFCTMP
# UGRD_10maboveground [m/s]  <-> U2D [m s-1]       <-> UU [m/s]
# VGRD_10maboveground [m/s]  <-> V2D [m s-1]       <-> VV [m/s]
 # PRES_surface [Pa]         <-> PSFC [Pa]         <-> SFCPRS [Pa]
# SPFH_2maboveground [kg/kg] <-> Q2D [kg kg^-1]    <-> Q2 [kg/kg]
#############################################################################
