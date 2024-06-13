#!/usr/bin/python
"""Remove subsurface reflections.

    The following steps are performed:

    - Locate the mirrored signal and its extent below the surface peak in a
      specified time segment. Save position and value of strongest signal
      of the sub-surface peak.
    
    - Substract this value from both peaks above and below the surface.
      (LK: maybe it is good to asume a weighting, I'm not sure!)
    
    - Remove negative values caused by this procedure.

    Authors
    -------
    [see parent module]

    History
    -------
    2018-12-12  (AA) Change filter name.

    2018-11-21  (AA) Add checks.

    2018-11-21  (AA) Complete re-implementation.

    2018-11-21  (AA) Exported from parent module

    [earlier]   [see parent module]
"""

# standard modules
import os
from copy import deepcopy as copy
import datetime as dt
import warnings

# PyPI modules
import numpy as np
from scipy.signal import argrelextrema

# local library
import aa_lib.tables as tab

# constants
_correction_date_table ='setup/mirac/first_correction.tab'
NAME = 'subsurface reflection filter'

_DEBUG = False

###################################################
# MAIN                                            #
###################################################
def check_input(data, setup):
    """Do nothing if input is ok, throw error otherwise."""
    # check for necessary setup parameters
    keys = ('subsurface_reflection_filter_full_width_time',
            'subsurface_reflection_filter_full_width_range',
            'subsurface_reflection_filter_min_frac_finite',
            'subsurface_reflection_filter_min_dist_to_surface',
            'subsurface_reflection_filter_max_dist_to_surface',
            )
    for key in keys:
        if key not in setup:
            raise KeyError('Missing setup parameter: %s' % key)

    # retrieve variables
    fw_t = setup['subsurface_reflection_filter_full_width_time']
    fw_r = setup['subsurface_reflection_filter_full_width_range']
    min_frac = setup['subsurface_reflection_filter_min_frac_finite']
    min_dist = setup['subsurface_reflection_filter_min_dist_to_surface']
    max_dist = setup['subsurface_reflection_filter_max_dist_to_surface']

    # fw_t must be a positive odd int
    assert isinstance(fw_t, int)
    assert fw_t >= 1
    assert fw_t % 2 == 1

    # fw_r must be a positive odd int
    assert isinstance(fw_r, int)
    assert fw_r >= 3
    assert fw_r % 2 == 1

    # min_frac must be a sensible fraction
    assert isinstance(min_frac, float)
    assert 0 < min_frac <= 1

    # distance to surface
    assert isinstance(min_dist, int)
    assert isinstance(max_dist, int)
    assert 0 < min_dist < max_dist

def main(data, setup):
    """Return a dict.

        Description see module docstring.

        Parameters
        ----------
        data : dict
        setup :dict

        Returns
        -------
        data : dict
            Below-surface reflexion removed from 'ze'.
    """
    if _DEBUG:
        setup['chrono'].debug_warning()

    # check whether this file is in the look-up table
    #do_anything = check_whether_to_remove_mirrored_signal(data, setup)
    #if not do_anything:
    #    zeros = np.zeros_like(data['ze'], dtype=bool)
    #    data['flag_subsurface_reflection_filter'] = zeros
    #    return data

    # ========== retrieve variables and parameters  ====== #
    fw_t = setup['subsurface_reflection_filter_full_width_time']
    fw_r = setup['subsurface_reflection_filter_full_width_range']
    Ze = data['ze']
    shape = np.shape(Ze)
    Nt, Nr = shape

    # ==================================================== #

    # initialize
    Ze_corr = np.nan * np.ones_like(Ze)

    hw_t = fw_t // 2    # half width
    for t in range(Nt):
        if hw_t <= t < Nt - hw_t:
            # regular case (far from borders)
            pass
        else:
            # close to border --> don't do anything
            Ze_corr[t] = Ze[t]
            continue
        
        # cut out a time section
        tlo = t - hw_t
        thi = t + hw_t + 1
        Ze_section = Ze[tlo:thi]
        Ze_column = Ze[t]


        r_max, dist_lo, dist_hi, Ze_refl = locate_mirrored_signal(
                Ze_column, Ze_section, data, setup)

        Ze_col_filtered = substract_mirrored_signal(
                Ze_column, r_max, dist_lo, dist_hi, Ze_refl)

        Ze_corr[t] = Ze_col_filtered

    flag = (Ze_corr != Ze) & ~np.isnan(Ze)
    data['ze'] = Ze_corr
    data['flag_subsurface_reflection_filter'] = flag

    return data


