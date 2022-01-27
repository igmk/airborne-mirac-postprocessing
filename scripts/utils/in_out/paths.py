#!/usr/bin/python2
"""Acloud file path functions."""

# standard modules
import os
import datetime as dt
import glob
import re

# PyPI modules
from netCDF4 import Dataset

# Acloud modules
from utils.in_out import init

# AA's library
from aa_lib import datetime_utils

_setup = {
        'time_beg' : None,
        'time_end' : None,
        }

###################################################
# MAIN FUNCTIONS                                  #
###################################################
def get_filenames(setup):
    """Return list of existing filenames.

        Parameters
        ----------
        setup : dict with these keys:
            'time_beg'
            'time_end'
            'lev_in'
            'path_base_in'

        Returns
        -------
        filenames : list of str
            absolute path to filenames
        """
    ###################################################
    # DEFAULT                                         #
    ###################################################
    for key in _setup:
        if key not in setup.keys():
            setup[key] = _setup[key]

    ###################################################
    # GET CANDIDATES                                  #
    ###################################################
    # ========== raw ================================ #
    lev_in = setup['lev_in']
    if lev_in == 'raw':
        io_sensor = init.get_io_sensor(setup)
        filenames = io_sensor.paths.get_filenames(setup)
        


    # ========== level >= 0 =============================== #
    else:
        time_beg = setup['time_beg']
        time_end = setup['time_end']
        
        # input check
        if time_beg is not None:
            assert isinstance(time_beg, dt.datetime)
        if time_end is not None:
            assert isinstance(time_end, dt.datetime)

        # path check
        print(lev_in)
        path = setup['path_base_in'] + '/%s' % lev_in # problem for  calibration --> you need a lev_
        print(lev_in)
        if not os.path.isdir(path):
            raise IOError('Directory does not exist: %s' % path)

        # filename candidates
        dig = '[0-9]'
        pattern = path + '/%s/%s/%s/*.nc' % (4 * dig, 2 * dig, 2 * dig)
        filenames = sorted(glob.glob(pattern))

    ###################################################
    # FILTER CANDIDATES                               #
    ###################################################
    filenames = filter_files_for_time_beg(filenames, setup)
    filenames = filter_files_for_time_end(filenames, setup)

    return filenames

def get_output_filename(filename_in=None, data=None, setup=None):
    """Return a str.

        Either `data` or `filename_in` must be given. If both are given, `data`
        is ignored.
        `setup` must be given.

        Parameters
        ----------
        filename_in : str
            input filename
        data : dict
        setup : dict with keys:
            'lev_out' : str
            'payload_sensor_name' : str
            'path_base_out' : str

        Returns
        -------
        filename_out : str
            output filename
    """
    ###################################################
    # INPUT CHECK                                     #
    ###################################################
    # data
    if filename_in is None:
        if not isinstance(data, dict):
            raise TypeError('data must be a dict.')
        if filename_in is None:
            if not 'time' in data:
                raise KeyError('data must contain time.')
            if not (isinstance, data['time'][0], list):
                raise TypeError("data['time'] must be a list.")
            if len(data['time']) < 1:
                raise IndexError('Empty time list in data.')
            if not (isinstance, data['time'][0], dt.datetime):
                raise TypeError('time must be dt.datetime object.')

    # setup
    if not isinstance(setup, dict):
        raise TypeError('setup must be a dict.')
    keys = ('lev_out', 'payload_sensor_name', 'path_base_out')
    for key in keys:
        if key not in setup.keys():
            raise KeyError('setup must contain "%s".' % key)

    ###################################################
    # BUILD FILENAME                                  #
    ###################################################
    lev_out = setup['lev_out']
    pbo = setup['path_base_out']
    sensor_name = setup['payload_sensor_name']

    if filename_in is not None:
        time_beg = get_start_time(filename_in, setup)
    else:
        time_beg = data['time'][0]

    yyyymmdd = time_beg.strftime('%Y/%m/%d')
    timestamp = time_beg.strftime('%Y%m%d_%H%M%S')

    path_out = '%s/%s/%s' % (pbo, lev_out, yyyymmdd)
    fno = '%s/%s_%s_%s.nc' % (path_out, sensor_name, lev_out, timestamp)

    return fno

