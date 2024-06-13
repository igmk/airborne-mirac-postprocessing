

import yaml
import ac3airborne
import os
from copy import deepcopy
from glob import glob
import datetime


meta_all = ac3airborne.get_flight_segments()
campaigns = ['ACLOUD', 'AFLUX', 'MOSAiC-ACA', 'HALO-AC3']
meta = {}
for campaign in campaigns:
    meta.update(meta_all[campaign]['P5'])

#%% preparation of calibration times
# write an empty file with takeoff and landing times
dct = {}
for flight_id, flight in meta.items():
    dct[flight_id] = [flight['takeoff'], flight['landing']]

with open(os.environ['PATH_PHD']+'/projects/mirac_processing/settings_yaml/calibration_times_empty.yaml', 'w') as f:
    yaml.dump(dct, f)

#%% lev_1a.calibrate
# read the file with the times and store it as a lev_1a.calibrate setup file
# template of setup file
file = os.environ['PATH_PHD']+'/projects/mirac_processing/airborne-mirac-correction/setup/templates/setup_lev_1a.calibrate.txt'
with open(file, 'r') as f:
    lev_1a_cal_template = f.read()

# read the defined times for each research flight
file = os.environ['PATH_PHD']+'/projects/mirac_processing/settings_yaml/calibration_times.yaml'
with open(file, 'r') as f:
    dct_times = yaml.safe_load(f)

# replace the time in the setup file and store one setup file per flight
for flight_id, times in dct_times.items():
    
    flight = meta[flight_id]
    
    lev_1a_cal = deepcopy(lev_1a_cal_template)
    
    lev_1a_cal = lev_1a_cal.replace("path_base_in : /net/secaire/nrisse/radar_processing/acloud/mirac_radar", 
                            "path_base_in : /net/secaire/nrisse/radar_processing/%s/mirac_radar"%flight['mission'].lower())

    lev_1a_cal = lev_1a_cal.replace("path_base_ins : /net/secaire/nrisse/radar_processing/acloud/gps_ins", 
                            "path_base_ins : /net/secaire/nrisse/radar_processing/%s/gps_ins"%flight['mission'].lower())

    lev_1a_cal = lev_1a_cal.replace("research_flight : 'RF04'", 
                            "research_flight : '%s'"%flight['name'])
    
    lev_1a_cal = lev_1a_cal.replace("campaign : 'ACLOUD'", 
                            "campaign : '%s'"%flight['mission'])

    lev_1a_cal = lev_1a_cal.replace("year_beg : 2017", times[0].strftime("year_beg : %Y"))
    lev_1a_cal = lev_1a_cal.replace("month_beg :   5", times[0].strftime("month_beg : %-m"))
    lev_1a_cal = lev_1a_cal.replace("day_beg :    23", times[0].strftime("day_beg : %-d"))
    lev_1a_cal = lev_1a_cal.replace("hour_beg :    0", times[0].strftime("hour_beg : %-H"))
    lev_1a_cal = lev_1a_cal.replace("minute_beg :  0", times[0].strftime("minute_beg : %-M"))
    lev_1a_cal = lev_1a_cal.replace("second_beg :  0", times[0].strftime("second_beg : %-S"))
    
    lev_1a_cal = lev_1a_cal.replace("year_end : 2017", times[1].strftime("year_end : %Y"))
    lev_1a_cal = lev_1a_cal.replace("month_end :   5", times[1].strftime("month_end : %-m"))
    lev_1a_cal = lev_1a_cal.replace("day_end :    24", times[1].strftime("day_end : %-d"))
    lev_1a_cal = lev_1a_cal.replace("hour_end :    0", times[1].strftime("hour_end : %-H"))
    lev_1a_cal = lev_1a_cal.replace("minute_end :  0", times[1].strftime("minute_end : %-M"))
    lev_1a_cal = lev_1a_cal.replace("second_end :  0", times[1].strftime("second_end : %-S"))
          
    file_lev_1a_cal = os.environ['PATH_PHD']+'/projects/mirac_processing/airborne-mirac-correction/setup/lev_1a/'+flight['mission'].lower()+'/setup_lev_1a_'+flight_id+'.calibrate.txt'
    with open(file_lev_1a_cal, 'w') as f:
        f.write(lev_1a_cal)
        
