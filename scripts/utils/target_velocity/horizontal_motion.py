#!/usr/bin/python
"""Compute x- and y-components of target velocity.

    Todo
    ----
    possibly replace matrix inversion by scipy.linalg.solve
"""

# built-in modules
from copy import deepcopy as copy
import itertools

# PyPI modules
import numpy as np
from numpy.linalg.linalg import LinAlgError

# AA's library
from aa_lib import datetime_utils
from aa_lib import geometry as geom
from aa_lib import string_utils

###################################################
# MAIN                                            #
###################################################
def compute_horizontal_motion(data, setup, idx_time=None, idx_range=None):
    """Compute x- and y-components and return a dict.

        Parameters
        ----------
        data : dict
            must contain
            'secs1970', 'alt', 'vm_r',
            'sensor_azimuth_angle', 'sensor_view_angle'
        setup : dict
        idx_time : list of int
            time indices to be decomposed
        idx_range : list of int
            range indices to be decomposed

        Returns
        -------
        data : dict
            These variables are added:
            vm_x : array
                target velocity in x-direction (eastward wind component)
            vm_y : array
                target velocity in y-direction (northward wind component)
            vm_x_unc, vm_y_unc : array
                uncertainties

        History
        -------
        2018-03-12 (AA): Created
        2018-05-16 (AA): Accurate indexing on temporal, vertical and horizontal
                         distance
    """
    chrono = setup['chrono']
    if chrono is not None:
        chrono_time_step = chrono.time_step
        chrono.time_step = 0.1

    Nt, Nr, Nf = np.shape(data['vm_r'])

    weighted = bool(setup['wind_averaging_use_weights'])

    ###################################################
    # DEFAULT                                         #
    ###################################################
    if idx_time is None:
        idx_time = range(Nt)

    if idx_range is None:
        idx_range = range(Nr)

    ###################################################
    # AVERAGING TOLERANCES                            #
    ###################################################
    data = compute_wind_averaging_tolerances(data, setup)

    ###################################################
    # INITIALIZE                                      #
    ###################################################
    vx = np.nan * np.zeros((Nt, Nr, Nf))
    vy = np.nan * np.zeros((Nt, Nr, Nf))

    vx_unc = np.nan * np.zeros((Nt, Nr, Nf))
    vy_unc = np.nan * np.zeros((Nt, Nr, Nf))

    inv = np.linalg.inv

    # broadcast time-variables to 2d (for performance reasons)
    make_2d = lambda x: np.repeat(np.expand_dims(x, 1), Nr, 1)
    azi_2d = make_2d(np.radians(data['sensor_azimuth_angle']))
    va_2d = make_2d(np.radians(data['sensor_view_angle']))

    data['secs1970'] = datetime_utils.datetime_to_seconds(data['time'])

    # nan-index
    idx_nonnan_2d = get_nonnan_idx(data, setup)

    ###################################################
    # CHRONOMETER                                     #
    ###################################################
    chrono.issue('target velocity: compute (horizontal) wind...')
    n = -1
    N = Nt * Nr 
    count_start = chrono.get_count()
    count_end = count_start + 1

    nt_last = None
    for nt, nr in itertools.product(idx_time, idx_range):
        # ========== chronometer ========================= #
        if nt != nt_last and chrono is not None:
            progress = 1. * nt / Nt
            ps = string_utils.percentage_string(progress)
            pb = string_utils.progress_bar(
                    progress, 60, fillcolor=string_utils._YELLOW)
            message = 'Decompose target velocity %s\n%s' % (ps, pb)
            chrono.set_count(count_start + progress)
            chrono.show(message, force=False)
        nt_last = nt
        # ================================================ #

        if not idx_nonnan_2d[nt, nr]:
            # some variable is missing (usually vm_r)
            continue

        # ========== index and weights  ================== #
        idx = copy(idx_nonnan_2d)
        idx, weights = get_sample_indices(
            data, setup, nt, nr, idx, weighted=weighted)
        # ================================================ #

        # extract indexed variables
        azi = azi_2d[idx]
        va = va_2d[idx]

        # ======= THIS IS WHERE THE MATHS HAPPENS ======== #
        # LEAST SQUARE SOLUTION
        # ---------------------

        # forward operator
        I = np.sum(idx)
        M = np.nan * np.ones((I, 3))
        M[:, 0] = np.sin(va) * np.sin(azi)
        M[:, 1] = np.sin(va) * np.cos(azi)
        M[:, 2] = - np.cos(va)

        if weighted:
            W = np.diag(weights[idx])
            MTW = M.T.dot(W)
        else:
            MTW = M.T

        # ========== uncertainty  ======================== #
        # (AA 2018-07-12: to my surprise, this is independent of v_r)
        try:
            v_unc = inv(MTW.dot(M))

            # TODO: can this be replaced by scipy.linalg.solve? (more efficient)
        except LinAlgError:
            v_unc = np.nan * np.ones((3, 3))

        vx_unc[nt, nr, :] = v_unc[0, 0]
        vy_unc[nt, nr, :] = v_unc[1, 1]
        # ================================================ #

        # ========== value =============================== #
        # compute solution for each of the different v_r candidates
        for nf in range(Nf):
            vr = data['vm_r'][:, :, nf][idx]

            # value
            v = v_unc.dot(MTW).dot(vr)

            # average horizontal motion within the sample population
            vx[nt, nr, nf] = v[0]
            vy[nt, nr, nf] = v[1]
        # ================================================ #

        # DEBUG
        DEBUG = False
        if DEBUG:
            chrono.debug_warning('WARNING: DEBUG-mode in %s' % __name__)
            break

    ###################################################
    # SOME MORE VARIABLES                             #
    ###################################################
    # ========== wind speed ============================== #
    # value
    wind_speed = np.sqrt(vx**2 + vy**2)

    # uncertainty
    radicand = (vx * vx_unc)**2 + (vy * vy_unc)**2
    wind_speed_unc = np.sqrt(radicand) / np.abs(wind_speed)

    # ========== wind direction ========================== #
    # value
    wind_to_direction = np.arctan2(vx, vy)

    # uncertainty
    radicand = (vy * vx_unc)**2 + (vx * vy_unc)**2
    num = np.sqrt(radicand)
    den = vx**2 + vy**2
    wind_to_direction_unc = num / den

    ###################################################
    # WRITE TO DICT                                   #
    ###################################################
    data['vm_x'] = vx
    data['vm_y'] = vy
    data['vm_x_unc'] = vx_unc
    data['vm_y_unc'] = vy_unc

    data['wind_speed'] = wind_speed
    data['wind_speed_unc'] = wind_speed_unc
    data['wind_to_direction'] = np.degrees(wind_to_direction)
    data['wind_to_direction_unc'] = np.degrees(wind_to_direction_unc)

    if chrono is not None:
        chrono.set_count(count_end)
        chrono.time_step = chrono_time_step

    return data

