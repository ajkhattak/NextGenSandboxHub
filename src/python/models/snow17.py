import os
import sys

from src.python.registry import register_model
from src.python.configuration import ConfigurationGenerator


@register_model("SNOW17")
class SNOW17ConfigurationGenerator(ConfigurationGenerator):

    def _write_input_files(self, member_id, tag):
        self.write_snow17_input_files(member_id=member_id, tag=tag)

    def write_snow17_input_files(self, member_id=1, tag="cfg"):

        # ensemble logic
        if self.ctx.ensemble_enabled and "SNOW17" in (self.ctx.ensemble_models or "").upper():
            pass
        elif member_id == 1:
            tag = "cfg"
        else:
            return

        snow17_dir = os.path.join(self.ctx.output_dir, "configs", "snow17")
        self.create_directory(snow17_dir)

        snow17_basefile = os.path.join(
            self.ctx.sandbox_dir,
            "configs/basefiles/config_snow17.namelist.input"
        )

        snow17_param_basefile = os.path.join(
            self.ctx.sandbox_dir,
            "configs/basefiles/snow17_params_cat.txt"
        )

        if not os.path.exists(snow17_basefile):
            sys.exit(f"Sample Snow17 config file does not exist: {snow17_basefile}")

        # Read all lines from the base template
        with open(snow17_basefile, "r") as infile:
            lines = infile.readlines()

        with open(snow17_param_basefile, "r") as infile_param:
            lines_param = infile_param.readlines()

        for catID in self.ctx.catids:
            cat_name = f"cat-{catID}"
            fname_snow17 = f"snow17_{tag}_{cat_name}.namelist.input"
            fname_snow17_param = f"snow17_params_{tag}_{cat_name}.txt"

            snow17_file = os.path.join(snow17_dir, fname_snow17)
            snow17_param_file = os.path.join(snow17_dir, fname_snow17_param)

            with open(snow17_file, "w") as outfile:
                for line in lines:

                    if line.strip().startswith("!"):
                        outfile.write(line)
                        continue

                    # Replace parameters
                    if line.strip().startswith("main_id"):
                        outfile.write(f'main_id             = "{cat_name}"     ! basin label or gage id\n')
                    elif line.strip().startswith("forcing_root"):
                        outfile.write(f'forcing_root        = "{self.ctx.forcing_dir}"\n')
                    elif line.strip().startswith("output_root"):
                        outfile.write(f'output_root         = "{self.ctx.output_dir}/output"\n')
                    elif line.strip().startswith("snow17_param_file"):
                        outfile.write(f'snow17_param_file   = "{snow17_param_file}"\n')
                    else:
                        outfile.write(line)

            area = self.ctx.gdf["divide_area"][cat_name]
            centroid_y = str(self.ctx.gdf["geometry"][cat_name].centroid.y)
            elevation_mean = self.ctx.gdf["elevation_mean"][cat_name]

            # write param files
            with open(snow17_param_file, "w") as outfile_param:
                for line in lines_param:

                    if line.strip().startswith("!"):
                        outfile_param.write(line)
                        continue

                    # Replace parameters
                    if line.strip().startswith("hru_id"):
                        outfile_param.write(f"hru_id {cat_name}\n")
                    elif line.strip().startswith("hru_area"):
                        outfile_param.write(f"hru_area {area}\n")
                    elif line.strip().startswith("latitude"):
                        outfile_param.write(f"latitude {centroid_y}\n")
                    elif line.strip().startswith("elev"):
                        outfile_param.write(f"elev {elevation_mean}\n")
                    else:
                        outfile_param.write(line)