#%% lev_1a
# read the file with the calibrated values and store the calibrated value in the lev_1a setup file
# template of lev_1a setup file
file = os.environ['PATH_PHD']+'/projects/mirac_processing/airborne-mirac-correction/setup/templates/setup_lev_1a.txt'
with open(file, 'r') as f:
    lev_1a_template = f.read()

# read all lev_1a calibrated files
files = glob(os.environ['PATH_PHD']+'/projects/mirac_processing/airborne-mirac-correction/setup/lev_1a/*/setup_lev_1a_*.calibrated.txt')
    
# one setup file is created for every research flight
# different chirp settings are treated one after another from the calibration
# different flights on the same day need special treatment
# here, one has to make sure that the beginning and end time are selected such
# that the file is read. not just simply takeoff and landing, because it depends
# on the file name. maybe start with one hour before takeoff and after landing
# for this selection.

for file in files:
    
    # get flight_id from filename
    flight_id = file.split('setup_lev_1a_')[1].split('.calibrated')[0]
    
    flight = meta[flight_id]
    
    lev_1a = deepcopy(lev_1a_template)
    
    lev_1a = lev_1a.replace("path_base_in : /net/secaire/nrisse/radar_processing/acloud/mirac_radar", 
                            "path_base_in : /net/secaire/nrisse/radar_processing/%s/mirac_radar"%flight['mission'].lower())

    lev_1a = lev_1a.replace("path_base_ins : /net/secaire/nrisse/radar_processing/acloud/gps_ins", 
                            "path_base_ins : /net/secaire/nrisse/radar_processing/%s/gps_ins"%flight['mission'].lower())

    lev_1a = lev_1a.replace("path_base_dropsondes : /net/secaire/nrisse/radar_processing/acloud/dropsondes", 
                            "path_base_dropsondes : /net/secaire/nrisse/radar_processing/%s/dropsondes"%flight['mission'].lower())
    
    lev_1a = lev_1a.replace("path_base_out : /net/secaire/nrisse/radar_processing/acloud/mirac_radar", 
                            "path_base_out : /net/secaire/nrisse/radar_processing/%s/mirac_radar"%flight['mission'].lower())
    
    lev_1a = lev_1a.replace("research_flight : 'RF04'", 
                            "research_flight : '%s'"%flight['name'])
    
    lev_1a = lev_1a.replace("campaign : 'ACLOUD'", 
                            "campaign : '%s'"%flight['mission'])
    
    times = [flight['takeoff'], flight['landing']]
    times[0] = times[0]-datetime.timedelta(hours=1)
    times[1] = times[1]+datetime.timedelta(hours=1)    
    
    lev_1a = lev_1a.replace("year_beg : 2017", times[0].strftime("year_beg : %Y"))
    lev_1a = lev_1a.replace("month_beg :   5", times[0].strftime("month_beg : %-m"))
    lev_1a = lev_1a.replace("day_beg :    23", times[0].strftime("day_beg : %-d"))
    lev_1a = lev_1a.replace("hour_beg :    0", times[0].strftime("hour_beg : %-H"))
    lev_1a = lev_1a.replace("minute_beg :  0", times[0].strftime("minute_beg : %-M"))
    lev_1a = lev_1a.replace("second_beg :  0", times[0].strftime("second_beg : %-S"))
    
    lev_1a = lev_1a.replace("year_end : 2017", times[1].strftime("year_end : %Y"))
    lev_1a = lev_1a.replace("month_end :   5", times[1].strftime("month_end : %-m"))
    lev_1a = lev_1a.replace("day_end :    24", times[1].strftime("day_end : %-d"))
    lev_1a = lev_1a.replace("hour_end :    0", times[1].strftime("hour_end : %-H"))
    lev_1a = lev_1a.replace("minute_end :  0", times[1].strftime("minute_end : %-M"))
    lev_1a = lev_1a.replace("second_end :  0", times[1].strftime("second_end : %-S"))
    
    # replace the calibrated parameters
    # get calibration parameters
    with open(file, 'r') as f:
        s = yaml.safe_load(f)
    
    # extract parameters from file
    azi = float(s['payload_sensor_azimuth_deg'].split(', ')[0])
    view = float(s['payload_sensor_view_angle_deg'].split(', ')[0])
    t_pos = float(s['time_offset_position_sensor'].split(', ')[0])
    t_att = float(s['time_offset_attitude_sensor'].split(', ')[0])
    
    # replace
    lev_1a = lev_1a.replace("payload_sensor_azimuth_deg : 177.", 
                            "payload_sensor_azimuth_deg : %f"%azi)
    lev_1a = lev_1a.replace("payload_sensor_view_angle_deg : 25.", 
                            "payload_sensor_view_angle_deg : %f"%view)
    lev_1a = lev_1a.replace("time_offset_position_sensor : 0.1", 
                            "time_offset_position_sensor : %f"%t_pos)
    lev_1a = lev_1a.replace("time_offset_attitude_sensor : 0.1", 
                            "time_offset_attitude_sensor : %f"%t_att)
    
    file_lev_1a = os.environ['PATH_PHD']+'/projects/mirac_processing/airborne-mirac-correction/setup/lev_1a/'+flight['mission'].lower()+'/setup_lev_1a_'+flight_id+'_after_cal.txt'
    with open(file_lev_1a, 'w') as f:
        f.write(lev_1a)
        
