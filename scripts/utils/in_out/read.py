#!/usr/bin/python
"""Read payload sensor data.

    Authors
    -------
    Andreas Anhaeuser (AA) <anhaeus@meteo.uni-koeln.de>
    Marek Jacob (MJ) <marek.jacob@uni-koeln.de>
    Institute for Geophysics and Meteorology
    University of Cologne, Germany
"""

# standard modules
import datetime as dt
import warnings

# PyPI modules
import numpy as np
from netCDF4 import Dataset

# Acloud modules
from utils.in_out import init

# AA's library
from aa_lib import datetime_utils

###################################################
# MAIN FUNCTION                                   #
###################################################
# (expected from outside)
def get_data(filename, setup, varnames=None):
    """Return data as dict.

        Parameters
        ----------
        filename : str
            path to file
        setup : dict
            compulsory keys:
            'lev_in' : input level
            optional keys:
            'time_beg' : datetime.datetime (inclusive)
            'time_end' : datetime.datetime (exclusive)
        varnames : list of str, optional
            If given, only these variables are loaded

        Returns
        -------
        data : dict
            with at least these keys:
            'secs1970' : array of float, length Nt
                seconds since 1970
            'time' : list of datetime.datetime, length Nt
                the above array converted to datetime objects
            'range' : array of float
                distance from sensor
            <signal> : array, shape (Nt, Nr)
                measured signal (return multiple variables in separate entries)

        History
        -------
        2018-01-28 (AA): Created
        2018-07-01 (AA): Generalization to handle all levels and sensors.
    """

    if 'chrono' in setup:
        setup['chrono'].issue('load %s' % filename)

    lev_in = setup['lev_in']
    if lev_in == 'raw':
        io_sensor = init.get_io_sensor(setup)
        data = io_sensor.read.get_data(filename, setup, varnames)
    else:
        data = get_data_raw(filename, setup, varnames)

    filter_time(data, setup)

    rename_variables(data, setup)

    return data

###################################################
# HELPER FUNCTIONS                                #
###################################################
def get_data_raw(filename, setup, varnames=None):
    """Get data for lev_in >= '0' and return as dict."""
    load_always = ('time', 'range')

    # input check
    lev_in = setup['lev_in']
    if lev_in == 'raw':
        raise ValueError('Unsupported data level: %s' % lev_in)

    data = {}
    with Dataset(filename, 'r') as fid:
        fid.set_auto_mask(False)

        # variables
        keys = fid.variables.keys()
        for key in keys:
            load = False
            if varnames is None:
                load = True
            elif key in varnames:
                load = True
            elif key in load_always:
                load = True

            if not load:
                continue

            with warnings.catch_warnings():
                warnings.simplefilter('ignore', RuntimeWarning)
                data[key] = load_variable(fid, key)

            if key.endswith('_flag'):
                vid = fid.variables[key]
                data[key + '_masks'] = vid.getncattr('flag_masks')
                data[key + '_meanings'] = vid.getncattr('flag_meanings')

        # global attributes
        atts = fid.ncattrs()
        for att in atts:
            key = 'global:%s' % att
            data[key] = str(fid.getncattr(att))

        # history
        if not 'history' in atts:
            data['global:history'] = ''

    # time conversion
    data['secs1970'] = data['time']
    data['time'] = datetime_utils.seconds_to_datetime(data['secs1970'])

    return data

def load_variable(fid, key):
    """Load nc-variable and perform string-conversion if applicable."""
    vid = fid.variables[key]
        
    # load
    value = vid[:]

    # convert string
    dimensions = vid.dimensions
    #if 'char_pos' in dimensions:
        
        #value = str(''.join(value)).strip('\0')
    return value

def filter_time(data, setup):
    """Filter for start and end time and return as dict."""
    # lower bound
    found = False
    for key in ('time_min', 'time_beg'):
        if key in setup:
            found = True
            time_min = setup[key]
            break
    if not found:
        time_min = data['time'][0]

    # upper bound
    found = False
    for key in ('time_max', 'time_end'):
        if key in setup:
            found = True
            time_max = setup[key]
            break
    if not found:
        time_max = data['time'][-1] + dt.timedelta(0, 0, 1)

    # create time index
    if 'time' in data:
        time_key = 'time'
    elif 'time' in data:
        time_key = 'time'
    else:
        raise KeyError('Cannot find any time key.')
    times = data[time_key]

    Nt = len(times)
    idx = np.ones(Nt, dtype=bool)
    if time_min > times[-1]:
        idx[:] = False
    elif time_max <= times[0]:
        idx[:] = False
    else:
        if time_min > times[0]:
            for t in range(Nt):
                if times[t] >= time_min:
                    break
            idx[:t] = False
        if time_max <= times[-1]:
            for t in range(Nt):
                if times[t] >= time_max:
                    break
            idx[t:] = False

    # apply time index
    if np.sum(idx) < Nt:
        data[time_key] = [times[t] for t in range(Nt) if idx[t]]

        for key in data.keys():
            if key == time_key:
                continue

            shape = np.shape(data[key])
            if Nt not in shape:
                continue
            axis = shape.index(Nt)
            idx_pos = np.arange(Nt)[idx]
            data[key] = np.take(data[key], idx_pos, axis=axis)

    return data

def rename_variables(data, setup):
    if 'global:platform' in data:
        data['platform_name'] = data['global:platform']


###################################################
# UNUSED                                          #
###################################################
def convert_masked_arrays(data, setup={}):
    """Convert masked arrays into regular array and return data as dict."""
    ###################################################
    # MASKED ARRAY --> NAN                            #
    ###################################################
    for key in data:
        if not np.ma.isMaskedArray(data[key]):
            continue

        vals = data[key].data
        mask = data[key].mask
        if np.any(mask):
            vals[mask] = np.nan
        data[key] = vals

    return data
