"""
Read calibration parameters for every research flight
"""


from glob import glob
import yaml
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


#%% Level 1a
files = glob(os.environ['PATH_PHD']+'/projects/mirac_processing/airborne-mirac-correction/setup/lev_1a/*/setup_lev_1a_*.calibrated.txt')

df_cal = pd.DataFrame()

for file in files:
    
    flight_id = file.split('.calibrated')[0].split('setup_lev_1a_')[1]
    
    with open(file, 'r') as f:
        s = yaml.safe_load(f)
    
    # extract parameters from file
    df_cal.loc[flight_id, 'azimuth'] = float(s['payload_sensor_azimuth_deg'].split(', ')[0])
    df_cal.loc[flight_id, 'viewing'] = float(s['payload_sensor_view_angle_deg'].split(', ')[0])
    df_cal.loc[flight_id, 't_pos'] = float(s['time_offset_position_sensor'].split(', ')[0])
    df_cal.loc[flight_id, 't_att'] = float(s['time_offset_attitude_sensor'].split(', ')[0])


fig, axes = plt.subplots(4, 1, figsize=(10, 8), sharex=True, constrained_layout=True)

x = np.arange(0, len(df_cal.index))

axes[0].scatter(x, df_cal.azimuth)
axes[0].axhline(180)
axes[0].set_ylabel('Azimuth [°]')

axes[1].scatter(x, df_cal.viewing)
axes[1].axhline(25)
axes[1].set_ylabel('Viewing [°]')

axes[2].scatter(x, df_cal.t_pos)
axes[2].axhline(0)
axes[2].set_ylabel('t pos [s]')

axes[3].scatter(x, df_cal.t_att)
axes[3].axhline(0)
axes[3].set_ylabel('t att [s]')

axes[3].set_xticks(x)
axes[3].set_xticklabels(df_cal.index.values, rotation=90)

# detect erroneous calibrations
ds_cal = df_cal.to_xarray()
outlier = ((ds_cal - ds_cal.mean()) > 2*df_cal.std())
weird = ds_cal.index.sel(index=np.sum(np.array([outlier[var].values for var in list(outlier)]), axis=0) > 0).values

axes[0].scatter(x[np.isin(df_cal.index, weird)], df_cal.azimuth[weird])
axes[0].axhline(180)
axes[0].set_ylabel('Azimuth [°]')

axes[1].scatter(x[np.isin(df_cal.index, weird)], df_cal.viewing[weird])
axes[1].axhline(25)
axes[1].set_ylabel('Viewing [°]')

axes[2].scatter(x[np.isin(df_cal.index, weird)], df_cal.t_pos[weird])
axes[2].axhline(0)
axes[2].set_ylabel('t pos [s]')

axes[3].scatter(x[np.isin(df_cal.index, weird)], df_cal.t_att[weird])
axes[3].axhline(0)
axes[3].set_ylabel('t att [s]')

print(weird)

#%% level 2
files = glob(os.environ['PATH_PHD']+'/projects/mirac_processing/airborne-mirac-correction/setup/lev_2/*/setup_lev_2_*.calibrated.txt')

df_cal = pd.DataFrame()

for file in files:
    
    flight_id = file.split('.calibrated')[0].split('setup_lev_2_')[1]
    
    with open(file, 'r') as f:
        s = yaml.safe_load(f)
    
    # extract parameters from file
    df_cal.loc[flight_id, 'fwhm'] = float(s['beam_fwhm_deg'].split(', ')[0])

fig, ax = plt.subplots(1, 1, figsize=(10, 8), sharex=True, constrained_layout=True)

x = np.arange(0, len(df_cal.index))

ax.scatter(x, df_cal.fwhm)
ax.axhline(1.1)
ax.set_ylabel('FWHM [°]')

ax.set_xticks(x)
ax.set_xticklabels(df_cal.index.values, rotation=90)
