"""
Description
Preparation for radar processing. Combine individual files from a flight 
to a single file.

SeqIntTime may vary between files, the values are overwritten always!
"""


import numpy as np
import xarray as xr
import os
import datetime
import yaml
import ac3airborne


if __name__ == '__main__':
    
    missing = []
        
    # read list with raw files 
    file = os.environ['PATH_PHD']+'/projects/mirac_processing/settings_yaml/files_raw.yaml'
    with open(file, 'r') as f:
        dct_files = yaml.safe_load(f)
    
    # read identified times of erroneous ze signal
    # due to 89 GHz calibration
    file = os.environ['PATH_PHD']+'/projects/mirac_processing/settings_yaml/measurement_error_times.yaml'
    with open(file, 'r') as f:
        dct_err_cal = yaml.safe_load(f)
        
    # due to surface reflection in first 600 m
    file = os.environ['PATH_PHD']+'/projects/mirac_processing/settings_yaml/surface_reflection_times_heights.yaml'
    with open(file, 'r') as f:
        dct_err_ref = yaml.safe_load(f)
    
    meta = ac3airborne.get_flight_segments()
    #campaigns = ['ACLOUD', 'AFLUX', 'MOSAiC-ACA', 'HALO-AC3']
    campaigns = ['HALO-AC3']
    meta_missions = {}
    for campaign in campaigns:
        meta_missions.update(meta[campaign]['P5'])

    flight_ids = list(meta_missions)
    
    for i_flight_id, flight_id in enumerate(flight_ids):
        
        #if flight_id not in missing:
        #    continue
        
        print('\n'+flight_id)
        
        #%% read meta information of flight
        flight = meta_missions[flight_id]
        t0 = np.datetime64(flight['takeoff'])
        t1 = np.datetime64(flight['landing'])
        
        #%% merge radar data files
        path = os.environ['PATH_SEC']+'/radar_processing/'+flight['mission'].lower()+'/mirac_radar/raw_rpg/'+flight['date'].strftime('%Y/%m/%d/')
        
        chirp_files = dct_files.get(flight_id)
        
        if chirp_files is None:
            continue
    
        for chirp, files in chirp_files.items():

            # for reading raw radar data
            drop_vars = ['ins_elevation', 'ins_azimuth', 'lat', 'lon', 'zsl',
                         'rr', 'rh', 'ta', 'pa', 'wspeed', 'wdir',
                         'source_rr', 'source_rh', 'source_ta', 'source_pa', 
                         'source_wspeed', 'source_wdir', 'SampDur',
                         'samples']
            kwds = dict(decode_times=False, drop_variables=drop_vars)
            
            if len(files) == 1:
                
                ds = xr.open_dataset(path+files[0], **kwds)
                assert ds.alias_flag == 0
                
            elif len(files) > 1:
                
                ds = xr.open_dataset(path+files[0], **kwds)
                assert ds.alias_flag == 0
                
                for file in files[1:]:
                    
                    ds_other = xr.open_dataset(path+file, **kwds)
                    assert ds_other.alias_flag == 0

                    ds = xr.concat([ds, ds_other],
                                   dim='time', data_vars='minimal',
                                   compat='override', coords='minimal')

            else:
                continue
            
            # remove duplicate times and keep the first occurrence
            _, index = np.unique(ds['time'], return_index=True)
            ds = ds.isel(time=index)
            
            # sort times
            ds = ds.sel(time=np.sort(ds.time))
            
            # rewrite time information
            attrs = ds.time.attrs
            attrs.pop('units')
            attrs.pop('comment')
            ds['time'] = [datetime.datetime(2001, 1, 1) + datetime.timedelta(seconds=int(t)) for t in ds['time'].values]
            ds['time'].attrs = attrs
            ds['time'].encoding = {'units': 'seconds since 2001-01-01 00:00:00'}
            
            # reduce to flight time
            print(t0)
            print(t1)
            print(ds.time.values[0])
            print(ds.time.values[-1])
            ds = ds.sel(time=((ds.time >= t0) & (ds.time <= t1)))
            print(ds.time.values[0])
            print(ds.time.values[-1])
            
            # replace -999 by nan
            ds['ze'] = ds['ze'].where(ds['ze'] != -999)
            ds['vm'] = ds['vm'].where(ds['vm'] != -999)
            ds['sw'] = ds['sw'].where(ds['sw'] != -999)
            ds['skew'] = ds['skew'].where(ds['skew'] != -999)
    
            # mask erroneous reflectivities
            dct_err_cal_flight = dct_err_cal.get(flight_id)
            dct_err_ref_flight = dct_err_ref.get(flight_id)  
            
            # after calibration
            if dct_err_cal_flight is not None:
                times = np.array(dct_err_cal_flight['times'])
                for t0_err, t1_err in times:
                    ds['ze'][(np.datetime64(t0_err) <= ds.time) & (ds.time <= np.datetime64(t1_err)), :] = np.nan
                    ds['vm'][(np.datetime64(t0_err) <= ds.time) & (ds.time <= np.datetime64(t1_err)), :] = np.nan
                    ds['sw'][(np.datetime64(t0_err) <= ds.time) & (ds.time <= np.datetime64(t1_err)), :] = np.nan
                    ds['skew'][(np.datetime64(t0_err) <= ds.time) & (ds.time <= np.datetime64(t1_err)), :] = np.nan
            
            # due to surface reflection
            if dct_err_ref_flight is not None:           
                coords = dct_err_ref_flight['coords']
                for t0_ref, r0_ref, t1_ref, r1_ref in coords:
                    ix_t = (np.datetime64(t0_ref) <= ds.time) & (ds.time <= np.datetime64(t1_ref))
                    ix_r = (r0_ref <= ds.range) & (ds.range <= r1_ref)
                    ds['ze'][ix_t, ix_r] = np.nan
                    ds['vm'][ix_t, ix_r] = np.nan
                    ds['sw'][ix_t, ix_r] = np.nan
                    ds['skew'][ix_t, ix_r] = np.nan
            
            # write dataset to file
            outdir = os.environ['PATH_SEC']+'/radar_processing/'+flight['mission'].lower()+'/mirac_radar/raw/'+flight['date'].strftime('%Y/%m/%d/')
            
            if not os.path.exists(outdir):
                os.makedirs(outdir)
            
            outfile = files[0][:-3].replace('_p_5', '') + '_raw' + '.nc'
            
            print('writing: '+outdir+outfile)
            ds.to_netcdf(outdir+outfile)
            