#%% lev_2.calibrate
# just use the same times as defined for the lev_1a calibration and see the result
# read the file with the times and store it as a lev_2.calibrate setup file
# template of setup file
file = os.environ['PATH_PHD']+'/projects/mirac_processing/airborne-mirac-correction/setup/templates/setup_lev_2.calibrate.txt'
with open(file, 'r') as f:
    lev_2_cal_template = f.read()

# read the defined times for each research flight
file = os.environ['PATH_PHD']+'/projects/mirac_processing/settings_yaml/calibration_times.yaml'
with open(file, 'r') as f:
    dct_times = yaml.safe_load(f)

# replace the time in the setup file and store one setup file per flight
for flight_id, times in dct_times.items():
    
    flight = meta[flight_id]
    
    lev_2_cal = deepcopy(lev_2_cal_template)
    
    lev_2_cal = lev_2_cal.replace("path_base_in : /net/secaire/nrisse/radar_processing/acloud/mirac_radar", 
                                  "path_base_in : /net/secaire/nrisse/radar_processing/%s/mirac_radar"%flight['mission'].lower())
    
    lev_2_cal = lev_2_cal.replace("year_beg : 2017", times[0].strftime("year_beg : %Y"))
    lev_2_cal = lev_2_cal.replace("month_beg :   5", times[0].strftime("month_beg : %-m"))
    lev_2_cal = lev_2_cal.replace("day_beg :    23", times[0].strftime("day_beg : %-d"))
    lev_2_cal = lev_2_cal.replace("hour_beg :    0", times[0].strftime("hour_beg : %-H"))
    lev_2_cal = lev_2_cal.replace("minute_beg :  0", times[0].strftime("minute_beg : %-M"))
    lev_2_cal = lev_2_cal.replace("second_beg :  0", times[0].strftime("second_beg : %-S"))
    
    lev_2_cal = lev_2_cal.replace("year_end : 2017", times[1].strftime("year_end : %Y"))
    lev_2_cal = lev_2_cal.replace("month_end :   5", times[1].strftime("month_end : %-m"))
    lev_2_cal = lev_2_cal.replace("day_end :    24", times[1].strftime("day_end : %-d"))
    lev_2_cal = lev_2_cal.replace("hour_end :    0", times[1].strftime("hour_end : %-H"))
    lev_2_cal = lev_2_cal.replace("minute_end :  0", times[1].strftime("minute_end : %-M"))
    lev_2_cal = lev_2_cal.replace("second_end :  0", times[1].strftime("second_end : %-S"))
          
    file_lev_2_cal = os.environ['PATH_PHD']+'/projects/mirac_processing/airborne-mirac-correction/setup/lev_2/'+flight['mission'].lower()+'/setup_lev_2_'+flight_id+'.calibrate.txt'
    with open(file_lev_2_cal, 'w') as f:
        f.write(lev_2_cal)

