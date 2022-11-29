"""
Radar processing

Create yaml file with all raw files and sort them by chirp table

Flights that need to be split manually after running the script
ACLOUD RF06/07:
    - Last file from RF06 is at 110000, first of RF07 at 124515
      
MOSAiC-ACA_P5_RF03+RF04:
    - Last file from RF03 is at 103850, first of RF04 at 111046
      
HALO-AC3_P5_RF02+RF03:
    - Last file from RF02 is at 090000, first of RF03 at 112558

HALO-AC3_P5_RF06+RF07:
    - Last file from RF06 is at 090000, first of RF07 at 120147
"""


import numpy as np
import xarray as xr
import yaml
import ac3airborne
from glob import glob
import os


if __name__ == '__main__':
    
    # path, where radar raw files are stored
    path_data = os.environ['PATH_SEC']+'/radar_processing/'
    
    # get flight id of all campaigns
    meta = ac3airborne.get_flight_segments()
    campaigns = ['ACLOUD', 'AFLUX', 'MOSAiC-ACA', 'HALO-AC3']
    meta_missions = {}
    for campaign in campaigns:
        meta_missions.update(meta[campaign]['P5'])
        
    flight_ids = list(meta_missions)
        
    # output dictionary, where file names will be stored
    dct_files = {}
    
    for flight_id in flight_ids:
        
        print(flight_id)
        flight = meta_missions[flight_id]
                
        # get all radar files from that date
        path = path_data+flight['mission'].lower()+'/mirac_radar/raw_rpg/'+flight['date'].strftime('%Y/%m/%d/')
        files = np.sort(glob(path+'mirac*a_p_5_*_ZEN_v2.0.nc'))
        
        if len(files) == 1:
            
            dct_files[flight_id] = {}
            dct_files[flight_id]['chirp_1'] = [files[0].split('/')[-1]]
            
        elif len(files) > 1:
            
            dct_files[flight_id] = {}
            dct_files[flight_id]['chirp_1'] = [files[0].split('/')[-1]]
            
            # read first file
            ds = xr.open_dataset(files[0], decode_times=False)
            
            i = 1  # counts chirps
            for file in files[1:]:
                
                # read next file
                ds_other = xr.open_dataset(file, decode_times=False)
                
                # check, if the same radar settings apply
                to_check = ['nqv', 'range_offsets']
                same_chirp = np.min([ds[var].values == ds_other[var].values for var in to_check]) == 1
                
                if same_chirp:
                    
                    # append the file name to the same chirp list
                    dct_files[flight_id]['chirp_%i'%i].append(file.split('/')[-1])
                
                else:
                                        
                    i += 1
                    
                    # append the file name to the next chirp list
                    dct_files[flight_id]['chirp_%i'%i] = [file.split('/')[-1]]
                    
                    # make the current file as basis for the next comparison
                    ds = ds_other.copy()
        
        else:
            continue  # no files at all will create no entry in yaml file
        
    with open(os.environ['PATH_PHD']+'/projects/mirac_processing/settings_yaml/files_raw.yaml', 'w') as f:
        yaml.dump(dct_files, f)