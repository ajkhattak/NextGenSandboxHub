import os
import subprocess
import json
import numpy as np
import pandas as pd

from src.python.registry import register_model
from src.python.configuration import ConfigurationGenerator


@register_model("CASAM")
class CASAMConfigurationGenerator(ConfigurationGenerator):

    def _write_input_files(self, member_id, tag):
        self.write_casam_input_files(member_id=member_id, tag=tag)

    def write_casam_input_files(self,
                                sft_coupled=False,
                                member_id=1,
                                tag="cfg"):

        # ensemble logic
        if self.ctx.ensemble_enabled and "CASAM" in (self.ctx.ensemble_models or "").upper():
            pass
        elif member_id == 1:
            tag = "cfg"
        else:
            return

        casam_dir = os.path.join(self.ctx.output_dir, "configs", "casam")
        self.create_directory(casam_dir)

        casam_params_file = os.path.join(
            self.ctx.ngen_dir,
            "extern/CASAM/CASAM/data/vG_params_stat_nom_ordered.dat"
        )

        # copy params file
        str_sub = f"cp -r {casam_params_file} {casam_dir}"
        subprocess.call(str_sub, shell=True)

        sft_calib = "False"
        soil_z = "10.0,15.0,18.0,23.0,29.0,36.0,44.0,55.0,69.0,86.0,107.0,134.0,166.0,207.0,258.0,322.0,401.0,500.0,600.0"

        casam_params_base = [
            'verbosity=none',
            f'soil_params_file={casam_params_file}',
            'layer_thickness=200.0[cm]',
            'initial_psi=2000.0[cm]',
            'timestep=3600[sec]',
            'endtime=1000000000.0[d]',
            'forcing_resolution=3600[sec]',
            'ponded_depth_max=0[cm]',
            'use_closed_form_G=true',
            'layer_soil_type=',
            'max_valid_soil_types=25',
            'wilting_point_psi=15495.0[cm]',
            'field_capacity_psi=340.9[cm]',
            'adaptive_timestep=true',
            'giuh_ordinates=',
            'a=0.0001',
            'b=3.0',
            'frac_to_GW=0.4',
            'PET_affects_precip=false',
            'spf_factor=0.6',
            'free_drainage_enabled=true',
            'allow_flux_caching=true',
            'calib_params=true',
            'log_mode=true'
        ]

        if sft_coupled:
            casam_params_base.append("sft_coupled=true")
            casam_params_base.append(f"soil_z={soil_z}[cm]")

        if sft_coupled and (sft_calib in ["true", "True"]):
            casam_params_base.append("calib_params=true")

        if self.ctx.ngen_cal_type in ["calibration", "validation", "restart"]:
            casam_params_base.append("calib_params=true")

        soil_type_loc = casam_params_base.index("layer_soil_type=")
        giuh_loc_id = casam_params_base.index("giuh_ordinates=")

        for catID in self.ctx.catids:
            cat_name = "cat-" + str(catID)

            casam_params = casam_params_base.copy()
            casam_params[soil_type_loc] += str(self.ctx.gdf["ISLTYP"][cat_name])

            giuh_cat = json.loads(self.ctx.gdf["giuh"][cat_name])
            giuh_cat = pd.DataFrame(giuh_cat, columns=["v", "frequency"])

            giuh_ordinates = ",".join(str(x) for x in np.array(giuh_cat["frequency"]))

            any_nans = np.any(np.isnan(giuh_cat["frequency"]))
            if any_nans:
                giuh_ordinates = "1.0"

            casam_params[giuh_loc_id] += giuh_ordinates

            fname_casam = f"casam_{tag}_{cat_name}.txt"
            casam_file = os.path.join(casam_dir, fname_casam)

            with open(casam_file, "w") as f:
                f.writelines("\n".join(casam_params))