#%% lev_2
# read the file with the calibrated values and store the calibrated value in the lev_2 setup file
# template of lev_2 setup file
file = os.environ['PATH_PHD']+'/projects/mirac_processing/airborne-mirac-correction/setup/templates/setup_lev_2.txt'
with open(file, 'r') as f:
    lev_2_template = f.read()

# read all lev_2 calibrated files
files = glob(os.environ['PATH_PHD']+'/projects/mirac_processing/airborne-mirac-correction/setup/lev_2/*/setup_lev_2_*.calibrated.txt')
    
# one setup file is created for every research flight
# different chirp settings are treated one after another from the calibration
# different flights on the same day need special treatment
# here, one has to make sure that the beginning and end time are selected such
# that the file is read. not just simply takeoff and landing, because it depends
# on the file name. maybe start with one hour before takeoff and after landing
# for this selection.

for file in files:
    
    # get flight_id from filename
    flight_id = file.split('setup_lev_2_')[1].split('.calibrated')[0]
    
    flight = meta[flight_id]
    
    lev_2 = deepcopy(lev_2_template)
    
    lev_2 = lev_2.replace("path_base_in : /net/secaire/nrisse/radar_processing/acloud/mirac_radar", 
                          "path_base_in : /net/secaire/nrisse/radar_processing/%s/mirac_radar"%flight['mission'].lower())

    lev_2 = lev_2.replace("path_base_out : /net/secaire/nrisse/radar_processing/acloud/mirac_radar", 
                            "path_base_out : /net/secaire/nrisse/radar_processing/%s/mirac_radar"%flight['mission'].lower())
    
    times = [flight['takeoff'], flight['landing']]
    times[0] = times[0]-datetime.timedelta(hours=1)
    times[1] = times[1]+datetime.timedelta(hours=1)    
    
    lev_2 = lev_2.replace("year_beg : 2017", times[0].strftime("year_beg : %Y"))
    lev_2 = lev_2.replace("month_beg :   5", times[0].strftime("month_beg : %-m"))
    lev_2 = lev_2.replace("day_beg :    23", times[0].strftime("day_beg : %-d"))
    lev_2 = lev_2.replace("hour_beg :    0", times[0].strftime("hour_beg : %-H"))
    lev_2 = lev_2.replace("minute_beg :  0", times[0].strftime("minute_beg : %-M"))
    lev_2 = lev_2.replace("second_beg :  0", times[0].strftime("second_beg : %-S"))
    
    lev_2 = lev_2.replace("year_end : 2017", times[1].strftime("year_end : %Y"))
    lev_2 = lev_2.replace("month_end :   5", times[1].strftime("month_end : %-m"))
    lev_2 = lev_2.replace("day_end :    24", times[1].strftime("day_end : %-d"))
    lev_2 = lev_2.replace("hour_end :    0", times[1].strftime("hour_end : %-H"))
    lev_2 = lev_2.replace("minute_end :  0", times[1].strftime("minute_end : %-M"))
    lev_2 = lev_2.replace("second_end :  0", times[1].strftime("second_end : %-S"))
    
    # replace the calibrated parameters
    # get calibration parameters
    with open(file, 'r') as f:
        s = yaml.safe_load(f)
    
    # extract parameters from file
    fwhm = float(s['beam_fwhm_deg'].split(', ')[0])
    
    # replace
    lev_2 = lev_2.replace("beam_fwhm_deg : 1.1", 
                          "beam_fwhm_deg : %f"%fwhm)
    
    file_lev_2 = os.environ['PATH_PHD']+'/projects/mirac_processing/airborne-mirac-correction/setup/lev_2/'+flight['mission'].lower()+'/setup_lev_2_'+flight_id+'_after_cal.txt'
    with open(file_lev_2, 'w') as f:
        f.write(lev_2)
        
