#!/bin/bash

module="process_to_lev_2.py"

for setup_in in `ls ../setup/lev_2/*/*_after_cal.txt`
do

    echo $module
    echo $setup_in

    python $module $setup_in

done
