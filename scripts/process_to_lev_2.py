

import os
import sys
import warnings
import datetime as dt
import numpy as np
import utils.in_out as io
import utils.setup as setup_utils
import utils.surface as sfc
import utils.target_velocity as tv
import utils.theory.surface as sfc_theo
from utils import several_datasets
from aa_lib.chronometer import Chronometer
import aa_lib.tables as tab


"""
Correct target velocities of airborne remote sensing data.

Call from command line
======================
(1) Modify setup file.
(2) Then call:
        <scriptname> [<setupfile>]

Purpose
=======
Use airborne remote sensing target velocities relative to the (moving)
sensor and compute the Earth-relative target velocities.

The output is still on a (time, range) grid, but with added target velocity
variables.

Input
=====
- level 01a airborne remote sensing data Z(time, range)

Output
======
(level 02)
netcdf files containing the same data as the level 01a, but with added
target velocity variables.

Author
======
Andreas Anhaeuser (AA) <anhaeus@meteo.uni-koeln.de>
Institute for Geophysics and Meteorology
University of Cologne, Germany

History
=======
2018-05-17 (AA): Created.
"""


_setup_file = '../setup/lev_2/acloud/setup_lev_2_ACLOUD_P5_RF04_after_cal.txt' #'../setup/setup_lev_2.txt'
_is_implemented = False


def main(setup_file=_setup_file, overwrite=True):
    """Main."""
    # load setup
    print('read setup file %s' % setup_file)
    setup = get_setup(setup_file)

    # list of filenames
    print('get filenames...')
    fnis = io.paths.get_filenames(setup)
    Nfiles = len(fnis)

    # chronometer (performance info)
    header = 'Derived data'
    info = setup_utils.get_chronometer_info(setup)
    chrono = Chronometer(Nfiles, header=header, info=info)
    setup['chrono'] = chrono

    datasets = []

    for fni in fnis:
        # chronometer
        chrono.issue('=' * 79)
        count_start = chrono.get_count()

        chrono.issue('current file: %s' % fni)

        # skip loop
        skip = True
        if overwrite:
            skip = False

        fno = io.paths.get_output_filename(fni, setup=setup)
        if not os.path.isfile(fno):
            skip = False

        if skip:
            chrono.issue('Skip loop since output files already exist.')
            chrono.decrease_total_count()
            continue

        # load
        datasets = add_datasets(datasets, setup, fni)
        datasets = remove_datasets(datasets, setup, fni)
        ncurr = get_ncurr(datasets, setup, fni)

        # computations
        chrono.issue('compute derived data...')
        data = compute_derived_data(datasets, setup, ncurr=ncurr)

        # DEBUG
        DEBUG = False
        if DEBUG:
            chrono.debug_warning(__name__)
            return data

        # write
        io.write.write_file(data, setup)

        # chronometer
        chrono.set_count(count_start + 1)

    # chronometer
    chrono.resumee()


def get_setup(setup_file):
    """Return a dict."""
    setup = tab.read_namelist(setup_file, convert_to_number=True)
    setup = process_setup(setup)
    return setup


def process_setup(setup):
    """Process setup after loading to make it usable by main()."""
    setup_utils.process_time(setup)

    # convert wind parameters to numpy arrays
    wind_params = ['wind_averaging_' + key for key in
            ('time', 'vertical', 'horizontal')]
    for key in wind_params:
        coef = setup[key]
        if not isinstance(coef, list):
            coef = [coef]
            setup[key] = np.array(coef)

    return setup


def compute_derived_data(datasets, setup, ncurr):
    # not implemented --> skip

    if not _is_implemented:
        return datasets[ncurr]

    # implemented
    if sensor_name == 'mirac':
        data = compute_target_velocity(datasets, setup, ncurr=ncurr)
    else:
        raise NotImplementedError()

    return data


def compute_target_velocity(datasets, setup, ncurr=1):
    """Dealias and decompose target velocity.

        Parameters
        ----------
        datasets : tuple of dict
            collection of datasets
        setup : dict
        ncurr : int, optional
            position of the current datasets within `datasets`. Default: 1

        Returns
        -------
        data : dict
            The current dataset with target velocity variables.
    """

    chrono = setup['chrono']
    
    # input check
    sensor_name = setup['payload_sensor_name'].lower()
    if sensor_name == 'mirac':
        pass
    elif sensor_name == 'amali':
        # don't do anything
        return datasets[ncurr]
    else:
        raise NotImplementedError('Sensor not implemented: %s' % sensor_name)

    # computations
    for data in datasets:
        if data is None:
            continue

        # synthesize theoretical signal
        if 'vm_raw_theo' not in data:
            sfc_theo.add_synthesized_signal(data, setup)
            normalize_Ze_theo(data, setup)
            fold_vm_theo(data, setup)

        # remove sensor motion
        if 'vm_c' not in data:
            tv.remove_sensor_motion(data, setup)

        # remove beam width effect
        if 'vm_c_bw-corrected' not in data:
            tv.remove_beam_width_effect(data, setup)

        # dealias (unfold)
        if 'vm_r' not in data.keys():
            tv.dealias(data, setup)

    # decompose
    # merge
    idx_time, idx_range = several_datasets.get_idx_current(
            datasets, ncurr=ncurr)
    data_merged = several_datasets.merge_datasets(datasets, setup, ncurr=ncurr)

    # decompose
    tv.decompose(
        data_merged, setup, idx_time=idx_time, idx_range=idx_range)

    # select current dataset
    data = several_datasets.select_current(
        data_merged, setup, idx_time=idx_time, idx_range=idx_range)

    return data


