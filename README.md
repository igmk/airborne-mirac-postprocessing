# Airborne radar post-processing
Processing of the MiRAC measurements for attitude and viewing geometry
[Andreas Anhaeuser (AA), 2018-06-28]

Processing of the MiRAC measurements for attitude and viewing geometry. This
prepares the MiRAC-A and soon also GRaWAC data.

## Status

**MiRAC-A:**

|  campaign  | raw_rpg | raw  | lev_0 | lev_1a | lev_2 | lev_3 | PANGAEA |
| ---------- | ------- | ---- | ----- | ------ | ----- | ----- | ------- |
| ACLOUD     | done    | done | done  | done   | done  | done  | done    |
| AFLUX      | done    | done | done  | done   | done  | done  | done    |
| MOSAiC-ACA | done    | done | done  | done   | done  | done  | done    |
| HALO-AC3   | done    | done | done  | done   | done  | done  | done    |
| HAMAG      | ----    | ---- | ----  | ----   | ----  | ----  | ----    |

Short flights from HALO-AC3 (RF02, RF06) are not processed further than raw level

**GraWAC:**

|  campaign  | raw_rpg | raw  | lev_0 | lev_1a | lev_2 | lev_3 | PANGAEA |
| ---------- | ------- | ---- | ----- | ------ | ----- | ----- | ------- |
| HAMAG      | ----    | ---- | ----  | ----   | ----  | ----  | ----    |

## Overview of processing

- Raw_rpg to raw: creating one flight per flight/chirp setting and cleaning data
- Raw to lev_0: artifact correction
- lev_0 to lev_1a: time match of instruments, coordinate tranformation
- lev_1a to lev_2: calibration of fwhm
- lev_2 to lev_3: conversion range to alt

### Yaml files (.settings_yaml)

- calibration_times.yaml: Calibration time window for lev_1a calibration for every research flight defined by hand.
- calibration_times_empty.yaml: Template for calibration_times.yaml
- files_lev_3.yaml: List with the file names of the lev_3 files for every research flight.
- files_raw.yaml: List with the file names of the raw files for every research flight and chirp setting.
- measurement_error_times.yaml: Time windows for MOSAiC-ACA flights, where errors due to 89 GHz calibration occur.
- surface_reflection_times_heights.yaml: Times and height windows for MOSAiC-ACA flights, where surface reflection occurs. No automatic detection exists, therefore these are defined by hand.

### Required scripts (./preparation/)

- calibration_parameters.py: Reads calibration parameters during steps lev_1a and lev_2 from the setup txt files and creates plots. Helps to identify calibration issues.
- calibration_times.py: Collection of helper functions: creates calibration_times_empty.yaml, creates setup files for calibration run every research flight based on calibration_times.yaml (lev_1a, lev_2), creates setup files with calibrated values (lev_1a, lev_2), creates setup files for lev_3
- file_list_raw.py: Creates the yaml file files_raw.yaml, where the file names of the raw files are sorted by research flight and chirp table. Modifications need to be done by hand, following the docstring of the script
- prepare_gps_ins.py: Reduction of gps_ins data to flight time, exclusion of measurement errors, and removal of some parameters which are not needed.
- prepare_raw_data.py: Combines the raw radar files listed in files_raw.yaml to a single file per flight. Additionally, the time attributes are changed to make them conform with CF conventions (xarray then converts to datetime automatically), the data is sorted along the time dimension and duplicate times are removed (keep first), and data is reduced to flight time, -999 replaced by nan (here also the nc attributes are not following CF conventions by having missing_value or _FillValue set to -999!). Finally, erroneous reflectivities are replaced by nan. Which occur during mosaic-aca.
- view_raw_ze.py: Plot of the raw radar reflectivity every 30 min to identify erroneous signals during MOSAiC-ACA campaign

## Step-by-step guide

### Directory structure

Build this structure. Individual files are sorted in yyyy/mm/dd directories.
Radar name is either "mirac_radar" by "grawac"

├── campaign

│   ├── gps_ins

│   └── radar_name

│       ├── lev_0

│       ├── lev_1a

│       ├── lev_2

│       ├── lev_3

│       ├── raw

│       └── raw_rpg

### Raw_rpg

- Raw data was created by Mario using the python version of the RPG processing routines with the binary files as input
- The processing scripts do not change the data, they only convert them to netcdf and make some calculations such as Ze, ...
- All files are created with the same version of the RPG routines: https://github.com/igmk/w-radar/releases/tag/v2.0_202007
- The files used from the output are ending with *_ZEN_v2.0.nc
- The compact files do not contain all required variables for the processing
- Usually there is one file per hour, but it might also be more irregular

### Identification of measurement errors 1: after calibration

