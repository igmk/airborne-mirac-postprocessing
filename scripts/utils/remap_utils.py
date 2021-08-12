#!/usr/bin/python2
"""Interpolate data to new height grid and remap to vertical columns."""

import warnings
import numpy as np
from scipy.interpolate import interp1d

from aa_lib import geometry as geom
from aa_lib import string_utils

###################################################
# MAIN                                            #
###################################################
def interpolate_to_height_grid(data, setup, alt_out, varnames_intp=None):
    """Return a dict of of variables interpolated to new height grid.

        Parameters
        ----------
        data : dict
            with variables on (time, range)-grid
        setup : dict
        alt_out : 1d-array
            the altitude array onto which data is to be interpolated
        varnames_intp : iterable or None, optional
            list of variable names to interpolate. None means all variables.
            Default: None

        Returns
        -------
        data : dict
            with variables on (time, alt)-grid

        History
        -------
        2018-11-02 (AA): Included option for categorical data
        2018-01-05 (AA): Created
    """
    ###################################################
    # FIND VARIABLES TO INTERPOLATE                   #
    ###################################################
    if varnames_intp is None:
        Nt, Nr = np.shape(data['lon'])
        varnames_intp = []
        for vn in data.keys():
            shape = np.shape(data[vn])
            if Nt not in shape:
                continue
            if Nr not in shape:
                continue
            varnames_intp.append(vn)

    ###################################################
    # EXPAND RANGE                                    #
    ###################################################
    Nt = len(data['secs1970'])
    r = data['range']
    range_large = np.repeat(np.expand_dims(r, 0), Nt, 0)

    ###################################################
    # INTERPOLATE                                     #
    ###################################################
    # Here, an interpolation function is created which is called with two
    # arguments only: 
    #     - the variable values x 
    #     - intp_kind : the kind of interpolation ('linear', 'nearest', ...)
    # 
    # (`alt` and `alt_out` don't change for different variables)
    alt = data['alt'][:]
    f = lambda x, intp_kind: interpolate_to_height_grid_one_variable(
            alt, x, alt_out, kind=intp_kind)

    data_intp = {}
    for vn in varnames_intp:
        # check whether data is categorical (e. g. flag):
        if is_categorical(vn):
            kind = 'nearest'
        else:
            kind = 'linear'

        data_intp[vn] = f(data[vn], kind)

    ###################################################
    # LINK OTHER KEYS                                 #
    ###################################################
    varnames = data.keys()
    varnames_ignore = varnames_intp
    for varname in varnames:
        if varname in varnames_ignore:
            continue
        data_intp[varname] = data[varname]

    data_intp['range'] = f(range_large, 'linear')
    data_intp['alt'] = alt_out

    return data_intp