###################################################
# HELPERS                                         #
###################################################
#=====================================
# Setup suggested by LK on 2018-10-08:
# ====================================
# fw_t = 25
# min_dist_to_surface
# -------------------
# (formerly called `find_mirror`)
# 12 or 10 (must be chosen in dependence of the chirp table)

def remove_mirrored_signal_old(data, setup):
    """Remove reflexion from below the surface.

        Parameters
        ----------
        Ze : 2d-array
            reflectivity
        fw_t : int
            full width of the window in time dimension

        Returns
        -------
        Ze_corr : 2d-array
            Signal with below-surface reflexion removed.

        Description
        -----------
        (originally by LK, rephrased by AA)

        The following steps are performed:
    
        - Locate the mirrored signal and its extent below the surface peak in a
          specified time segment.
        
        - Save the strongest signal of the sub-surface peak.
        
        - Substract this value from both peaks above and below the surface.
          (LK: maybe it is good to asume a weighting, I'm not sure!)
        
        - Remove negative values caused by this procedure.
    """
    raise Exception('Function deprecated.')
    # TODO: put this in the setup file
    hw_r = 2

    # check whether this file is in the look-up table
    #do_anything = check_whether_to_remove_mirrored_signal(data, setup)
    #if not do_anything:
    #    data['flag_mirrored_signal'] = np.zeros_like(data['ze'], dtype=bool)
    #    return data

    # ========== retrieve variables and parameters  ====== #
    fw_t = setup['harmonics_filter_full_width_time']
    Ze = data['Ze_raw']
    shape = np.shape(Ze)
    Nt, Nr = shape
    # ==================================================== #

    # initialize
    Ze_corr = np.nan * np.ones_like(Ze)

    hw_t = fw_t // 2    # half width
    tmax = Nt - fw_t

    for t in range(tmax):
        tlo = t
        thi = t + fw_t
        values = Ze[tlo:thi]

        amount, v_range = diff_surf_dist(values)

        Ze_corr1 = find_extrema_move(values, amount, v_range, hw_t, hw_r, 1,
                setup=setup)

        t_center = t + hw_t
        Ze_corr[t_center] = Ze_corr1

    flag = (Ze_corr != Ze) & ~np.isnan(Ze)
    data['ze'] = Ze_corr
    data['flag_mirrored_signal'] = flag

    return data

def locate_maximum_signal(Ze_column):
    r_max = np.nanargmax(Ze_column)
    Z_max = np.nanmax(Ze_column)

    return r_max, Z_max

