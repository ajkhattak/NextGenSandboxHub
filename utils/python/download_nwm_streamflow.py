import xarray as xr
import requests
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

from dataretrieval import nwis, utils, codes, nldi
import s3fs
import fsspec

#Available data sources are: ['ca_gages', 'census2020-nhdpv2', 'epa_nrsa', 'geoconnex-demo', 'gfv11_pois', 'GRAND', 'HILARRI', 'huc12pp', 'huc12pp_102020', 'nmwdi-st', 'npdes', 'nwisgw', 'nwissite', 'ref_dams', 'ref_gage', 'vigil', 'wade', 'wade_rights', 'wade_timeseries', 'WQP', 'comid']

def get_comid(fid):
    #gdf = nldi.get_features(feature_source="WQP", feature_id=fid)
    gdf = nldi.get_features(feature_source="nwissite", feature_id=fid)
    if gdf.empty:
        raise ValueError(f"No feature found for {fid}")

    comid = int(gdf['comid'][0])

    return comid

def get_gage_name(gage_id):
    if not 'USGS' in gage_id:
        gage_id = 'USGS-'+gage_id
    gdf = nldi.get_features(feature_source="nwissite", feature_id=gage_id)
    gage_name = gdf['name'][0]
    return gage_name

def get_nwm_streamflow(gage_list, start_time, end_time, domain='conus'):
    results = {}
    for g in gage_list:
        print (f"Downloading data for gage: [{g}]")
        df = get_streamflow_per_gage(
            g,
            start_time=start_time,
            end_time=end_time,
            domain=domain
        )
        df.set_index('time', inplace=True)
        gage_name = get_gage_name(g)
        results[g] = {
            'name': gage_name,
            'data': df
        }
    return results

def save_nwm_streamflow(gage_list,
                        start_time,
                        end_time,
                        output_dir,
                        domain='conus',
                        file_format='parquet'  # or 'csv'
                        ):
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for g in gage_list:
        print (f"Downloading data for gage: [{g}]")
        df = get_streamflow_per_gage(
            g,
            start_time=start_time,
            end_time=end_time,
            domain=domain
        )
        
        df.set_index('time', inplace=True)

        file_name = f"gage_{g}_streamflow.{file_format}"
        file_path = output_dir / file_name

        # Write to file
        if file_format == 'csv':
            df.to_csv(file_path)
        elif file_format == 'parquet':
            df.to_parquet(file_path)
        else:
            print(f"Unsupported file format: {file_format}")
            continue

        print(f"Saved: {file_path}")


def get_streamflow_per_gage(gage_id, start_time, end_time, domain):

    #gage_id = "USGS-01052500"
    if not 'USGS' in gage_id:
        gage_id = 'USGS-'+gage_id

    comid = get_comid(gage_id)

    #awspath2 ='https://noaa-nwm-retrospective-2-1-zarr-pds.s3.amazonaws.com/ldasout.zarr'
    if domain.lower() == "conus":
        domain = "CONUS"
    elif domain.lower() == "hi":
        domain = "Hawaii"
    elif domain.lower() == "pr":
        domain = "PR"
    elif domain.lower() == "AK":
        domain = "Alaska"

    awspath3  = f'https://noaa-nwm-retrospective-3-0-pds.s3.amazonaws.com/{domain}/zarr/chrtout.zarr'
    #nwm_url  = 's3://noaa-nwm-retrospective-3-0-pds/CONUS/zarr/chrtout.zarr' # this also works

    fs = s3fs.S3FileSystem(anon=True, requester_pays=True)
    bucket = "noaa-nwm-retrospective-3-0-pds"
    zarr_path = f"{domain}/zarr/chrtout.zarr"
    
    store = fs.get_mapper(f"{bucket}/{zarr_path}")
    ds = xr.open_zarr(store, consolidated=True)
        
    #ds = xr.open_zarr(awspath3,consolidated=True)

    nwm_streamflow = ds['streamflow']

    #nwm_streamflow has dimensions ('time', 'feature_id')
    # slice the time dimension by range of start and end times
    nwm_streamflow = nwm_streamflow.sel(time=slice(start_time, end_time))

    # slice feature_id dimension by comid
    flow_data = nwm_streamflow.sel(feature_id=comid)

    df = pd.DataFrame({
        'time': flow_data.time,
        'flow': flow_data.data
    })

    # time units [hour]
    # flow units [m3 s-1]
    return df

if __name__ == "__main__":

    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("-gid", dest="gage_id",    type=str, required=True,  help="USGS gage ID")
        parser.add_argument("-s",   dest="start_rime", type=str, required=True,  help="start time")
        parser.add_argument("-e",   dest="end_time",   type=str, required=True,  help="end time")
    except:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    get_nwm_streamflow(args.gage_id, args.start_time, args.end_time, "conus")