- The raw data contains measurement errors, which occur after the internal calibration at 89 GHz (only during MOSAiC-ACA).
- For two flights, the calibration was switched off: RF09, RF10. For two flights, the calibration is turned off partly: RF08, RF11. All other flights contain the stripes after nearly every 89 GHz calibration.
- The measurement error is removed by hand. Basis is the script view_raw_ze.py. It creates 30 min quicklooks of the measured Ze and the (afterwards) filtered Ze together with the measurement internval
- The measurement interval is about >8 s during 89 GHz calibration, while it is 1-2 seconds during all other times
- The times, when internal calibration is over and when the individual files end (times.txt, also printed by the view_raw_ze.py script), serve as basis for the detection of erroneous Ze values.
- The final time intervals, where erroneous values occur and comments on this for each fight are stored in measurement_error_times.yaml and can be read with the yaml library in python (as in view_raw_ze.py)
- All Ze values at these times are set to nan, but the time is kept. An additional flag value shows, that the data was removed because of measurement errors.
- Another error found is missing pixels at certain altitudes. It is not addressed here.

### Identification of measurement errors 2: multiple reflections

- In the upper chirp from 0 to 600 m range, multiple surface reflection occur during several MOSAiC-ACA and HALO-AC3 flights. Mostly, this signal is clearly separated from clouds. However, it also can be seen within clouds, but no attempt was made to substract the signal since both magnitude and vertical position could not be predicted. Therefore, only cases where the signal is clearly visible were removed by hand. In CFAD plots, the signal can be clearly seen, with similar Ze than cloud edges
- Time/height regions are identified using quicklooks of the raw signal with view_raw_ze.py similarly to the step above (errors 1). The script also plots identified regions, which are stored in surface_reflection_times_heights.yaml
- After the regions are defined properly, the processing can be started.
- Difficult flights during HALO-AC3, where manual identification was not possible properly:
  - RF03, RF04

### From raw_rpg to raw

- In this step, one file is created per flight and chirp setting. This is a two-step approach. At first, the files belonging to a flight are organized in a yaml file. Then these are merged using another script. The filename needs to be specified such that the radar processing recognizes the date. The date is needed for the processing later and should be the time of the first file of the flight/chirp setting.
- Filename convention: first 13 letters contain date and initial time
- If flights are on the same day, the files need to be separated manually!! See first lines in file_list_raw.py
- New flight for example during HALO-AC3: Run the file_list_raw.py file to add the desired flight files into the files_raw.yaml file.
- This step is done with the script prepare_raw_data.py and it includes
  - removal of duplicate times
  - sorting along time axis
  - replacement of -999 by nan
  - removal of measurement errors detected before (Ze only)
  - reduction to flight time with ac3airborne
  - creation of a single file per flight/chirp
  - adaption of attributes (time! Default is not recognized by xarray and therefore changed)
- Hint: if many flights are processed at once, then use the “missing” list and run it in parallel with ~5 flights each run

### GPS and INS data

- The gps and ins data are taken from the script dship_gps_ins_to_netcdf.py in airborne_tools

### From raw to lev_0

- This step is the same for all files/flights, and the filter settings are not changed
- Three setup files are created for the three campaigns to be able to run the processing without having to change the setup file every time (path of radar data)
- ACLOUD: python process_to_lev_0.py ../setup/lev_0/acloud/setup_lev_0_acloud.txt
- AFLUX: python process_to_lev_0.py ../setup/lev_0/aflux/setup_lev_0_aflux.txt
- MOSAiC-ACA: python process_to_lev_0.py ../setup/lev_0/mosaic-aca/setup_lev_0_mosaic-aca.txt
- HALO-AC3: python process_to_lev_0.py ../setup/lev_0/halo-ac3/setup_lev_0_halo-ac3.txt

### From lev_0 to lev_1a

- This step requires the GPS and INS data
- Create the calibration_times_empty.yaml file with a specific time interval
  - Requirement for calibration: strong Ze ground signal, curves/ascents/descents where angles change, continuous ground signal (most important), as long as possible, over flat surface (ocean or sea ice)
  - Usually just the one perfect interval is enough, no need to test multiple
  - These time intervals are also used in calibration during lev_2
  - Calibrated parameters are: orientation of mirac (azimuth, zenith), and time offset (between attitude/position sensor)