###################################################
# HELPERS                                         #
###################################################
def compute_wind_averaging_tolerances(data, setup):
    """Add wind averaging tolerance to data and return as dict."""
    z = data['alt']
    kinds = ('time', 'vertical', 'horizontal')
    for kind in kinds:
        key = 'wind_averaging_' + kind
        coef = setup[key]
        tol = np.polyval(coef[::-1], z)
        tol[tol<0] = 0.
        data[key] = tol

    return data

###################################################
# INDEXING                                        #
###################################################
def get_nonnan_idx(data, setup, nf=0):
    """Return 2d-index of points where no relevant variable is none."""
    idx_va = ~ np.isnan(data['sensor_view_angle'])
    idx_azi = ~ np.isnan(data['sensor_azimuth_angle'])
    idx_t = idx_va & idx_azi

    idx_vm = ~ np.isnan(data['vm_r'][:, :, nf])

    return idx_vm & np.expand_dims(idx_t, 1)

def get_sample_indices(data, setup, nt, nr, idx, weighted=False):
    """Return a two 2d-boolean arrays.
    
        Parameters
        ----------
        idx : 2d-index
        weighted : bool
    """
    if weighted:
        w = 1. * idx
    else:
        w = None
    idx, w = index_for_time_tolerance(data, setup, nt, nr, idx, w)
    idx, w = index_for_z_tolerance(data, setup, nt, nr, idx, w)
    idx, w = index_for_xy_tolerance(data, setup, nt, nr, idx, w)
    return idx, w

