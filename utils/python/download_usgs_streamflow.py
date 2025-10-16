import pandas as pd
from hydrotools.nwis_client.iv import IVDataService

# Retrieve data from a single site
service = IVDataService(
    value_time_label="value_time"
)

cf_per_hr_to_m3_per_hr = 0.0283168
gage_ids = ['10011500', '08070500']
start = '2015-10-01 00:00:00'
end   = '2022-09-30 23:00:00'
cf_per_hr_to_m3_per_hr = 0.028316847
output_dir = "/scratch4/NCEPDEV/ohd/Ahmad.Jan.Khattak/Core/projects/nwm_v4_bm/usgs_obs_streamflow"

def fetch_and_save_hourly_usgs_data(service, gage_id, start, end, cf_per_hr_to_m3_per_hr, output_dir='.'):
    """
    Fetches 15-min USGS streamflow data for a given gage ID, filters to hourly values,
    converts units, and saves to CSV.

    Parameters:
        service:          USGS data service client (e.g., from dataretrieval or ulmo)
        gage_id:          str, USGS site ID (e.g., '10011500')
        start:            str or datetime, start date (e.g., '2015-10-01 00:00:00')
        end:              str or datetime, end date (e.g., '2015-11-01 00:00:00')
        cf_per_hr_to_m3_per_hr: float, conversion factor from ft³/hr to m³/hr
        output_dir:       str, directory to save the CSV file in
    """
    try:
        # Fetch data
        observations_data = service.get(
            sites=gage_id,
            startDT=start,
            endDT=end
        )

        if observations_data.empty:
            print(f"[WARNING] No data returned for site {gage_id}")
            return

        # Parse datetime and convert units
        observations_data['value_time'] = pd.to_datetime(observations_data['value_time'])
        observations_data['value'] = observations_data['value'] * cf_per_hr_to_m3_per_hr

        # Filter to hourly values
        hourly_only = observations_data[
            (observations_data['value_time'].dt.minute == 0) &
            (observations_data['value_time'].dt.second == 0)
        ]

        # Select only value_time and value
        hourly_df = hourly_only[['value_time', 'value']].copy()

        # Save to file
        output_path = f"{output_dir}/gage_{gage_id}_hourly_streamflow.csv"
        hourly_df.to_csv(output_path, index=False)
        print(f"[INFO] Saved hourly data for gage {gage_id} to {output_path}")

    except Exception as e:
        print(f"[ERROR] Failed to fetch/process data for gage {gage_id}: {e}")



for gage_id in gage_ids:
    fetch_and_save_hourly_usgs_data(
        service=service,
        gage_id=gage_id,
        start=start,
        end=end,
        cf_per_hr_to_m3_per_hr=cf_per_hr_to_m3_per_hr,
        output_dir=output_dir)
