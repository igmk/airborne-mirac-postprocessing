#!/bin/bash

# this script runs the lev_2 calibration for every research flight
# from the three campaigns. The calibration parameters will be written
# into the calibrated* file of the same directory

module="process_to_lev_2.calibrate.py"

for setup_in in `ls ../setup/lev_2/$1/*calibrate.txt`
do

    setup_out=${setup_in::-4}"d.txt"

    echo $module
    echo $setup_in
    echo $setup_out

    python $module $setup_in $setup_out

done
