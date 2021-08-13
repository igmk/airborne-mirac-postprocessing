

import os
import sys
import datetime as dt
import numpy as np
import utils.in_out as io
import utils.setup as setup_utils
from utils import remap_utils
from utils import several_datasets
from aa_lib.chronometer import Chronometer
from aa_lib import datetime_utils
from aa_lib import tables as tab


"""
Map lev 02 data from (time, range) to (time, alt) grid.

Call from command line
======================
(1) Modify setup file.
(2) Then call:
        <scriptname> [<setupfile>]

Purpose
=======
The Polar 5 MIRAC Doppler radar data contain the 0th to 3rd moments of the
Doppler speed. They come in coordinates relative to the sensor (distance to
the radar antenna). This script uses data the data in the level 02 files to
re-maps the data points
* from input: Z(time, range)
* to output: Z(aircraft_pos(time), altitude)
and stores them such that data in one column does not correspond to the
same measurement time but rather to the same lon-lat position.

Input
=====
- level 02 files

Output
======
- level 03 files: data mapped onto a globally-constant height grid
(- level 02a files: data mapped onto a file-constant height grid) # not used

Author
======
Andreas Anhaeuser (AA) <anhaeus@meteo.uni-koeln.de>
Institute for Geophysics and Meteorology
University of Cologne, Germany

History
=======
2018-02-02 (AA): Created.
"""


_setup_file = '../setup/setup_lev_3.txt'


def from_command_line():
    """Run from command line"""
    setup_file = _setup_file

    # command line arguments
    # override defaults
    argv = sys.argv
    args = []

    # get un-dashed parameters
    for arg in argv:
        if arg[:1] == '-':
            continue
        args.append(arg)

    # check whether setup file has been specified
    if len(args) > 1:
        setup_file = args[1]

    # process setup
    print('read setup file %s' % setup_file)
    setup = tab.read_namelist(setup_file, convert_to_number=True)
    setup_utils.process_setup(setup, chop_lists=True)

    main(setup)


def main(setup, overwrite=True):
    """Run main."""
    
    # preparation
    # input files
    print('get filenames...')
    fnis_abs = io.paths.get_filenames(setup)
    Nfiles = len(fnis_abs)

    # datasets
    data_prev = None
    data_curr = None
    data_next = None

    # chronometer
    cw = 20
    header = 'Remap data'
    info = setup_utils.get_chronometer_info(setup)
    chrono = Chronometer(Nfiles, header=header, info=info)
    setup['chrono'] = chrono

    for nfile in range(-1, Nfiles):
        chrono.issue('=' * 79)

        # shift data by one loop
        data_prev = data_curr
        data_curr = data_next

        # load
        # current file name
        if nfile >= 0:
            fni_abs_curr = fnis_abs[nfile]
        else:
            fni_abs_curr = 'none'
        chrono.issue('current file: %s' % fni_abs_curr)

        # load next data file
        if nfile < Nfiles - 1:
            fni_abs_next = fnis_abs[nfile + 1]
            chrono.issue('load next data file: %s' % fni_abs_next)
            data_next = get_data_on_native_grid(fni_abs_next, setup)
            assert data_next is not None
        else:
            data_next = None

        # skip loop
        if nfile < 0:
            continue

        skip = True
        if overwrite:
            skip = False

        fno = io.paths.get_output_filename(fni_abs_curr, setup=setup)
        if not os.path.isfile(fno):
            skip = False

        if skip:
            chrono.issue('Skip loop since outputs files already exist')
            chrono.decrease_total_count()
            continue

        # Interpolate data from range grid to height grid.
        # Cases:
        # (1) file_constant:
        #     The output grid is different for each file.
        #     Therefore, all three data sets in memory have to be
        #     re-interpolated each loop.
        # (2) globally_constant:
        #     Technically, it would suffice to interpolate each dataset only
        #     once. However, distinguishing this case from (1) would complicate
        #     the code. As the interpolation is not the bottleneck of the
        #     script, clarity is preferred over efficiency.
        chrono.issue('interpolate to output height grid...')

        # output altitude grid
        alts_out = remap_utils.get_output_height_grid(data_curr, setup)

        # interpolate all 3 datasets
        datasets = (data_prev, data_curr, data_next)
        f = interpolate_several_datasets_to_height_grid
        data_intp = f(datasets, setup, alts_out, ncurr=1)

        # Remap data onto vertical columns.
        # At the file borders, matching aircraft and target positions may be in
        # different files. Therefore, the two adjacent data sets to `data_curr`
        # are used.
        # As this operation is the bottleneck, only columns
        # referring to `data_curr` (and not those of `data_prev` and
        # `data_next`) are remapped. This speeds up the program substantially.
        chrono.issue('remap to vertical columns...')

        # time indices of `data_curr` within (data_prev, data_curr, data_next)
        idx_time, idx_range = several_datasets.get_idx_current(
                datasets, ncurr=1)

        # remap time steps idx_curr, but also use adjacent data to do so.
        chrono.issue('re-map spatially...')
        data_remap = remap_utils.remap_data_spatially(
                data_intp, setup, idx_time=idx_time
                )

        # un-merge (last, curr, next)
        chrono.issue('un-merge datasets (last, current, next)')
        data_remap_curr = several_datasets.select_current(
                data_remap, setup, idx_time=idx_time)

        # write result
        chrono.issue('write %s' % fno)
        data_remap_curr['time'] = datetime_utils.seconds_to_datetime(
                data_remap_curr['secs1970'])
        io.write.write_file(data_remap_curr, setup)
        del data_remap_curr['time']


def get_data_on_native_grid(fni, setup):
    """Return a dict."""
    data = io.read.get_data(fni, setup)
    del data['time']
    return data


def interpolate_several_datasets_to_height_grid(
        datasets, setup, alts_out, ncurr=1):
    """Return one dict of all interpolated data merged together.

        Parameters
        ----------
        datasets : list of dict
        setup : dict
        alts_out : array (1D)
        ncurr : int
            index of the 'current' dataset within `datasets`. This is used to
            copy time independent (but file dependent) variables from the
            appropriate data set.
    """

    init = False
    assert 0 <= ncurr < len(datasets)
    data_intp = {}

    for ndata, data in enumerate(datasets):
        # skip empty data
        if data is None:
            assert ndata != ncurr
            continue

        data_intp_one = remap_utils.interpolate_to_height_grid(
                data, setup, alts_out)

        varnames = data.keys()
        Nt = len(data['secs1970'])

        # copy time independent variables if data set is labelled 'current'
        if ndata == ncurr:
            for varname in varnames:
                # check whether time dependent
                shape = np.shape(data_intp_one[varname])
                if shape[:1] == (Nt,):
                    if varname not in ('alt',):
                        continue

                data_intp[varname] = data_intp_one[varname]

        # time dependent
        for varname in varnames:
            # check whether time dependent
            shape = np.shape(data_intp_one[varname])
            if shape[:1] != (Nt,):
                continue

            if varname in ('alt',):
                continue

            # initialize
            if not init:
                data_intp[varname] = data_intp_one[varname]

           # concatenate
            else:
                axis = shape.index(Nt)
                d = (data_intp[varname], data_intp_one[varname])
                data_intp[varname] = np.concatenate(d, axis)

        init = True

    return data_intp


if __name__ == '__main__':

    from_command_line()
