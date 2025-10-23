from __future__ import annotations

import typing

from ngen.cal import hookimpl
from hypy.nexus import Nexus
import pandas as pd
import numpy as np

if typing.TYPE_CHECKING:
    from datetime import datetime
    from ngen.cal.model import ModelExec

_workdir: Path | None = None

class Proxy:
    def __init__(self, obj):
        self._proxy_obj = obj

    def set_proxy(self, obj):
        self._proxy_obj = obj

    def __getattribute__(self, name: str):
        if name not in ("_proxy_obj", "set_proxy"):
            return getattr(super().__getattribute__("_proxy_obj"), name)
        return super().__getattribute__(name)

    def __repr__(self):
        return repr(super().__getattribute__("_proxy_obj"))

    def __hash__(self):
        return hash(super().__getattribute__("_proxy_obj"))


class ReadObservedData:
    def __init__(self):
        self.proxy = Proxy(pd.Series())
        self.obs_data_path = None

    @hookimpl
    def ngen_cal_model_configure(self, config: ModelExec) -> None:
        path = config.workdir
        global _workdir
        # HACK: fix this in future
        _workdir = path
        
        self.obs_data_path = config.plugin_settings["read_obs_data"][
            "obs_data_path"
        ]

        start = self.obs_kwargs["start_time"]
        end = self.obs_kwargs["end_time"]

        ds = self._read_observations(self, self.obs_data_path, start, end)
        self.proxy.set_proxy(ds)

    @staticmethod
    def _read_observations(self,
        filename: str, start_time: datetime, end_time: datetime
    ) -> pd.Series:
        # read file

        df = pd.read_csv(filename, usecols=["value_time", "value"])

        df["value_time"] = pd.to_datetime(df["value_time"])
        df.set_index("value_time", inplace=True)

        ds = df.loc[start_time:end_time, "value"].copy()

        ds.rename("obs_flow", inplace=True)

        return ds

    @hookimpl(tryfirst=True)
    def ngen_cal_model_observations(
        self,
        nexus: Nexus,
        start_time: datetime,
        end_time: datetime,
        simulation_interval: pd.Timedelta,
    ) -> pd.Series:
        self.obs_kwargs = {
            "nexus": nexus,
            "start_time": start_time,
            "end_time": end_time,
            "simulation_interval": simulation_interval,
        }

        # `ngen_cal_model_observations` must have already called, so call again and set proxy
        if not self.proxy.empty:
            assert self.obs_data_path is not None, "invariant"
            ds = self._read_observations(self,
                self.obs_data_path, start_time, end_time
            )
            self.proxy.set_proxy(ds)

        return self.proxy
