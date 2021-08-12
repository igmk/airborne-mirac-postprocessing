#!/usr/bin/python
"""Remove speckles from signal. Sub-module to mirac.py.

    Authors
    -------
    [see parent module]

    History
    -------
    2018-12-12  (AA) Changed filter name.

    2018-11-21  (AA) Exported from parent module

    [earlier]   [see parent module]
"""
#=====================================
# Setup suggested by LK on 2018-10-08:
# ====================================
# range_filter 
# ------------
# this must be always optimized in dependence of the chirp table:
# 20 for 154 range gates (25.05.2017), otherwise 35


# standard modules
import itertools

# PyPI modules
import numpy as np

NAME = 'speckle filter'
_DEBUG = False

###################################################
# MAIN                                            #
###################################################
def main(data, setup):
    """Do this and return that.

        Optimally, the sensitivity should behave like smoothed curved profiles
        without strong peaks. However, it was recognized that the horizontal
        artifact and the surface signal produce such peaks. Therefore, an
        averaged optimal sensitivity profile is developed from the sensitivity
        profiles.

        The following steps are performed:

        - First, the sensitivity is used to estimate the location of the
          horizontal artifact. This procedure works also if there is no
          mirrored signal below the surface.

        - This optimal sensitivity profile is subtracted from all sensitivity
          profiles, so that high differences can be located.

        - Afterwards, a Contour Frequency by Altitude Diagram (CFAD,
          range_gate_histogram) marks the estimated location of the horizontal
          artifact. Especially in this location a clutter filter / artifact
          filter should be used. Because the location is an estimation 15
          additional range gates are considered.

        - Now, there is an area to use the filter. The filter works as follows:
          It is taken a rectangle around a centered pixel. All reflectivities
          are set to 1 and the other pixels are set to 0. If there is a
          reflectivity pixel there must be a minimum fraction `min_frac` of
          reflectivity values in the total rectangle, so that the centered
          reflectivity pixel will be considered as true.

        Parameters
        ----------
        data : dict
        setup : dict with keys
            'fw_time' : int
            'fw_range' : int

        Returns
        -------
        data : dict
    """
    if _DEBUG:
        chrono = setup['chrono']
        chrono.debug_warning()
        data['flag_speckle_filter'] = np.zeros_like(data['ze'], dtype=bool)
        return data

    # ========== setup  ================================== #
    frac_finite_thresh = setup['speckle_filter_min_frac_finite']
    assert 0 < frac_finite_thresh < 1

    # window half widths
    fw_time = int(setup['speckle_filter_full_width_time'])
    fw_range = int(setup['speckle_filter_full_width_range'])
    assert fw_time > 0
    assert fw_range > 0
    
    # range in which filter is used
    filter_range = setup['percent_range_speckle_filter']
    assert filter_range > 0

    # upper limit for range gate amount to use the filter:
    limit_range = setup['max_filter_range_gates']
    assert limit_range > 0

    # handle fractional half-widths
    # To account for non-int half-widths, the lower end gets one pixel more
    # than the higher.
    hw_time_down = fw_time // 2
    hw_time_up = (fw_time-1) // 2
    hw_range_down = fw_range // 2
    hw_range_up = (fw_range - 1) // 2

    # ========== read data  ============================== #
    Ze = data['ze']
    sensitivity = data['Ze_sensitivity']
    shape = np.shape(Ze)
    Nt, Nr = shape

    # ========== determine rmin  ========================= #
    # whatever this may be....
    # TODO: what is the meaning of `range_filter`?
    # TODO: what is the meaning of `artifact_center`?

    range_filter = get_range_filter(Ze,filter_range,limit_range)
    Ze_max_arg = np.zeros(np.shape(Ze)[0])
    artifact_center = np.shape(Ze)[1] - range_filter
    rmin = artifact_center
    
    # ==================================================== #
    
    # initialize flag for speckle filter
    flag = np.zeros(shape, dtype=bool)
    
    # windows of this are going to be used in the loop
    is_finite = np.isfinite(Ze)

    for t, r in itertools.product(range(Nt), range(rmin, Nr)):
        if not is_finite[t, r]:
            continue
        # range indices of windows
        rlo = r - hw_range_down
        rhi = r + hw_range_up + 1

        # keep them in bounds:
        rlo = max(rlo, 0)
        rhi = min(rhi, Nr)
        rwidth = rhi - rlo

        # time indices of windows
        tlo = t - hw_time_down
        thi = t + hw_time_up + 1

        # keep them in bounds:
        tlo = max(tlo, 0)
        thi = min(thi, Nt)
        twidth = thi - tlo

        # compute fraction of masked pixels
        window = is_finite[tlo:thi, rlo:rhi]
	
        Nfinite = np.sum(window)
        Ntotal = np.prod(np.shape(window))
	
        frac_finite = 1. * Nfinite  / Ntotal

        if not (frac_finite >= frac_finite_thresh):
            flag[t, r] = True

    Ze[flag] = np.nan
    data['ze'] = Ze
    data['flag_speckle_filter'] = flag
    return data

def check_input(data, setup):
    # check for necessary setup parameters
    keys = ('speckle_filter_full_width_time',
            'speckle_filter_full_width_range',
            'speckle_filter_min_frac_finite',
            )
    for key in keys:
        if key not in setup:
            raise KeyError('Missing setup parameter: %s' % key)

    fw_t = setup['speckle_filter_full_width_time']
    fw_r = setup['speckle_filter_full_width_range']
    min_frac = setup['speckle_filter_min_frac_finite']

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

###################################################
# HELPERS                                         #
###################################################
def get_range_filter(Ze,filter_range,limit_range):
    """<Do this and return that.>

        Parameters
        ----------
        Ze : 2d-array
            reflectivity

        Returns
        -------
        range_filter : int
            <meaning>
    """
    # TODO  Meaningful function docstring missing. Replace all <...>
    # placeholders appropriately, then delete this comment. (AA)
    Nt, Nr = np.shape(Ze)

    # TODO: Can me make this less arbitrary? (AA)
    
    range_filter = int(np.round(Nr*(filter_range/100.)))
    if range_filter >= limit_range:
       range_filter = limit_range
    print(Nr, range_filter)
    return range_filter
