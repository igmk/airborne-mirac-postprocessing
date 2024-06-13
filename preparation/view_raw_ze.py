"""
Description
Preparation for radar processing. Combine individual files from a flight 
to a single file.

TODO:
    - conversion to datetime object
    - takeoff and landing
"""


import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import datetime
import collections
import matplotlib.dates as mdates
import yaml
import ac3airborne
from glob import glob
import pandas as pd
import os


if __name__ == '__main__':
    
    # read identified times of erroneous ze signal
    # due to 89 GHz calibration
    file = os.environ['PATH_PHD']+'/projects/mirac_processing/settings_yaml/measurement_error_times.yaml'
    with open(file, 'r') as f:
        dct_err_cal = yaml.safe_load(f)
        
    # due to surface reflection in first 600 m
    file = os.environ['PATH_PHD']+'/projects/mirac_processing/settings_yaml/surface_reflection_times_heights.yaml'
    with open(file, 'r') as f:
        dct_err_ref = yaml.safe_load(f)
        
    meta = ac3airborne.get_flight_segments()['HALO-AC3']['P5']
    
    flight_ids = list(meta)
        
    for flight_id in flight_ids:
        
        print('\n'+flight_id)
        
        #%% read meta information of flight
        flight = meta[flight_id]
        t0 = np.datetime64(flight['takeoff'])
        t1 = np.datetime64(flight['landing'])
        
        #%% read radar data into dict
        path = os.environ['PATH_SEC']+'/radar_processing/'+flight['mission'].lower()+'/mirac_radar/raw_rpg/'+flight['date'].strftime('%Y/%m/%d/')
        
        files = glob(path+'*_ZEN_compact_v2.0.nc')
        files_large = glob(path+'*_ZEN_v2.0.nc')
        
        # make sure, that same amount of large and small files exists
        print(f'Large files: {len(files_large)}, Compact files: {len(files)}')
        
        ds_dct = {}
        for file in files:
        
            ds = xr.open_dataset(file, decode_times=False)
                        
            # remove duplicate times
            _, index = np.unique(ds['time'], return_index=True)
            ds = ds.isel(time=index)
            
            # sort times
            ds = ds.sel(time=np.sort(ds.time))
            
            # replace -999 by nan
            ds['ze'] = ds['ze'].where(ds['ze'] != -999)
        
            # rewrite time information
            ds['time'] = [datetime.datetime(2001, 1, 1) + datetime.timedelta(seconds=int(t)) for t in ds['time'].values]
            
            # calculate measurement interval and save as new variable in dataset
            d_time = (ds.time.values[1:]-ds.time.values[:-1]).astype('int')*1e-9
            ds['d_time'] = (('time'), np.append([0], d_time))
            
            # make continuous time step
            t_cont = pd.date_range(ds.time.values[0], ds.time.values[-1], freq='1S')
            
            ds = ds.reindex({'time': t_cont})
                    
            filename = file.split('/')[-1]
            ds_dct[filename] = ds
            
        # sort dct
        ds_dct = collections.OrderedDict(sorted(ds_dct.items()))
        
        #%% get times
        for filename, ds in ds_dct.items():
            
            print(filename)
            
            # get time of calibration cycle
            t_calib = pd.to_datetime(ds.time[ds.d_time >= 8].values)
            t_end = pd.to_datetime(ds.time[-1].values)
            
            print([t.strftime('%Y-%m-%d %H:%M:%S') for t in t_calib])
            print(t_end.strftime('%Y-%m-%d %H:%M:%S'))
                        
        #%% view data
        # ax_flag: flag of time steps with erroneous data
        # ax_ze: ze including erroneous data
        # ax3: ze with erroneous data set to nan
        
        # substract 30 dB in linear space for the one case  # test
        #case = 'mirac_a_p_5_200911_110000_P04_ZEN_compact_v2.0.nc'      # test    
        #x = -30  # substract dB  # test
        #ds_dct[case]['ze'] = ds_dct[case].ze - 10**(0.1 * x)       # test
        
        fig, (ax_flag, ax_ze, ax_ze_fil, ax_dt) = plt.subplots(4, 1, figsize=(10, 10), sharex=True,
                                            gridspec_kw=dict(height_ratios=[0.05, 1, 1, 0.2]))
        
        fig.suptitle(flight_id+' '+str(flight['date']))
        
        for filename, ds in ds_dct.items():
            
            print(filename)
            
            ax_ze.annotate(filename.split('_')[5], xy=(ds.time.values[0], 1), xycoords=('data', 'axes fraction'),
                         rotation=90)
            
            # plot ze
            # original
            im = ax_ze.pcolormesh(ds.time.values, ds.range, 10*np.log10(ds.ze.T), 
                                  cmap='magma', vmin=-30, vmax=10,
                                  shading='nearest')
            
            # filtered for errors
            ds['ze_filtered'] = ds['ze'].copy()
            
            dct_err_cal_flight = dct_err_cal.get(flight_id)
            dct_err_ref_flight = dct_err_ref.get(flight_id)            
            
            # calibration-induced errors
            if dct_err_cal_flight is not None:
                
                times = np.array(dct_err_cal_flight['times'])
                
                for t0_cal, t1_cal in times:
                    ds['ze_filtered'][(np.datetime64(t0_cal) <= ds.time) & (ds.time <= np.datetime64(t1_cal)), :] = np.nan
            
            # surface reflection induced errors
            if dct_err_ref_flight is not None:
                                
                coords = dct_err_ref_flight['coords']
                
                for t0_ref, r0_ref, t1_ref, r1_ref in coords:
                    
                    ix_t = (np.datetime64(t0_ref) <= ds.time) & (ds.time <= np.datetime64(t1_ref))
                    ix_r = (r0_ref <= ds.range) & (ds.range <= r1_ref)
                    
                    ds['ze_filtered'][ix_t, ix_r] = np.nan
            
            # plot filtered radar reflectivity (or original, if no filter applied)
            im = ax_ze_fil.pcolormesh(ds.time.values, ds.range, 10*np.log10(ds.ze_filtered.T), 
                                      cmap='magma', vmin=-30, vmax=10, shading='nearest')
            
            ax_dt.scatter(ds.time.values, ds.d_time)
            
        ax_dt.set_xlabel('Time')
        ax_ze.set_ylabel('Range [m]')
        ax_ze_fil.set_ylabel('Range [m]')
        ax_dt.set_ylabel('Time between\nmeasurements [s]')
        
        # mark takeoff and landing
        ax_dt.axvline(t0)
        ax_dt.axvline(t1)
        
        ax_ze.set_ylim(4000, 0)
        ax_ze_fil.set_ylim(4000, 0)
        
        fig.colorbar(im, ax=[ax_ze, ax_ze_fil], label='Ze [dBZ]', orientation='horizontal', shrink=0.5)
        
        # plot identified times with errorneous signal
        # calibration error
        dct_err_cal_flight = dct_err_cal.get(flight_id)
        if dct_err_cal_flight is not None:
            times = np.array(dct_err_cal_flight['times'])
            for t0_cal, t1_cal in times:
                ax_flag.plot([t0_cal, t1_cal], [0, 0], color='red', linewidth=10)
                ax_ze.fill_betweenx(y=[0, 4000], x1=t0_cal, x2=t1_cal, color='gray', alpha=0.5,
                                  edgecolor=None)
        
        # surface reflection error
        dct_err_ref_flight = dct_err_ref.get(flight_id)
        if dct_err_ref_flight is not None:
            coords = dct_err_ref_flight['coords']
            for t0_ref, r0_ref, t1_ref, r1_ref in coords:
                ax_flag.plot([t0_ref, t1_ref], [0, 0], color='orange', linewidth=5)
                ax_ze.fill_betweenx(y=[r0_ref, r1_ref], x1=t0_ref, x2=t1_ref, color='pink', alpha=0.5,
                                  edgecolor=None)
                
        ax_flag.axis('off')
        
        # save as hourly plots
        time_steps = pd.date_range(pd.to_datetime(t0).floor('30min'), 
                                   pd.to_datetime(t1).ceil('30min'), 
                                   freq='30min')
        
        #time_steps = time_steps[6:8]  # test
        
        for i in range(len(time_steps)-1):
            
            # get start and end time
            t00 = time_steps[i]
            t11 = time_steps[i+1]
                        
            ax_dt.set_xlim(t00, t11)
            
            # date axis format
            for ax in (ax_ze_fil, ax_dt):
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                ax.xaxis.set_minor_locator(mdates.MinuteLocator())
                ax.grid()
            
            # save to file
            time_str = t00.strftime('%Y%m%d_%H%M')
            file = flight_id+'_'+time_str+'.png'
            plt.savefig(os.environ['PATH_PHD']+'/projects/mirac_processing/plots/radar_quicklook_30min/'+flight['mission'].lower()+'/'+file, 
                        dpi=300)
            
        #%%
        plt.close('all')