- Setup files for the calibration step are created for every research flight with specific time ranges using calibration_times.py
- A bash script loops over each setup file and creates a corresponding calibrated.txt file
- ACLOUD: bash run_lev_1a_calibrate.sh acloud
- AFLUX: bash run_lev_1a_calibrate.sh aflux
- MOSAiC-ACA: bash run_lev_1a_calibrate.sh mosaic-aca
- HALO-AC3: bash run_lev_1a_calibrate.sh halo-ac3
- Check the calibration parameters by running some parts of the script calibration_parameters.py
- If some calibration parameters are clearly wrong, because the ground signal is lost (maximum reflectivity not at surface, …), then adapt the time range for these flights (check quicklook etc.). To calibrate single flights and not the entire campaign again, follow the steps (i.e. line in bash scripts above):
  - 1: modification of the times in the calibration_times.yaml file
  - 2: call calibration_times.py to update the setup files
  - 3: run python process_to_lev_1a.calibrate.py ../setup/lev_1a/acloud/setup_lev_1a_ACLOUD_P5_RF10.calibrate.txt ../setup/lev_1a/acloud/setup_lev_1a_ACLOUD_P5_RF10.calibrated.txt
  - 4: call calibration_parameters.py to view the updates parameters
- The resulting calibration values are copied to a new setup file for every research flight using again the calibration_times.py script. Although the mounting position should be constant, the values are changed for each fight. Maybe the aircraft is not aligned the same way for every flight?
- A bash script loops over every research flight and processes the data to lev_1a
- ACLOUD: bash run_lev_1a.sh acloud
- AFLUX: bash run_lev_1a.sh aflux
- MOSAiC-ACA: bash run_lev_1a.sh mosaic-aca
- HALO-AC3: bash run_lev_1a.sh halo-ac3

### From lev_1a to lev_2

- The calibration of fwhm is done for the same times as selected in the previous step
  - ACLOUD: bash run_lev_2_calibrate.sh acloud
  - AFLUX: bash run_lev_2_calibrate.sh aflux
  - MOSAiC-ACA: bash run_lev_2_calibrate.sh mosaic-aca
  - HALO-AC3: bash run_lev_2_calibrate.sh halo-ac3
- Check again calibration_parameters.py to view the FWHM
- Calibration results differ between flights, but seem to be correct. Some flights show FWHM around 1.9, while most are between 1.1 and 1.2
- The resulting calibration values are copied to a new setup file for every research flight using again the calibration_times.py script.
- The processing to level 2 is done using a bash script, which calls the correct setup file for every research flight. Runs very fast.
- bash run_lev_2.sh

### From lev_2 to lev_3

- Since this step takes long and some flights might be processed again, one setup file is created for each research flight in advance. The only difference is the campaign name and the time between the flights, such that only one flight is processed
  - ACLOUD: bash run_lev_3.sh acloud
  - AFLUX: bash run_lev_3.sh aflux
  - MOSAiC-ACA: bash run_lev_3.sh mosaic-aca
  - HALO-AC3: bash run_lev_3.sh halo-ac3
  - individual flight: python process_to_lev_3.py ../setup/lev_3/`mission`/setup_lev_3_`MISSION`_P5_RF`NUMBER`.txt

### From lev_3 to flight files for PANGAEA and general use

- Lev_3 files are still split, if the chirp table changed during a flight. Also, the file name is not very useful and does not contain information on the flight number
- This process is done during the data preparation for pangaea. If more than one file occurs for a research flight, these are concatenated along time
- Also, the number of variables is reduced to the ones that will be put on pangaea
- This part is outside of the radar processing and is done with another script data_prep_mirac_radar.py
- The files are stored under net/secaire/nrisse/radar_processing/`campaign`/mirac_radar/compact
- Format for PANGAEA:
  - time: radar time (gps/ins are shifted to this time), when column was overflown
  - lat/lon: position, when column was overflown (= position of column)
  - tb: brightness temperature (with comment for 89 GHz over sea ice)
  - flag: instrument_status (only for MOSAiC-ACA)
    - 0: active_off (measurement errors in radar, but passive is working)
    - 1: active_on (radar and passive working)
- One additional correction has to be made for MOSAiC-ACA flights for times, when measurement errors due to 89 GHz calibration occur. Since entire range profiles had to be removed, there is a risk that these flagged values (set to nan, while no cloud is also nan) are shifted into a column without measurement errors, leading to a reduced hydrometeor fraction. Therefore, all values in the transformed lev_3 data (height instead of range) which occur 30 seconds before a measurement error due to calibration are also set to nan and masked. These columns might otherwise be not entirely filled. The value of 30 seconds was chosen as a good approximation for high-altitude flight legs: the measurement of a full column takes 20 seconds at 3 km with 70 m/s and 25° viewing angle: tan(25)*3000/70 = 20 s
  - This is not yet done in lev_3 processing output, therefore caution when working with lev_3 data
- Modifications for HALO-AC3:
  - changed email contact in attributes
  - changed time reference to seconds since 2017-01-01
- Visualization of every single flight and all netcdf variables: plot_radar_data_pangaea.ipynb