def locate_mirrored_signal(Ze_column, Ze_section, data, setup):
    """Return position of surface peak and subsurface reflection.

        Parameters
        ----------
        Ze_section : 2d-array
            (time, range)-section of Ze
        data : dict
        setup : dict

        Returns
        -------
        r_max : int
            index of the global maximum (surface peak)
        dist_lo : int
            distance from global maximum to beginning near bound of the
            reflection artifact
        dist_hi : int
            distance from global maximum to beginning far bound of the
            reflection artifact
    """
    min_dist_surface = get_min_dist_to_surface(data, setup)
    max_dist_surface = get_max_dist_to_surface(data, setup)
    valid = np.isfinite(Ze_section)
    
    # test Ze_column for All-NaN slices
    nan_column = np.where(np.isnan(Ze_column))
    
    if len(nan_column[0]) == len(Ze_column):
       r_max = np.nan
       r_max_val = np.nan
       return r_max, 0, 0, np.nan

    # position of signal peak
    r_max = np.nanargmax(Ze_column)
    r_max_val = np.nanmax(Ze_column)
    dBZ = 20
    if r_max < 10**(dBZ/10):
    	return r_max, 0, 0, np.nan


    # 1d-histogram (sum of valid values along time axis)
    hist = np.sum(valid, axis=0)

    # maximum allowed range for reflection
    rlo = r_max + min_dist_surface
    rhi = r_max + max_dist_surface + 1
    if rhi > len(Ze_column):
        rhi = len(Ze_column) + 1

    # position of reflection center
    interval = hist[rlo:rhi]
    if len(interval) == 0:
        return r_max, 0, 0, np.nan

    find_zero = np.where(interval == 0)
    idx_zeros = find_zero[0] 
    if len(idx_zeros) != 0:
        first_zero = np.argmin(idx_zeros) # artifact needs to be separated from surface signal
        interval[0:idx_zeros[first_zero]+1] = 0
        r_refl_peak_rel = np.argmax(interval)
        
        if r_refl_peak_rel > first_zero:
            r_refl_peak = rlo + r_refl_peak_rel
    
            # reflection signal upper bound
            upper_part = hist[r_refl_peak:rhi+1]
            r_refl_upper_bound_rel = np.argmin(upper_part)
            r_refl_upper_bound = r_refl_peak + r_refl_upper_bound_rel
            dist_hi = r_refl_upper_bound - r_max
    
            # reflection signal lower bound
            lower_part = hist[rlo:r_refl_peak+1]
            lower_part_inverse = lower_part[::-1]
            idx_inverse = np.argmin(lower_part_inverse)
            r_refl_lower_bound = r_refl_peak - idx_inverse
            dist_lo = r_refl_lower_bound - r_max
               
            # strongest reflection signal
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', RuntimeWarning)
            Ze_refl = np.nanmax(Ze_section[:, r_refl_lower_bound:r_refl_upper_bound+1])
            
        else:    
             return r_max, 0, 0, np.nan
         
    else:    
        return r_max, 0, 0, np.nan

    return r_max, dist_lo, dist_hi, Ze_refl

def substract_mirrored_signal(Ze_column, r_max, dist_lo, dist_hi, Ze_refl):
    Ze_col_out = copy(Ze_column)

    if np.isnan(Ze_refl):
        return Ze_col_out
    
    # remove below ground
    rlo = r_max + dist_lo
    rhi = r_max + dist_hi
    #print('1')
    #print(Ze_col_out[rlo:rhi])
    Ze_col_out[rlo:rhi] -= Ze_refl
    #print('2')
    #print(Ze_col_out[rlo:rhi])
    # remove above ground
    rlo = r_max - dist_hi
    rhi = r_max - dist_lo

    Ze_col_out[rlo:rhi] -= Ze_refl

    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        negatives = Ze_col_out <= 0
        Ze_col_out[negatives] = np.nan

    return Ze_col_out

#def check_whether_to_remove_mirrored_signal(data, setup):
#    """Return True if file starting with this time needs first correction.
#
#        Parameters
#        ----------
#        time : datetime.datetime
#            first time step in file
#
#        Returns
#        -------
#        bool
#            True if correction is to be done, False otherwise
#    """
#    # TODO: Can we automize this instead of using a manually created look-up
#    # table?  (AA)
#    #
#    # This can be done in the following way:
#    # 1) Define *objective* criteria to include a file in the look-up table.
#    # 2) Translate these criteria into code.
#    # 3) Give plausible scientific reasons for your criteria.
#
#    fmt = '%Y-%m-%d %H:%M:%S'            # time stamp format in the text file
#    
#    # name of the file containing a list of timestamps where correction is to
#    # be done:
#    filename = _correction_date_table
#    if not os.path.isfile(filename):
#        raise IOError('Cannot find correction table: %s' % filename)
#
#    time = data['time'][0]
#    
#    # read times where corrections are to be applied from text file
#    columns = tab.read_column_list(filename, sep='@')
#
#    # column that contains the time stamps
#    column = columns[0]
#
#    # str --> dt.datetime
#    times = [dt.datetime.strptime(row, fmt) for row in column]
#
#    # check whether `time` is in this list
#    return (time in times)


