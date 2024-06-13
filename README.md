# Airborne radar post-processing
Processing of the MiRAC measurements for attitude and viewing geometry
[Andreas Anhaeuser (AA), 2018-06-28]

 
A package for processing a variety of airborne remote sensing data. For
documentation, see folder 'doc'.  (Other) folders:


processing/
===========
Data processing from level 01 (raw data) to higher levels.


analysis/
=========
Plotting routines.


utils/
======
Helper functions to the above.


aa_lib/
=======
Link to AA's python library.


setup/
======
Setup files to processing and anaylsis scripts.


doc/
====
Documentation (pdf).


tiny_scripts/
=============
Use-and-dispose scripts for special purposes. Not intended for automatization.
How to run one processing step
==============================

1) If you use a sensor that is not yet implemented, you first have to create
   I/O routines for this sensor.
   - This is done in ../utils/in_out/
   - A template for the necessary folder structure is saved in
     'template_payload_sensor'. Copy this to the name of your payload sensor
     and modify the files therein.
2) Manipulate setup file in ./setup/
   - each processing step has its own setup file
3) Run the processing step



Manipulate the code
===================
If you just quickly want to adapt the processing to your specific problem, it
is most probably the best to *WRITE A SUBROUTINE*. The main code is then only
extended by an if-statement capturing your specific case.

*DON'T PUT MAGIC NUMBERS INTO THE CODE.* Everything that is kind of arbitrary
(constants, parameters, etc.) should go to the setup files.


Contact
=======
Andreas Anhäuser
<andreas.anhaeuser@uni-koeln.de>
<andreas.anhaeuser@posteo.net>

How to process MiRAC-A Radar:

-raw file: The first 13 letters of the raw file needs to contain the date and initial time and research flight number: ******_******_RF.. ...

Step 0:
1. Choose dates, input and output path in "setup_lev_0.txt"  
2. Here you can change speckle filter and disturbance filter settings if you want "setup_lev_0.txt" 
3. Process: process_to_lev_0.py

Step 1a:
1. Set up the gps and ins data, which should be in NETCDF-format (folder: /ins/P5/gps1 or /ins/P5/ins1)
2. .../processing/utils/in_out/ins/read.py: change input path in variable "_path_ins"
3. .../processing/calibration.py: change variable "plot_path_out" in line 154
3. For calibration choose dates, input and output path and if necessary change first guesses for the calibration parameters: setup_lev_1a.calibrate.txt
4. Choose dates for calibration: Measurements should be continuous, surface height nearly constant and time interval needs to be as long as possible
5. Process: process_to_lev_1a.calibrate.py
6. Look up the calibrated values: setup_lev_1a.calibrated.txt
7. Choose dates (-->input and output path) and insert the calibrated values: setup_lev_1a.txt 
8. Process: process_to_lev_1a.py
Note: If time offsets variation between the flights is large, please calibrate every single flight.

Step 2:
1. For calibration choose dates, input and output path and if necessary change first guesses for the calibration parameters: setup_lev_2.calibrate.txt
2. Choose dates for calibration: Measurements should be continuous, surface height nearly constant and time interval needs to be as long as possible
3. Process: process_to_lev_2.calibrate.py 
4. Look up the calibrated values: setup_lev_2.calibrated.txt
5. Choose dates, input and output path and insert the calibrated values: setup_lev_2.txt
6. Process: process_to_lev_2.py

Step 3: 
1. Choose dates, input and output path: setup_lev_3.txt
2. If necessary change the grid of the data: setup_lev_3.txt
3. Process: process_to_lev_3.py
