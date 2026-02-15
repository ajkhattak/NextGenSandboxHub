import os
import sys
import yaml
import pandas as pd

from src.python.registry import register_model
from src.python.configuration import ConfigurationGenerator

@register_model("LSTM")
class LSTMConfigurationGenerator(ConfigurationGenerator):

    def _write_input_files(self, member_id, tag):
        self.write_lstm_input_files(member_id=member_id, tag=tag)


    def write_lstm_input_files_train1(self, member_id=1, tag="cfg"):
        lstm_dir = os.path.join(self.ctx.output_dir, "configs", "lstm")
        self.create_directory(lstm_dir)

        lstm_basefile = os.path.join(
            self.ctx.sandbox_dir,
            "configs",
            "basefiles",
            "config_lstm.yaml"
        )

        if not os.path.exists(lstm_basefile):
            raise FileNotFoundError(
                f"Sample LSTM config file does not exist: {lstm_basefile}"
            )

        with open(lstm_basefile, "r") as f:
            base_file = yaml.safe_load(f)

        train_cfg_path = os.path.normpath(
            os.path.join(
                self.ctx.sandbox_dir,
                "extern",
                "lstm",
                base_file.get("train_cfg_file"),
            )
        )

        gpkg_name = os.path.basename(self.ctx.gpkg_file).split(".")[0]
        gage_id = gpkg_name.split("_")[1]

        for catID in self.ctx.catids:
            cat_name = f"cat-{catID}"
            fname = f"lstm_config_{cat_name}.yaml"

            centroid = self.ctx.gdf.loc[cat_name, "geometry"].centroid

            config = {
                "train_cfg_file": train_cfg_path,
                "area_sqkm": float(self.gdf.loc[cat_name, "divide_area"]),
                "basin_id": gage_id,
                "elev_mean": float(self.gdf.loc[cat_name, "elevation_mean"]),
                "slope_mean": float(self.gdf.loc[cat_name, "terrain_slope"]),
                "lat": float(centroid.y),
                "lon": float(centroid.x),
                "verbose": 0,
                "time_step": "1 hour",
                "initial_state": "zero",
            }

            with open(os.path.join(lstm_dir, fname), "w") as f:
                yaml.dump(config, f, sort_keys=False)

    def write_lstm_input_files(self, member_id=1, tag="cfg"):

        if self.ctx.ensemble_enabled and "LSTM" in self.ctx.ensemble_models:
            pass
        elif (member_id == 1):
            tag = "cfg"
        else:
            return
        
        lstm_dir = os.path.join(self.ctx.output_dir, "configs", "lstm")
        self.create_directory(lstm_dir)

        lstm_basefile = os.path.join(
            self.ctx.sandbox_dir,
            "configs",
            "basefiles",
            "config_lstm.yaml"
        )

        if not os.path.exists(lstm_basefile):
            raise FileNotFoundError(
                f"Sample LSTM config file does not exist: {lstm_basefile}"
            )

        with open(lstm_basefile, "r") as f:
            base_file = yaml.safe_load(f)

        train_cfg_path = os.path.normpath(
            os.path.join(
                self.ctx.sandbox_dir,
                "extern",
                "lstm",
                base_file.get("train_cfg_file"),
            )
        )

        attributes_file = base_file.get("attributes_file")
        df_attr_div  = pd.read_parquet(attributes_file)
        df_attr_div = df_attr_div.set_index("divide_id")

        with open(train_cfg_path, "r") as f:
            train_cfg = yaml.safe_load(f)
            
        static_attributes = train_cfg['static_attributes']

        gpkg_name = os.path.basename(self.ctx.gpkg_file).split(".")[0]
        gage_id = gpkg_name.split("_")[1]

        for catID in self.ctx.catids:
            cat_name = f"cat-{catID}"
            
            fname_lstm = f'lstm_{tag}_{cat_name}.yaml'
            lstm_file = os.path.join(lstm_dir, fname_lstm)
            
            if cat_name not in df_attr_div.index:
                raise KeyError(f"{cat_name} not found in attributes parquet")

            centroid = self.ctx.gdf.loc[cat_name, "geometry"].centroid
            """
            # works when names in the training and .parquet files are consistent
            attr_row = df_attr_div.loc[cat_name]

            static_attr_values = {
                attr: float(attr_row[attr])
                for attr in static_attributes
                if attr in attr_row
            }

            config = {
                "train_cfg_file": train_cfg_path,
                "basin_id": gage_id,
                "verbose": 0,
                "time_step": "1 hour",
                "initial_state": "zero",
                **static_attr_values
            }
            """
            config = {
                "train_cfg_file": train_cfg_path,
                "basin_id": gage_id,
                "verbose": 0,
                "time_step": "1 hour",
                "initial_state": "zero",
                "ari_ix_mean" : float(df_attr_div.loc[cat_name]["ari_ix_mean"]),
                "slp_dg_mean" : float(df_attr_div.loc[cat_name]["slp_dg_mean"]),
                "centroid_y"  : float(df_attr_div.loc[cat_name]["lat_dec_deg"]),
                "ims_pc_mean" : float(df_attr_div.loc[cat_name]["ims_pc_mean"]),
                "ele_mt_mean" : float(df_attr_div.loc[cat_name]["ele_mt_mean"]),
                "snd_pct"     : float(df_attr_div.loc[cat_name]["snd_pct"]),
                "cly_pct"     : float(df_attr_div.loc[cat_name]["cly_pct"]),
                "lka_pc_sse"  : float(df_attr_div.loc[cat_name]["lka_pc_sse"]),
                "areasqkm"    : float(df_attr_div.loc[cat_name]["areasqkm"]),
                "for_pc_forest_sse" : float(df_attr_div.loc[cat_name]["for_pc_forest"]),
            }


            with open(lstm_file, "w") as f:
                yaml.dump(config, f, sort_keys=False)

