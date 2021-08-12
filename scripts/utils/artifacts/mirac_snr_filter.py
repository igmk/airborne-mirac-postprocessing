#!/usr/bin/python
"""Remove signal weaker than a certain threshold. Sub-module to mirac.py.

    Authors
    -------
    [see parent module]

    History
    -------
    2018-11-21  (AA)
                Exported from parent module

    [earlier]   [see parent module]
"""
# standard modules
from copy import deepcopy as copy
import warnings

# PyPI modules
import numpy as np

NAME = 'SNR filter'

def main(data, setup):
    """<Do this and that.>

        Parameters
        ----------
        data : dict
        setup : dict

        Returns
        -------
        data : dict
    """
    # TODO  Meaningful function docstring missing. Replace all <...>
    # placeholders appropriately, then delete this comment. (AA)
    Ze_corr = copy(data['ze'])
    sensitivity = data['Ze_sensitivity']

    snr_threshold = setup['snr_filter_threshold']

    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        snr = Ze_corr / sensitivity
        flag = snr < snr_threshold

    Ze_corr[flag] = np.nan

    data['ze'] = Ze_corr
    data['flag_snr_filter'] = flag

    return data

def check_input(data, setup):
    # check that SNR threshold is non-negative
    assert 'snr_filter_threshold' in setup
    assert setup['snr_filter_threshold'] >= 0.
