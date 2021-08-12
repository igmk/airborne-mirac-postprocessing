#!/usr/bin/python
"""Set defective gates to nan.

    Authors
    -------
    [see parent module]

    History
    -------
    2018-12-12  (AA) Change filter name.

    2018-11-21  (AA) Export from parent module

    [earlier]   [see parent module]
"""
# standard modules
from copy import deepcopy as copy
import warnings

# PyPI modules
import numpy as np

NAME = 'defective gate filter'

###################################################
# MAIN                                            #
###################################################
def main(data, setup):
    """Set defective gates to nan.

        Sometimes specific range gates show a continuous error. These errors
        occur always in the same range gates, if the chirp sequences are the
        same. In this range gate a reflectifity threshold is always used. (LK)

        Parameters
        ----------
        data : dict
        setup : dict

        Returns
        -------
        data : dict
            defective gates in Ze are set to nan.
    """
    Ze = data['ze']
    Ze_out = copy(Ze)

    Nt, Nr = np.shape(Ze)

    thresholds = get_constant_gate_thresholds(data, setup)
    Ze_dB = 10 * np.log10(Ze)
    for r, thresh in thresholds:
        apply_reflectivity_threshold(Ze_dB, r, thresh)

    flag = np.isnan(Ze_dB) & ~np.isnan(Ze)
    Ze_out[flag] = np.nan

    data['ze'] = Ze_out
    data['flag_defective_gate_filter'] = flag

    return data

###################################################
# HELPERS                                         #
###################################################
# TODO: Think of an objective/automatic way to chose gates and thresolds
def get_constant_gate_thresholds(data, setup):
    """Return as tuple of (range_gate, thresh) pairs.
    
        Returns
        -------
        tuple of (r, th)
            r : int
                range gate
            th : float
                Ze threshold for this range gate.
    """
    Ze = data['ze']
    Nt, Nr = np.shape(Ze)
    chrono = setup['chrono']

    if Nr == 364:
        thresholds = ((77, -38.), (78, -38.), (268, -27.), (269, -27.))
    else:
        # implement other chirp tables here
        thresholds = ()

    return thresholds

def apply_reflectivity_threshold(x, r, thresh, make_copy=False):
    """Set values range gate nan if they are lower than a threshold.

        Parameters
        ----------
        x : 2d-array
            dimensions : time, range
        r : int
            range gate number to check
        thresh : float
            threshold; values which are lower than this are set to nan.
        make_copy : bool, optional
            if False, the input array is changed and returned. Otherwise, a
            modified copy if the input array is returned. Default: False.

        Returns
        -------
        x_corr : 2d-array
    """
    # Initialize output
    if make_copy:
        x_out = copy(x)
    else:
        x_out = x

    # index of values to be replaced by nan
    idx = x_out[:, r] < thresh

    # do the replacement
    x_out[:, r][idx] = np.nan

    return x_out

def check_input(data, setup):
    """Raise Exception if input if in bad shape, do nothing otherwise."""
    # There are no input checks implemented so far. Feel free to do so.
    return


###################################################
# UNUSED                                          #
###################################################
def range_gate_histogram(Zem_10corr):
    """<Do this and return that.>

        Parameters
        ----------
        Zem_10corr : <type>
            <meaning>

        Returns
        -------
        Zem_10corr : <type>
            <meaning>
    """
    # TODO  Meaningful function docstring missing. Replace all <...>
    # placeholders appropriately, then delete this comment. (AA)

    # TODO: Make this comment a bit more explanatory. (AA)
    # Like a CFADs 

    # TODO: magic number. What is its meaning? Why this value and not another?
    # (AA)
    _bini = 100
    shape = np.shape(Zem_10corr)
    Nt, Nr = shape
    bini = _bini
    zvalues = np.zeros((bini-1, Nr))

    for r in range(Nr - 1):
        bins = bini - 1
        hist_range = [-75, 24]
        rslice =  Zem_10corr[:, r]
        histo = np.histogram(rslice, bins=bins, range=hist_range)
        zvalues[:, r] = histo[0]

    xvalues = histo[1]
    yvalues = np.arange(Nr)

    return Zem_10corr