###################################################
# HELPER FUNCTIONS                                #
###################################################
def get_time_bounds(filename, setup):
    """Return start and end time as tuple of datetime.datetime.

        Parameters
        ----------
        filename : str
            path to an existing file

        Returns
        -------
        time_beg : datetime.datetime
            first time in file
        time_end : datetime.datetime
            last time in file
    """
    # start
    time_beg = get_start_time(filename, setup)
    time_end = get_end_time(filename, setup)
    return time_beg, time_end

def get_start_time(filename, setup):
    """Return a datetime.datetime."""
    lev_in = setup['lev_in']
    if lev_in == 'raw':
        io_sensor = init.get_io_sensor(setup)
        return io_sensor.paths.get_start_time(filename, setup)

    try:
        # This is cheap since there is no need to open the file.
        time = get_start_time_from_filename(filename, setup)
    except ValueError:
        # well, this did not work --> open file and have a look at the data
        return get_start_time_from_data(filename, setup)

    return time

def get_end_time(filename, setup):
    """Return a datetime.datetime."""
    lev_in = setup['lev_in']
    if lev_in == 'raw':
        io_sensor = init.get_io_sensor(setup)
        return io_sensor.paths.get_end_time(filename, setup)

    with Dataset(filename, 'r') as fid:
        vid = fid.variables['time']
        secs1970_end = vid[-1]

    time_end = datetime_utils.seconds_to_datetime(secs1970_end)
    return time_end

def get_start_time_from_filename(filename, setup):
    """Return a datetime.datetime.

        Parameters
        ----------
        filename : str
        setup : dict

        Returns
        -------
        datetime.datetime

        Raises
        ------
        ValueError
            If filename has unsupported format
    """
    # ========== input check  ============================ #
    mandatory_keys = ('payload_sensor_name', 'lev_in')
    for key in mandatory_keys:
        if key not in setup:
            raise KeyError('Missing setup key: %s' % key)
    # ==================================================== #

    # ========== crop the filename  ====================== #
    prefix = setup['payload_sensor_name'] + '_' + setup['lev_in']
    len_pref = len(prefix)

    # Assume that the filename contains the start time as *yymmdd_HHMMSS*
    fmt = '%Y%m%d_%H%M%S'
    len_date = 8    # yyyymmdd
    len_infix = 1   # '_'
    len_time = 6    # HHMMSS

    # shorten filename (ignore folder component)
    idx_dir = filename.rfind('/')
    idx_beg = idx_dir + 1 + len_pref
    search_string = filename[idx_beg:]
    # ==================================================== #

    # find the first digit
    digits = re.search(r'\d', search_string)
    if digits is None:
        raise ValueError('Cannot find timestamp in filename.')

    # isolate what we think is the timestamp
    beg = digits.start()
    end = beg + len_date + len_infix + len_time
    timestamp = search_string[beg:end]

    # try whether this works
    # (raises ValueError if not)
    time = dt.datetime.strptime(timestamp, fmt)

    return time

def get_start_time_from_data(filename, setup):
    """Return a datetime.datetime."""
    lev_in = setup['lev_in']
    if lev_in == 'raw':
        raise ValueError('Cannot handle data level: %s' % lev_in)

    with Dataset(filename, 'r') as fid:
        vid = fid.variables['time']
        secs1970_beg = vid[0]

    time_beg = datetime_utils.seconds_to_datetime(secs1970_beg)
    return time_beg

def filter_files_for_time_beg(filenames, setup):
    """Filter for starting time and return list of str."""
    time_beg = setup['time_beg']
    if time_beg is None:
        return filenames

    filenames_out = []

    N = len(filenames)
    for n, filename in enumerate(filenames):
        keep = False

        # ============ start after time_beg ============== #
        if get_start_time(filename, setup) >= time_beg:
            keep = True
        # ================================================ #

        # ========== start before time_beg  ============== #
        # check start time of next file
        elif n < N - 1 and get_start_time(filenames[n+1], setup) < time_beg:
            # start of next file also before time_beg
            keep = False

        # check end time
        elif get_end_time(filename, setup) >= time_beg:
            keep = True
        # ================================================ #

        if keep:
            filenames_out.append(filename)

    return filenames_out

def filter_files_for_time_end(filenames, setup):
    """Filter for end time and return list of str."""
    time_end = setup['time_end']
    if time_end is None:
        return filenames

    filenames_out = []
    for fn in filenames:
        time = get_start_time(fn, setup)
        if time < time_end:
            filenames_out.append(fn)

    return filenames_out
