#!/usr/bin/python
"""MIRAC level 01: Paths, filenames, times."""

# standard modules
import os
import datetime as dt
import glob
import re

# Acloud modules
from utils.in_out.mirac import read

###################################################
# COMPULSORY FUNCTIONS                            #
###################################################
# (these are expected from outside)
def get_filenames(setup):
    """Return list of filenames."""
    lev_in = setup['lev_in']
    if lev_in != 'raw':
        raise ValueError('Unsupported data level: %s' % lev_in)

    # path check
    path = setup['path_base_in'] + '/%s' % lev_in
    if not os.path.isdir(path):
        raise IOError('Directory does not exist: %s' % path)

    # filename candidates
    dig = '[0-9]'
    pattern = path + '/%s/%s/%s/*.nc' % (4 * dig, 2 * dig, 2 * dig)
    filenames = sorted(glob.glob(pattern))

    # filter
    filenames = filter_for_filename(filenames)

    return filenames

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
    time_beg = get_start_time(filename, setup)
    time_end = get_end_time(filename, setup)
    return time_beg, time_end

def get_start_time(filename, setup):
    """Return a datetime.datetime."""
    lev_in = setup['lev_in']
    if lev_in != 'raw':
        raise ValueError('Unsupported data level: %s' % lev_in)

    #try:
    # This is cheap since there is no need to open the file.
    time = get_start_time_from_filename(filename, setup)
    #except ValueError:
    #    # well, this did not work --> open file and have a look at the data
    #    time = get_start_time_from_data(filename, setup)

    return time

def get_end_time(filename, setup):
    """Return a datetime.datetime."""
    lev_in = setup['lev_in']
    if lev_in != 'raw':
        raise ValueError('Unsupported data level: %s' % lev_in)

    data = read.get_data(filename, setup, varnames=('time'))
    times = data['time']

    return times[-1]

###################################################
# HELPER FUNCTIONS                                #
###################################################
# (for internal use only)
def filter_for_filename(filenames):
    """Filter for filename and return list of str."""
    filenames_out = []

    # filter for name
    for filename in filenames:
        # if not 'compact' in filename:
            # continue
        filenames_out.append(filename)

    return filenames_out

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
    # Assume that the filename contains the start time as *yymmdd_HHMMSS*

    # find first appearance of a digit
    fmt = '%y%m%d_%H%M%S'
    len_date = 6    # yyyymmdd
    len_infix = 1   # '_'
    len_time = 6    # HHMMSS

    # shorten filename (ignore folder component)
    idx_dir = filename.rfind('/')
    idx_dir = max(idx_dir, 0)
    filename_short = filename[idx_dir:]

    # find the first digit
    digits = re.search(r'\d', filename_short)
    if digits is None:
        raise ValueError('No digits in filename.')

    # isolate what we think is the timestamp
    beg = digits.start()
    end = beg + len_date + len_infix + len_time
    timestamp = filename_short[beg:end]

    # try whether this works
    # (raises ValueError if not)
    time = dt.datetime.strptime(timestamp, fmt)
    return time

def get_start_time_from_data(filename, setup):
    """Return a datetime.datetime."""
    lev_in = setup['lev_in']
    
    if lev_in != '01':
        raise ValueError('Unsupported data level: %s' % lev_in)

    data = read.get_data(filename, setup, varnames=('time'))
    times = data['time']

    return times[-1]