def remap_data_spatially(data, setup, varnames_remap=None, idx_time=None):
    """Return dict of variables remapped onto vertical columns.

        These variables are added:

        lon_target, lat_target, secs1970_target
        time_diff_target, horizontal_distance_target

        Parameters
        ----------
        data : dict
        setup : dict
        varnames_remap : list of str
            variable names to be remapped
        idx_time : list of int
            time indices to be remapped

        Returns
        -------
        data : dict
    """
    Nt = len(data['secs1970'])
    Nz = len(data['alt'])

    ###################################################
    # DEFAULT                                         #
    ###################################################
    if varnames_remap is None:
        varnames_remap = []
        for vn in data.keys():
            shape = np.shape(data[vn])
            if Nt not in shape:
                continue
            if Nz not in shape:
                continue
            varnames_remap.append(vn)

    if idx_time is None:
        idx_time = range(Nt)

    ###################################################
    # INITIALIZE                                      #
    ###################################################
    zeros = np.zeros((Nt, Nz))
    lon_target = np.nan * zeros
    lat_target = np.nan * zeros
    secs1970_target = np.nan * zeros
    time_diff_target = np.nan * zeros
    horizontal_distance_target = np.nan * zeros

    data_out = {}
    for varname in varnames_remap:
        shape_in = data[varname].shape
        shape_out = (Nt, Nz) + shape_in[2:]
        data_out[varname] = np.nan * np.zeros(shape_out)

    secs_inc = (data['secs1970'][-1] - data['secs1970'][0]) / (Nt - 1.)

    assert secs_inc > 0

    if 'chrono' in setup.keys():
        chrono = setup['chrono']
        chrono_inc = 1. / len(idx_time)
        chrono_nstart = chrono.get_count()
        progress = 0.
        
    else:
        chrono = None

    vas_deg = data['sensor_view_angle']
    sin_va_default = np.sin(np.radians(np.nanmax(vas_deg)))
    v_sensor_default = np.nanmax(data['v_sensor'])

    assert np.isfinite(sin_va_default)
    assert np.isfinite(v_sensor_default)
    assert v_sensor_default > 0

    for t in range(Nt):
        if t not in idx_time:
            continue

        lonp = data['lon_sensor'][t]
        latp = data['lat_sensor'][t]
        secs = data['secs1970'][t]

        alt_sensor = data['alt_sensor'][t]        # (m) aircraft altitude
        v_sensor = data['v_sensor'][t]            # (m/s) aircraft speed
        va_deg = data['sensor_view_angle'][t]     # (deg) viewing angle
        sin_va = np.sin(np.radians(va_deg))         # sine of viewing angle

        if np.isnan(sin_va):
            sin_va = sin_va_default

        if np.isnan(v_sensor):
            v_sensor = v_sensor_default

        if v_sensor == 0:
            continue

        if np.isnan(alt_sensor):
            continue

        assert np.isfinite(v_sensor)
        assert v_sensor > 0
        assert np.isfinite(alt_sensor)
        assert np.isfinite(sin_va)

        # progress bar
        if chrono is not None:
            progress += chrono_inc
            chrono.set_count(chrono_nstart + progress)
            message = ' ' * 11 + 'remapping (%s) ...\n' % \
                    string_utils.percentage_string(progress) + \
                    ' ' * 11 + \
                    string_utils.progress_bar(
                            progress, 60, fillcolor=string_utils._YELLOW)
            chrono.show(message, wrap=False)

        for z in range(Nz):
            ###################################################
            # GET TIME INDICES                                #
            ###################################################
            # select only as many time steps as needed. They are about
            # delta_t = sin(va) * (alt_sensor - alt_target) / v_sensor
            # into the future. Use some more to be tolerant to roll angles and
            # curves.
            alt_target = data['alt'][z]
            delta_secs = np.abs(sin_va * (alt_sensor - alt_target) / v_sensor)
            delta_t = delta_secs / secs_inc
            dt_lo = int(np.ceil(delta_t * 0.5))  # a bit into the past
            dt_hi = int(np.ceil(delta_t * 2.0))  # tolerance factor 2
            tlo = max(t - dt_lo, 0)
            thi = min(t + dt_hi, Nt)

            ###################################################
            # FIND CLOSEST TARGET                             #
            ###################################################
            lons_compare = data['lon'][tlo:thi, z]
            lats_compare = data['lat'][tlo:thi, z]

            X = geom.nearest_neighbour_on_sphere(
                    lonp, latp, lons_compare, lats_compare)

            nlon, nlat, idx, value, dist = X
            if idx is None:
                continue
            
            tt = idx[0] + tlo       # time index of nearest point

            lon_target[t, z] = nlon
            lat_target[t, z] = nlat
            horizontal_distance_target[t, z] = dist

            secs_target = data['secs1970'][tt]
            secs1970_target[t, z] = secs_target
            time_diff_target[t, z] = secs_target - secs

            for varname in varnames_remap:
                data_out[varname][t, z] = data[varname][tt, z]

    ###################################################
    # LINK OTHER KEYS                                 #
    ###################################################
    varnames = data.keys()
    varnames_ignore = varnames_remap
    for varname in varnames:
        if varname in varnames_ignore:
            continue
        data_out[varname] = data[varname]

    data_out['lon'] = lon_target
    data_out['lat'] = lat_target
    data_out['secs1970_target'] = secs1970_target
    data_out['horizontal_distance_target'] = horizontal_distance_target
    data_out['time_diff_target'] = time_diff_target
    
    if chrono is not None:
        chrono.set_count(chrono_nstart + 1)

    return data_out