###################################################
# OLD (deprecated)                                #
###################################################
def find_extrema_move(
        Ze, artifact_distribution, v_range, t_center, hw_range,
        data_mass_parameter, min_dist_to_surface=None,
        max_dist_to_surface=None, setup={}):
    """<Do this and return that.>

        Parameters
        ----------
        Ze : <type>
            <meaning>
        artifact_distribution : <type>
            <meaning>
        v_range : <type>
            <meaning>
        t_center : <type>
            <meaning>
        hw_range : int
            half width in range direction of the window which is used to
            determine whether the pivot is located on a maximum
        data_mass_parameter : int
            <meaning>
        min_dist_to_surface : int
            if the sub-surface reflection is closer than this to the surface,
            then nothing is done.
        max_dist_to_surface : int
            if the sub-surface reflection is farther than this to the surface,
            then nothing is done.

        Returns
        -------
        <name> : <type>
            <meaning>
    """
    # TODO  Meaningful function docstring missing. Replace all <...>
    # placeholders appropriately, then delete this comment. (AA)

    # TODO: This whole function is very tough to understand. Can we rewrite it
    # is such that a reader other than the author can understand it? (AA)

    chrono = setup['chrono']

    if min_dist_to_surface is None:
        min_dist_to_surface = get_min_dist_to_surface(Ze)

    if max_dist_to_surface is None:
        max_dist_to_surface = get_max_dist_to_surface(Ze)

    Nt, Nr = np.shape(Ze)
    Ze_corr = copy(Ze)
    shape = np.shape(artifact_distribution)
    lang = len(artifact_distribution)

    i_out = int(t_center)

    idx_low_amount = (artifact_distribution <= data_mass_parameter)
    artifact_distribution[idx] = 0

    peaky = np.nan * np.ones(shape)

    # Note: In an earlier version, we used order=1
    idx_peak_scipy = argrelextrema(artifact_distribution, np.greater_equal, order=hw_range)

    # TODO: Describe what is happening in the following loop, then delete this
    # comment. (AA)
    # Find peak in range-direction
    imin = hw_range
    imax = lang - hw_range
    for i in range(imin, imax):
        ilo = i - hw_range
        ihi = i + hw_range + 1
        art_interval = artifact_distribution[ilo:ihi]
        art_max = np.max(art_interval)
        art_current = artifact_distribution[i]

        if art_current != art_max:
            continue
        if art_max == 0:
            continue
        peaky[i] = art_current

    idx_peak_homemade = np.where(np.isfinite(peaky))
    idx_peak = np.intersect1d(idx_peak_homemade, idx_peak_scipy)

    # TODO: What is the meaning of this warning? It is displayed 100+ times per
    # file.
    if len(idx_peak) == 0:
        chrono.warning('No mirror artifact to correct data.')
        return Ze_corr[i_out, :]

    # assume that the reflection is the last peak
    idx_reflection = np.max(idx_peak)

    # position of signal maximum
    idx_max = np.where(v_range == 0)

    if idx_reflection < int(idx_max[0]) + min_dist_to_surface:
        # peak too close to surface
        return Ze_corr[i_out, :]

    dummy = np.abs(idx_low_amount - idx_reflection)
    id1 = np.argmin(dummy)
    idd1 = idx_low_amount[id1]


    above = (idx_low_amount <= idx_low_amount[id1])
    # TODO: What is this magic number? (AA)
    idx_low_amount[above] = 999

    id2 = np.argmin(np.abs(idx_low_amount - idx_reflection))
    idd2 = idx_low_amount[id2]

    distance_to_surface = idx_reflection - idx_max
    maxZe_mean = np.round(np.nanmean(np.nanargmax(Ze, 1)))

    maxdiff1 = (idd1 - idx_max) + maxZe_mean

    maxdiff2 = idd2 - idx_max + maxZe_mean
    vall = Ze[:, int(maxdiff1) - 1:int(maxdiff2)]
    vall_m = vall

    # Maxima near observation boundary
    if maxdiff2 > Nr:
        return Ze_corr[i_out, :]

    high_wert = np.nanmax(np.nanmax(vall_m))
    idm = np.where(vall_m == high_wert)
    Ze_subtract = vall[idm]
    subtract_val = Ze_subtract

    if len(subtract_val) == 0:
        return Ze_corr[i_out, :]

    elif distance_to_surface > max_dist_to_surface:
        return Ze_corr[i_out, :]

    # Something happens here, but what? (AA)
    subtract_val[np.isnan(subtract_val)] = 0

    ilo = int(maxdiff1 - 2*distance_to_surface - 1)
    ihi = int(maxdiff2 - 2*distance_to_surface)
    Ze_corr[:, ilo:ihi] = Ze[:, ilo:ihi] - subtract_val #Ze_average

    ilo = int(maxdiff1 - 1)
    ihi = int(maxdiff2)
    Ze_corr[:, ilo:ihi] = Ze[:, ilo:ihi] - subtract_val #Ze_average

    return Ze_corr[i_out, :]

