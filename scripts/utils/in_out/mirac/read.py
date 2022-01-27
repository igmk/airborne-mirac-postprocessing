#!/usr/bin/python
"""Mirac level 01 file reader."""

# standard modules
import datetime as dt

# PyPI modules
import numpy as np
from netCDF4 import Dataset

# local library
from aa_lib import datetime_utils as dt_utils

###################################################
# MAIN FUNCTION                                   #
###################################################
# (expected from outside)
def get_data(filename, setup={}, varnames=None):
    """Return payload sensor data as dict.

        Parameters
        ----------
        filename : str
            path to radar file
        setup : dict, optional


        Returns
        -------
        data : dict
            compulsory keys:
            'time' : list of datetime.datetime of length Nt
            'secs1970' : array of length Nt, seconds since 1970
            'range' : array of length Nr, distance from sensor
            'global:history' : str (global nc-attribute)

            sensor specific keys, shape (Nt, Nr):
            'ze'
            'vm_raw'
            'v_sigma'
            'v_skew'

            sensor specific keys, other shape:
            'lwp'
            'tb'
            'freq_sb'
            'nqv'
            'range_offsets'
            ...


        History
        -------
        2018-01-28 (AA): Created
    """

    # load raw data
    data, meta = load_data_raw(filename, setup, varnames)

    # post-processing jobs to make data nicer:
    jobs = (
            convert_time,
            convert_variables,
            handle_nans,
            )
    for job in jobs:
        data, meta = job(data, meta, setup)

    return data

###################################################
# HELPERS                                         #
###################################################
# (internal)
def load_data_raw(filename, setup={}, varnames=None):
    """Get data and return as dict."""

    ###################################################
    # LOAD                                            #
    ###################################################
    load_always = ('time', 'range')
    load_never = ('lon_instr', 'lat_instr', 'zsl')
    data = {}
    meta = {}
    with Dataset(filename, 'r') as fid:
        # variables
        fid.set_auto_maskandscale(False)
        keys = fid.variables.keys()

        for key in keys:
            load = False
            if varnames is None:
                load = True
            elif key in varnames:
                load = True
            elif key in load_always:
                load = True

            if key in load_never:
                load = False

            if not load:
                continue

            vid = fid.variables[key]
            data[key] = vid[:]
            meta[key] = {}
            vatts = vid.ncattrs()
            for att in vatts:
                meta[key][att] = vid.getncattr(att)

        # global attributes
        atts = fid.ncattrs()
        for att in atts:
            key = 'global:%s' % att
            data[key] = fid.getncattr(att)

        # history
        if not 'history' in atts:
            data['global:history'] = ''

    return data, meta

def convert_time(data, meta, setup={}):
    """Convert time and return data as dict."""
    # reference time
    ref = dt.datetime(2001, 1, 1)

    # assert that assumed reference date appears in meta data
    assert 'time' in data
    assert 'units' in meta['time']
    patterns = ['1.1.2001', '2001.01.01', '2001-01-01']
    found = False
    for pattern in patterns:
        if pattern in meta['time']['long_name'] or pattern in meta['time']['units']:
            found = True
            break
    assert found

    # convert
    data['time'] = dt_utils.seconds_to_datetime(data['time'], ref)
    meta['time']['long_name'] = ''
    meta['time']['units'] = ''

    data['secs1970'] = dt_utils.datetime_to_seconds(data['time'])
    meta['secs1970'] = {}

    return data, meta

def convert_variables(data, meta, setup={}):
    """Do handy variable conversions and return data as dict.
    
        References
        ----------
        [1] Radiometer Physics note on offsets in W-band cloud radar gain
        offsets. 08/2018. 5-page pdf files should be with the documentation.
        Otherwise, ask Mario Mech.
    """
    ###################################################
    # UNITS                                           #
    ###################################################
    # lwp
    if 'lwp' in data:
        data['lwp'] *= 1e-3     # g m-2 --> kg m-2

    ############################################################
    # signal correction                                        #
    ############################################################
    # Extend this section to other time intervals for which you know whether or
    # not a correction needs to be applied.
    #
    # BE CAREFUL! -- Make sure, the program only passes this section for times
    # that you are certain about whether they need correction or not.
    if 'ze' in data:
        time_file = data['time'][1]
        if time_file < dt.datetime(2019, 1, 1):
            # Factor 2 / "3dB"-Correction
            # ---------------------------
            # The RPG software before version 5.11 issues the reflectivity in a
            # wrong way. (as of 2018-11-01)
            data['ze'] *= 2
        elif time_file > dt.datetime(2019, 3, 7):
            # After this date, the RPG software has been fixed. No correction
            # is necessary anymore.
            pass
        else:
            raise NotImplementedError(
                'Please check whether the correction has to be applied ' +
                'after this date and modify code accordingly.'
                )

    ###################################################
    # rename variables                                #
    ###################################################
    # renaming list. structure:
    # [(old, new), (old, new), ...]
    move_table = [                      
            ('vm', 'vm_raw'),
            ('sw', 'v_sigma'),
            ('skew', 'v_skew'),
            ('ze', 'Ze_raw'),
            ('SLv', 'Ze_sensitivity'),
            ]

    # do the renaming (variable by variable):
    for line in move_table:
        oldkey, newkey = line
        if oldkey not in data:
            continue
        data[newkey] = data[oldkey]
        del data[oldkey]

    ###################################################
    # Nyquist Doppler speed                           #
    ###################################################
    # make DoppMax a vector of same length as range
    if 'nqv' in data:
        dm = data['nqv']

        # indexing from matlab to python (start counting at 0)
        range_offsets = data['range_offsets'] - 1

        # initialize
        dm_new = np.nan * np.ones_like(data['range'])
        for n, offset in enumerate(range_offsets):
            dm_new[offset:] = dm[n]

        data['nqv'] = dm_new

        del dm, dm_new

    return data, meta

def handle_nans(data, meta, setup={}):
    """Convert invalid values to nans and return data as dict."""
    ###################################################
    # -999 -> NAN                                     #
    ###################################################
    nan_keys = ('ze', 'vm', 'sw', 'skew', 'lwp', 'tb')
    for key in data:
        if key not in nan_keys:
            continue
        idx = data[key] == -999
        data[key][idx] = np.nan

    return data, meta
