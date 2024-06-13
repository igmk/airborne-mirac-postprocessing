"""
Prepare gps and ins data for radar processing

This includes the removal of
  - erroneous values (lat, lon, z)
  - reduction to the necessary variables, which are
    - time, lat, lon, alt, pitch, roll, heading
"""


import os
import xarray as xr
import numpy as np
import ac3airborne
import datetime


if __name__ == '__main__':
    
    path = '/data/obs/campaigns/'
    
    meta = ac3airborne.get_flight_segments()['HALO-AC3']['P5']
    
    for flight_id, flight in meta.items():
        
        print(flight_id)
        
        # this is just quick and dirty workaround for the other path for halo-ac3
        aircraft = ''
        if flight['mission'] == 'HALO-AC3':
            aircraft = '/p5'
        
        file = path+flight['mission'].lower()+aircraft+'/gps_ins/'+flight['date'].strftime('%Y/%m/%d')+\
                             '/'+flight['mission']+'_polar5_gps_ins_'+flight['date'].strftime('%Y%m%d')+'_'+flight['name']+'.nc'    
                             
        ds = xr.open_dataset(file, drop_variables=['lat_dir', 'lon_dir'])
        
        # reduce to flight time
        ds = ds.sel(time=slice(flight['takeoff']-datetime.timedelta(minutes=1), 
                               flight['landing']+datetime.timedelta(minutes=1)))
        
        # create a mask for erroneous values
        mask = (ds['alt'] < 10000) & (ds['alt'] > 0) & \
               (ds['lon'] < 30) & (ds['lon'] > -30) & \
               (ds['lat'] < 89) & (ds['lat'] > 30) & \
               (np.abs(ds['roll']) < 60) & \
               (np.abs(ds['pitch']) < 60) & \
               (np.abs(ds['heading']) < 180)
        
        print(np.sum(~mask))
        
        ds = ds.where(mask)
        
        # make sure, encoding is in seconds since 1970 for the processing
        ds['time'].encoding = dict(units='seconds since 1970-01-01', calendar='standard')
        
        # write file
        outdir = '/net/secaire/nrisse/radar_processing/'+flight['mission'].lower()+'/gps_ins/'+flight['date'].strftime('%Y/%m/%d/')
        
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        
        outfile = 'gps_ins_'+flight['mission']+'_polar5_'+flight['date'].strftime('%Y%m%d')+'_'+flight['name']+'.nc'    
        
        print('writing: '+outdir+outfile)
        ds.to_netcdf(outdir+outfile)
                