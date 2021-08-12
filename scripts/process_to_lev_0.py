#!/usr/bin/python2
"""


    Input
    =====
    - raw airborne remote sensing data Z(time, range)

    Output
    ======

    Author
    ======
    Andreas Anhaeuser (AA) <anhaeus@meteo.uni-koeln.de>
    Institute for Geophysics and Meteorology
    University of Cologne, Germany


    History
    =======
    2018-05-17 (AA): Created.


    Acknowledgements
    ================
    AA would like to express his gratitude to any machine that executes this
    code.
"""
# Standard modules
import os
import sys
import warnings
import datetime as dt

# PyPI modules
import numpy as np

# Acloud modules
import utils.in_out as io
import utils.setup as setup_utils
from utils.artifacts import perform_corrections as correct_artifacts

# AA's library
import aa_lib.tables as tab
from aa_lib.chronometer import Chronometer

_setup_file = '../setup/setup_lev_0.txt'
_DEBUG = False

###################################################
# MAIN                                            #
###################################################
# this is called from the section 'RUN' at the bottom
def main(setup_file=_setup_file, overwrite=True):
    """Main."""
    ###################################################
    # PREPARATION                                     #
    ###################################################
    print('read setup file %s' % setup_file)
    setup = tab.read_namelist(setup_file, convert_to_number=True)
    
    process_setup(setup)

    # list of filenames
    print('get filenames...')
    fnis = io.paths.get_filenames(setup)    # input filenames
    Nfiles = len(fnis)

    # chronometer (performance info)
    header = 'Artifact correction'
    info = setup_utils.get_chronometer_info(setup)
    chrono = Chronometer(Nfiles, header=header, info=info)
    setup['chrono'] = chrono    # for re-use in subfunctions

    if _DEBUG:
        chrono.warning('DEBUG-mode in main.')

    # DEBUG:
    if _DEBUG:
        fnis = fnis[6:7]

    ###################################################
    # LOOP OVER ALL INPUT FILES                       #
    ###################################################
    # Each input file is treated separately and independently.
    # This is suited very well for parallelization (if you want to do that).
    for fni in fnis:
        chrono.issue('=' * 79)
        chrono.issue('input file: %s' % fni)

        ###################################################
        # SKIP IF OUTPUT FILE EXISTS                      #
        ###################################################
        # Check whether this loop can be skipped. This is the case if both of
        # these are true:
        # - overwrite == False
        # - output file exists already

        skip = True

        # never skip if output file does not exist
        fno = io.paths.get_output_filename(fni, setup=setup)
        if not os.path.isfile(fno):
            skip = False

        # never skip if overwriting is desired
        if overwrite:
            skip = False

        if skip:
            chrono.issue('Skip loop since output file already exists')
            chrono.decrease_total_count()
            continue

        ###################################################
        # LOAD                                            #
        ###################################################
        # ========== load payload sensor data ============ #
        chrono.issue('load payload sensor data...')
        data = io.read.get_data(fni, setup)

        # ========== case: input file very short  ======== #
        # (less than two time steps)
        Ntime = len(data['secs1970'])
        if Ntime < 2:
            chrono.issue(
                    'WARNING: File contains less than 2 time steps. --> skip.')
            chrono.decrease_total_count()
            continue

        ###################################################
        # COMPUTATIONS                                    #
        ###################################################
        chrono.issue('artifact correction...')

        data = correct_artifacts(data, setup)

        ###################################################
        # OUTPUT                                          #
        ###################################################
        write = io.write.write_file(data, setup)          # an abbreviation

        chrono.loop()

        # DEBUG
        if _DEBUG:
            break

    chrono.resumee()

    return data, setup

###################################################
# PREPARATION                                     #
###################################################
def process_setup(setup):
    """Process setup after loading to make it usable by main()."""
    setup_utils.process_setup(setup, chop_lists=True)
    return setup


###################################################
# RUN                                             #
###################################################
if __name__ == '__main__':
    # If script is called from command line, then the first argument (if
    # present) is the setup file
    argv = sys.argv
    args = []

    for arg in argv:
        if arg[:1] == '-':
            continue
        args.append(arg)

    if len(args) > 1:
        setup_file = args[1]
    else:
        setup_file = _setup_file

    data, setup = main(setup_file=setup_file)

if _DEBUG and __name__ == '__main__':
    import matplotlib.pyplot as plt
    tmax = 500

    Ze_raw = data['Ze_raw'][:tmax]
    Ze = data['ze'][:tmax]

    plt.subplot(3, 1, 1)
    plt.pcolormesh(Ze_raw.T)
    plt.colorbar()
    
    plt.subplot(3, 1, 2)
    plt.pcolormesh(Ze.T)
    plt.colorbar()
    
    cmap = plt.get_cmap('jet', 16)
    vmin = 0
    vmax = 15
    flags = data['flag']
    plt.subplot(3, 1, 3)
    plt.pcolormesh(flags.T, vmin=vmin, vmax=vmax, cmap=cmap)
    plt.colorbar()

    plt.show()