def diff_surf_dist(Ze):
    """Return distribution <of what?> vs. distance to signal peak.

        Parameters
        ----------
        Ze : 2d-array
            reflectivity. Axes: time, range

        Returns
        -------
        amount : 1d-array
            <meaning>
        v : 1d-array
            (gates) distance to signal peak
    """
    # TODO  Meaningful function docstring missing. Replace all <...>
    # placeholders appropriately, then delete this comment. (AA)

    shape = np.shape(Ze)
    Nt, Nr = shape

    # index of signal maximum for each time step
    rmax = np.expand_dims(np.nanargmax(Ze, 1), 1)

    # construct index matrix
    r_range = np.expand_dims(np.arange(Nr), 0)
    X = np.repeat(r_range, Nt, 0)

    # distance to reflectivity peak
    Diffmax = X - rmax

    findmin = np.min(Diffmax)
    findmax = np.max(Diffmax)

    v = np.arange(findmin, findmax)
    amount = np.nan * np.ones(len(v))

    for i in range(len(v)):
        idrangegate = np.where(Diffmax == v[i])
        radref = Ze[idrangegate]
        amount[i] = np.size(np.where(~np.isnan(radref)))

    return amount, v

def get_min_dist_to_surface(data, setup):
    """Return `min_dist_to_surface` as int."""
    # TODO: What is this and how does this depend on the chirp table? (AA)

    # Make this objective, verifiable and reproductable.
    #
    # This can be achieved in the following way:
    # 1) Define *objective* criteria for your decision.
    # 2) Give plausible scientific reasons for your criteria.
    # 3) Translate these criteria into code.

    return setup['subsurface_reflection_filter_min_dist_to_surface']

def get_max_dist_to_surface(data, setup):
    """Return `max_dist_to_surface` as int."""
    # TODO
    # Make this objective, verifiable and reproductable.
    #
    # This can be achieved in the following way:
    # 1) Define *objective* criteria for your decision.
    # 2) Give plausible scientific reasons for your criteria.
    # 3) Translate these criteria into code.

    return setup['subsurface_reflection_filter_max_dist_to_surface']
