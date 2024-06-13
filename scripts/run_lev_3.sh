#!/bin/bash

module="process_to_lev_3.py"

for setup_in in `ls ../setup/lev_3/$1/*.txt`
do

    echo $module
    echo $setup_in

    python $module $setup_in

done
