import os
import sys
import yaml


from src.python.registry import register_model
from src.python.configuration import ConfigurationGenerator

@register_model("CFE-S")
@register_model("CFE-X")
class CFEConfigurationGenerator(ConfigurationGenerator):
    
    def _write_input_files(self, member_id, tag):
        self.write_cfe_input_files(member_id=member_id, tag=tag)
        
    def write_cfe_input_files(self, member_id=1, tag="cfg"):

        if self.ctx.ensemble_enabled and "CFE" in self.ctx.ensemble_models:
            pass
        elif (member_id == 1):
            tag = "cfg"
        else:
            return
        
        cfe_dir = os.path.join(self.ctx.output_dir, "configs/cfe")
        self.create_directory(cfe_dir, member_id)

        cfe_basefile = os.path.join(self.ctx.sandbox_dir, "configs/basefiles/config_cfe.txt")

        if not os.path.exists(cfe_basefile):
            sys.exit(f"Sample CFE config file does not exist, provided is {cfe_basefile}")

        delimiter = ","
        
        # Read infile line by line
        with open(cfe_basefile, 'r') as infile:
            lines = infile.readlines()

        for catID in self.ctx.catids:
            cat_name = 'cat-' + str(catID)
            fname = cat_name + '*.txt'

            fname_cfe = f'cfe_{tag}_{cat_name}.txt'
            
            cfe_file = os.path.join(cfe_dir, fname_cfe)

            with open(cfe_file, 'w') as file:
                for line in lines:
                    if line.startswith("#"):
                        continue
                    if line.strip().startswith('soil_params.b'):
                        if self.ctx.gdf['soil_b'][cat_name] == 1.0:
                            file.write(f'soil_params.b=1.1[]\n')
                        else:
                            file.write(f'soil_params.b={self.ctx.gdf["soil_b"][cat_name]}[]\n')
                    elif line.strip().startswith('soil_params.satdk'):
                        file.write(f'soil_params.satdk={self.ctx.gdf["soil_satdk"][cat_name]}[m s-1]\n')
                    elif line.strip().startswith('soil_params.satpsi'):
                        file.write(f'soil_params.satpsi={self.ctx.gdf["soil_satpsi"][cat_name]}[m]\n')
                    elif line.strip().startswith('soil_params.slop'):
                        file.write(f'soil_params.slop={self.ctx.gdf["soil_slop"][cat_name]}[m/m]\n')
                    elif line.strip().startswith('soil_params.smcmax'):
                        file.write(f'soil_params.smcmax={self.ctx.gdf["soil_smcmax"][cat_name]}[m/m]\n')
                    elif line.strip().startswith('soil_params.wltsmc'):
                        file.write(f'soil_params.wltsmc={self.ctx.gdf["soil_wltsmc"][cat_name]}[m/m]\n')
                    elif line.strip().startswith('soil_params.refkdt'):
                        file.write(f'refkdt={self.ctx.gdf["soil_refkdt"][cat_name]}\n')
                    elif line.strip().startswith('max_gw_storage'):
                        file.write(f'max_gw_storage={self.ctx.gdf["max_gw_storage"][cat_name]}[m]\n')
                    elif line.strip().startswith('Cgw'):
                        file.write(f'Cgw={self.ctx.gdf["Cgw"][cat_name]}[m h-1]\n')
                    elif line.strip().startswith('expon'):
                        file.write(f'expon={self.ctx.gdf["gw_expon"][cat_name]}[]\n')
                    elif line.strip().startswith('surface_runoff_scheme'):
                        surface_runoff_scheme = line.strip().split("=")[1]
                        file.write(line)

                        if surface_runoff_scheme == "GIUH" or surface_runoff_scheme == 1:
                            giuh_cat = json.loads(self.ctx.gdf['giuh'][cat_name])
                            giuh_cat = pd.DataFrame(giuh_cat, columns=['v', 'frequency'])
                            giuh_ordinates = ",".join(str(x) for x in np.array(giuh_cat["frequency"]))
                            file.write(f'giuh_ordinates={giuh_ordinates}\n')
                        elif surface_runoff_scheme == "NASH_CASCADE" or surface_runoff_scheme == 2:
                            file.write(f'N_nash_surface={int(self.ctx.gdf["N_nash_surface"][cat_name])}[]\n')
                            file.write(f'K_nash_surface={self.ctx.gdf["K_nash_surface"][cat_name]}[h-1]\n')
                            s = [str(0.0),] * int(self.ctx.gdf['N_nash_surface'][cat_name])
                            s = delimiter.join(s)
                            file.write(f'nash_storage_surface={s}[]\n')
                            file.write(f'retention_depth_nash_surface=0.0[]\n')

                    elif line.strip().startswith('N_nash_surface') or line.strip().startswith('K_nash_surface') or \
                         line.strip().startswith('nash_storage_surface'):
                        continue
                    elif line.strip().startswith('surface_water_partitioning_scheme'):

                        if "CFE-X" in self.ctx.formulation:
                            self.surface_water_partitioning_scheme = "Xinanjiang"
                            soil_id = self.ctx.gdf['ISLTYP'][cat_name]
                            file.write(f'surface_water_partitioning_scheme={self.surface_water_partitioning_scheme}\n')
                            file.write(f'a_Xinanjiang_inflection_point_parameter={self.ctx.soil_class_NWM["AXAJ"][soil_id]}\n')
                            file.write(f'b_Xinanjiang_shape_parameter={self.ctx.soil_class_NWM["BXAJ"][soil_id]}\n')
                            file.write(f'x_Xinanjiang_shape_parameter={self.ctx.soil_class_NWM["XXAJ"][soil_id]}\n')
                            file.write(f"urban_decimal_fraction={self.ctx.gdf['impervious_mean'][cat_name]}\n")
                            #file.write(f"urban_decimal_fraction=0.0\n")
                        elif "CFE-S" in self.ctx.formulation:
                            self.surface_water_partitioning_scheme = line.strip().split("=")[1]
                            file.write(line)

                    elif line.strip().startswith('a_Xinanjiang_inflection_point_parameter') or \
                         line.strip().startswith('b_Xinanjiang_shape_parameter') or \
                         line.strip().startswith('x_Xinanjiang_shape_parameter'):
                        continue
                    elif line.strip().startswith('sft_coupled'):
                        sft_coupled = line.strip().split("=")[1]
                        if sft_coupled.lower() == "true":
                            ice_content_threshold = 0.3
                            file.write("sft_coupled=true")
                            file.write(f"ice_content_threshold={ice_content_threshold}")
                    else:
                        file.write(line)
                if "SFT" in self.ctx.formulation:
                    ice_content_threshold = 0.3
                    file.write("sft_coupled=true\n")
                    file.write(f"ice_content_threshold={ice_content_threshold}")