def get_sample_indices_time(data, setup, nt, idx, weighted=False):
    raise Exception('Deprecated.')
    if weighted:
        w = 1. * idx
    else:
        w = None
    return index_for_time_tolerance(data, setup, nt, idx, w)

def index_for_time_tolerance(data, setup, nt, nr, idx_2d, weights_2d):
    """Return a 2d-boolean array."""
    # tol = setup['wind_averaging_time']
    tol = data['wind_averaging_time'][nt, nr]

    # SPECIAL CASE: ZERO TOLERACE
    if tol == 0:
        idx_self = idx_2d[nt, :]
        idx_2d &= False
        idx_2d[nt, :] = idx_self
        if weights_2d is not None:
            weights_2d_self = weights_2d[nt, :]
            weights_2d *= 0.
            weights_2d[nt, :] = weights_2d_self
        return idx_2d, weights_2d

    secs_all = data['secs1970']    # target time
    secs = secs_all[nt]

    dist = np.abs(secs_all - secs)

    # index
    idx_t = dist <= tol     # 1d
    idx_2d = idx_2d & np.expand_dims(idx_t, 1)

    # weight
    if weights_2d is not None:
        weights_1d = 1. - dist / tol
        zeros_1d = np.zeros_like(weights_1d)
        weights_1d = np.nanmax((zeros_1d, weights_1d), 0)
        weights_2d *= np.expand_dims(weights_1d, 1)

    return idx_2d, weights_2d

def index_for_z_tolerance(data, setup, nt, nr, idx_2d, weights_2d):
    """Return a 2d-boolean array."""
    tol = data['wind_averaging_vertical'][nt, nr]

    # SPECIAL CASE: ZERO TOLERACE
    if tol == 0:
        idx_self = idx_2d[nt, nr]
        idx_2d &= False
        idx_2d[nt, nr] = idx_self
        if weights_2d is not None:
            weights_2d *= 0.
            weights_2d[nt, nr] = 1.
        return idx_2d, weights_2d


    # retrieve variables
    alts = data['alt']   # target altitude

    # current points
    alt = alts[nt, nr]

    # other points
    alts_1d = alts[idx_2d]

    # distances
    dist_1d = np.abs(alts_1d - alt)

    # weights
    if weights_2d is not None:
        weights_1d = 1. - dist_1d / tol
        weights_1d[weights_1d < 0] = 0.
        weights_2d[idx_2d] *= weights_1d

    # index
    idx_1d = dist_1d <= tol
    idx_2d[idx_2d] = idx_1d

    return idx_2d, weights_2d

def index_for_xy_tolerance(data, setup, nt, nr, idx_2d, weights_2d):
    """Return a 2d-boolean array."""
    tol = data['wind_averaging_horizontal'][nt, nr]

    # SPECIAL CASE: ZERO TOLERACE
    if tol == 0:
        idx_self = idx_2d[nt, nr]
        idx_2d &= False
        idx_2d[nt, nr] = idx_self
        if weights_2d is not None:
            weights_2d *= 0.
            weights_2d[nt, nr] = 1.
        return idx_2d, weights_2d

    # REGULAR CASE
    lons = data['lon']
    lats = data['lat']

    # position of current point
    lon = lons[nt, nr]
    lat = lats[nt, nr]

    # position of other points
    lons_1d = lons[idx_2d]
    lats_1d = lats[idx_2d]

    # distances
    dist_1d = geom.distance_on_sphere(lon, lat, lons_1d, lats_1d)

    # weights
    if weights_2d is not None:
        weights_1d = 1 - dist_1d / tol
        weights_1d[weights_1d < 0] = 0.
        weights_2d[idx_2d] *= weights_1d

    # index
    idx_1d = dist_1d <= tol
    idx_2d[idx_2d] = idx_1d

    return idx_2d, weights_2d
