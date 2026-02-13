import os
import geopandas as gpd
import json
import pandas as pd

from src.python.registry import register_model
from src.python.configuration import ConfigurationGenerator


@register_model("PET")
class PETConfigurationGenerator(ConfigurationGenerator):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.pet_method = self.ctx.pet_method
        
    def _write_input_files(self, member_id, tag):
        self.write_pet_input_files(member_id=member_id, tag=tag)

    def write_pet_input_files(self, member_id=1, tag="cfg"):

        # ensemble logic
        if self.ctx.ensemble_enabled and "PET" in (self.ctx.ensemble_models or "").upper():
            pass
        elif member_id == 1:
            tag = "cfg"
        else:
            return
        
        pet_dir = os.path.join(self.ctx.output_dir, "configs", "pet")
        self.create_directory(pet_dir,member_id)

        for catID in self.ctx.catids:
            cat_name = "cat-" + str(catID)

            centroid_x = str(self.ctx.gdf["geometry"][cat_name].centroid.x)
            centroid_y = str(self.ctx.gdf["geometry"][cat_name].centroid.y)
            elevation_mean = self.ctx.gdf["elevation_mean"][cat_name]

            veg_type = int(self.ctx.gdf.loc[cat_name]["IVGTYP"])

            if self.ctx.ensemble_enabled or "IVGTYP_nlcd" in self.ctx.gdf.columns:
                veg_type_nlcd = json.loads(self.ctx.gdf.loc[cat_name]['IVGTYP_nlcd'])
                veg_type_nlcd = pd.DataFrame(veg_type_nlcd, columns=['v', 'frequency'])
                veg_type = veg_type_nlcd['v'][member_id - 1]

            veg_height = self.ctx.vegetation_height[veg_type]

            # taken from evapotranpiration repo (see include/PETPenmanMonteithMethod.h)
            zero_plane_displacement = 2.0 / 3.0 * veg_height
            momentum_transfer_roughness_length = 0.1845 * zero_plane_displacement
            heat_transfer_roughness_length = 0.1 * momentum_transfer_roughness_length

            pet_params = [
                "verbose=0",
                f"pet_method={self.ctx.pet_method}",
                "forcing_file=BMI",
                "run_unit_tests=0",
                "yes_aorc=1",
                "yes_wrf=0",
                "wind_speed_measurement_height_m=10.0",
                "humidity_measurement_height_m=2.0",
                f"vegetation_height_m={veg_height}",
                f"zero_plane_displacement_height_m={zero_plane_displacement}",
                f"momentum_transfer_roughness_length={momentum_transfer_roughness_length}",
                f"heat_transfer_roughness_length_m={heat_transfer_roughness_length}",
                "surface_longwave_emissivity=0.965",
                "surface_shortwave_albedo=0.2",
                "cloud_base_height_known=FALSE",
                "time_step_size_s=3600",
                "num_timesteps=1",
                "shortwave_radiation_provided=1",
                f"latitude_degrees={centroid_y}",
                f"longitude_degrees={centroid_x}",
                f"site_elevation_m={elevation_mean}"
            ]

            fname_pet = f"pet_{tag}_{cat_name}.txt"
            pet_file = os.path.join(pet_dir, fname_pet)

            with open(pet_file, "w") as f:
                f.writelines("\n".join(pet_params))