def normalize_Ze_theo(data, setup):
    """Return a dict."""

    Ze_real_sfc = sfc.get_value_at_surface(data, varname='ze')
    Ze_theo_sfc = sfc.get_value_at_surface(data, varname='ze_theo')

    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        f = Ze_real_sfc / Ze_theo_sfc
        f[np.isnan(f)] = 1.
        data['ze_theo'] *= np.expand_dims(f, 1)
    return data


def fold_vm_theo(data, setup):
    """Return a dict."""
    v = data['vm_raw_theo']
    vny = data['nqv']
    v = (v + vny) % (2 * vny) - vny
    data['vm_raw_theo'] = v
    return data



def time_bounds_datasets(data_curr, setup):
    """Return pair of dt.datetime."""

    # bounds of current dataset
    time_beg_curr = data_curr['time'][0]
    time_end_curr = data_curr['time'][-1]

    # tolerance
    alt_max = np.nanmax(data_curr['alt'])
    coef = setup['wind_averaging_time']
    secs_max = np.polyval(coef[::-1], alt_max)
    time_tol = dt.timedelta(seconds=secs_max)

    # time bounds
    time_beg = time_beg_curr - time_tol
    time_end = time_end_curr + time_tol

    return time_beg, time_end


def get_ncurr(datasets, setup, fni):
    """Return position of current dataset as int or None."""

    ds_filenames = [data['filename'] for data in datasets]
    if fni not in ds_filenames:
        return None

    return ds_filenames.index(fni)


def remove_datasets(datasets, setup, fni):
    """Return list of dict."""

    # time bounds
    ncurr = get_ncurr(datasets, setup, fni)
    data_curr = datasets[ncurr]
    time_beg, time_end = time_bounds_datasets(data_curr, setup)

    N = len(datasets)
    keep = [True] * N
    for n, data in enumerate(datasets):
        if len(data['time']) < 1:
            keep[n] = False
            continue

        time_beg_data = data['time'][0]
        time_end_data = data['time'][-1]

        if time_beg_data > time_end:
            keep[n] = False
        elif time_end_data < time_beg:
            keep[n] = False

    return [datasets[n] for n in range(N) if keep[n]]


def add_datasets(datasets, setup, fni):
    """Return list of dict."""

    ds_filenames = [data['filename'] for data in datasets]

    # retrieve current dataset
    if fni in ds_filenames:
        ncurr = ds_filenames.index(fni)
        data_curr = datasets[ncurr]
    else:
        # load current dataset
        data_curr = io.read.get_data(fni, setup)
        data_curr['filename'] = fni

    # all filenames
    time_beg, time_end = time_bounds_datasets(data_curr, setup)
    setup_tmp = {'time_beg' : time_beg, 'time_end' : time_end}
    copy_keys = ('path_base_in', 'lev_in', 'payload_sensor_name')
    for key in copy_keys:
        setup_tmp[key] = setup[key]
    filenames = io.paths.get_filenames(setup_tmp)

    # load missing datasets
    datasets_out = []
    for filename in filenames:
        if filename == fni:
            # use current dataset
            datasets_out.append(data_curr)
        elif filename in ds_filenames:
            # use existing dataset
            n = ds_filenames.index(filename)
            datasets_out.append(datasets[n])
        else:
            # load dataset
            data = io.read.get_data(filename, setup)
            data['filename'] = filename
            datasets_out.append(data)

    return datasets_out


def check_dimensions(data, setup):
    """Check if variables match time/range dimensions. Raise error if not."""

    chrono = setup['chrono']
    Nt = len(data['time'])
    Nr = len(data['range'])

    for key in sorted(data):
        shape = np.shape(data[key])
        if len(shape) < 2:
            continue
        if shape[:2] == (Nt, Nr):
            continue
        text = (('dimension of %s is %s and does not conform ' +
                '(time, range): %s') %
                (key, str(shape), str((Nt, Nr))))
        chrono.warning(text)
        raise Exception('Dimensions do not match.')


if __name__ == '__main__':

    # command line arguments
    args = sys.argv
    argv = []
    for arg in args:
        if arg[:1] != '-':
            argv.append(arg)

    # If script is called from command line, then the first argument (if
    # present) is the setup file
    if len(argv) > 1:
        setup_file = argv[1]
    else:
        setup_file = _setup_file

    data = main(setup_file=setup_file, overwrite=True)