#%% lev_3
# create one lev_3 setup file for every flight, to make it easier when a single
# flights needs to be processed again
# template of lev_3 setup file
file = os.environ['PATH_PHD']+'/projects/mirac_processing/airborne-mirac-correction/setup/templates/setup_lev_3.txt'
with open(file, 'r') as f:
    lev_3_template = f.read()

# read all lev_2 calibrated files (just to create lev_3 files for every flight)
files = glob(os.environ['PATH_PHD']+'/projects/mirac_processing/airborne-mirac-correction/setup/lev_2/*/setup_lev_2_*.calibrated.txt')
    
# one setup file is created for every research flight
# different chirp settings are treated one after another from the calibration
# different flights on the same day need special treatment
# here, one has to make sure that the beginning and end time are selected such
# that the file is read. not just simply takeoff and landing, because it depends
# on the file name. maybe start with one hour before takeoff and after landing
# for this selection.

for file in files:
    
    # get flight_id from filename
    flight_id = file.split('setup_lev_2_')[1].split('.calibrated')[0]
    
    flight = meta[flight_id]
    
    lev_3 = deepcopy(lev_3_template)
    
    lev_3 = lev_3.replace("path_base_in : /net/secaire/nrisse/radar_processing/acloud/mirac_radar", 
                          "path_base_in : /net/secaire/nrisse/radar_processing/%s/mirac_radar"%flight['mission'].lower())
    
    lev_3 = lev_3.replace("path_base_ins : /net/secaire/nrisse/radar_processing/acloud/gps_ins", 
                          "path_base_ins : /net/secaire/nrisse/radar_processing/%s/gps_ins"%flight['mission'].lower())

    lev_3 = lev_3.replace("path_base_out : /net/secaire/nrisse/radar_processing/acloud/mirac_radar", 
                          "path_base_out : /net/secaire/nrisse/radar_processing/%s/mirac_radar"%flight['mission'].lower())
    
    times = [flight['takeoff'], flight['landing']]
    times[0] = times[0]-datetime.timedelta(hours=1)
    times[1] = times[1]+datetime.timedelta(hours=1)    
    
    lev_3 = lev_3.replace("year_beg : 2017", times[0].strftime("year_beg : %Y"))
    lev_3 = lev_3.replace("month_beg :   5", times[0].strftime("month_beg : %-m"))
    lev_3 = lev_3.replace("day_beg :    23", times[0].strftime("day_beg : %-d"))
    lev_3 = lev_3.replace("hour_beg :    0", times[0].strftime("hour_beg : %-H"))
    lev_3 = lev_3.replace("minute_beg :  0", times[0].strftime("minute_beg : %-M"))
    lev_3 = lev_3.replace("second_beg :  0", times[0].strftime("second_beg : %-S"))
    
    lev_3 = lev_3.replace("year_end : 2017", times[1].strftime("year_end : %Y"))
    lev_3 = lev_3.replace("month_end :   5", times[1].strftime("month_end : %-m"))
    lev_3 = lev_3.replace("day_end :    24", times[1].strftime("day_end : %-d"))
    lev_3 = lev_3.replace("hour_end :    0", times[1].strftime("hour_end : %-H"))
    lev_3 = lev_3.replace("minute_end :  0", times[1].strftime("minute_end : %-M"))
    lev_3 = lev_3.replace("second_end :  0", times[1].strftime("second_end : %-S"))
    
    lev_3 = lev_3.replace("research_flight : 'RF04'", 
                          "research_flight : '%s'"%flight['name'])
    
    lev_3 = lev_3.replace("campaign : 'ACLOUD'", 
                          "campaign : '%s'"%flight['mission'])
    
    file_lev_3 = os.environ['PATH_PHD']+'/projects/mirac_processing/airborne-mirac-correction/setup/lev_3/'+flight['mission'].lower()+'/setup_lev_3_'+flight_id+'.txt'
    with open(file_lev_3, 'w') as f:
        f.write(lev_3)