###################################################
# HELPERS                                         #
###################################################
def get_output_height_grid(data, setup):
    """Return a 1D-array of altitudes."""
    agt = setup['alt_grid_type']

    if agt == 'file_constant':
        alt_max = np.nanmax(data['alt'])
        assert alt_max < 10e3

        va_mean_deg = np.nanmean(data['sensor_view_angle'])
        assert np.isfinite(va_mean_deg)

        r = data['range']
        cos_va = np.cos(np.radians(va_mean_deg))
        alt_out = alt_max - r[::-1] * cos_va

    elif agt == 'globally_constant':
        alt_min = setup['alt_min']     # (m)
        alt_max = setup['alt_max']     # (m)
        alt_inc = setup['alt_inc']     # (m)
        alt_out = np.arange(alt_min, alt_max, alt_inc)

    else:
        raise NotImplementedError('alt_grid_type not implemented: %s' % agt)

    return alt_out

def interpolate_to_height_grid_one_variable(
        alt_in, val_in, alt_out, kind='linear'
        ):
    """Return one interpolated variable as array.

        Parameters
        ----------
        alt_in : np.ndarray (N, M)
            Altitude matrix on the (time, range)-grid
        val_in : np.ndarray (N, M)
            Values on the (time, range)-grid
        alt_out : np.ndarray (Mnew,)
            Output altitude array
        kind : str, optional
            Specifies the kind of interpolation as a string ('linear',
            'nearest', 'zero', 'slinear', 'quadratic', 'cubic', 'previous',
            'next', where 'zero', 'slinear', 'quadratic' and 'cubic' refer to a
            spline interpolation of zeroth, first, second or third order;
            'previous' and 'next' simply return the previous or next value of
            the point) or as an integer specifying the order of the spline
            interpolator to use. Default is 'linear'.
            Default: 'linear'

            Dimension interpretation:
            N : time dimension
            M : range dimension
            Mnew : alt dimension

        Returns
        -------
        val_out : np.ndarray (N, Mnew)

        History
        -------
        2018-11-02 (AA): Included optional `kind` parameter
        2018-07-04 (AA): Implemented higher dimensional case
        2018-01-05 (AA): Created
    """
    ###################################################
    # NOMENCLATURE                                    #
    ###################################################
    # ------------
    # N : dimension of axis 0
    # M : dimension of axis 1
    # K : dimension of axis 2  (if present)
    # i : in
    # o : out

    ###################################################
    # INPUT CHECK                                     #
    ###################################################
    assert np.shape(val_in)[:2] == np.shape(alt_in)
    assert len(np.shape(alt_out)) == 1
    
    ###################################################
    # RETRIEVE VARIABLES                              #
    ###################################################
    N, Mi = np.shape(alt_in)

    Mo = len(alt_out)
    shape_in = np.shape(val_in)
    shape_out = (N, Mo) + shape_in[2:]

    xo = alt_out
    yo = np.nan * np.zeros(shape_out)

    ###################################################
    # HIGHER DIMENSION INPUT                          #
    ###################################################
    # call function recursively if more than two dimensions:
    if len(shape_out) > 2:
        K = shape_out[2]
        for k in range(K):
            yo[:, :, k] = interpolate_to_height_grid_one_variable(
                    alt_in, val_in[:, :, k], alt_out)
        return yo

    ###################################################
    # INTERPOLATE                                     #
    ###################################################
    # catch runtime warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        for n in range(N):
            xi = alt_in[n]      # independent input variable
            yi = val_in[n]      # dependent input variable
            f = interp1d(
                    xi, yi, kind=kind, copy=False, assume_sorted=False,
                    bounds_error=False)
            yo[n] = f(xo)

    return yo

def is_categorical(varname):
    """Return a bool saying whether data is categorical.

        Parameters
        ----------
        varname : str

        Returns
        -------
        bool
    """
    categorical = False

    if 'flag' in varname:
        categorical = True

    return categorical
