#!/usr/bin/python2
"""Remove effect of finite beam width on surface reflection."""

from copy import deepcopy as copy
import warnings

import numpy as np

import utils.surface as sfc
from utils.maths import symmod

def main(data, setup):
    """Remove effect of finite beam width on surface reflection."""
    # input check
    varnames = ('vm_raw_c', 'vm_raw_c_theo', 'ze', 'ze_theo')
    for varname in varnames:
        if not varname in data.keys():
            raise LookupError('data must contain variable %s.' % varname)

    # display info message
    chrono = setup['chrono']
    chrono.issue('target velocity: correct for finite beam width...')

    # retrieve variabbles
    vm_raw_c = data['vm_raw_c']
    vm_raw_c_theo = data['vm_raw_c_theo']
    vnys = data['nqv']

    # ========== main  =================================== #
    # get mask
    mask = get_correction_mask(data, setup)

    alternative = False
    if alternative:
        # get factor
        factor = get_correction_factor(data, setup)
        v_out = np.nan * np.zeros_like(vm_raw_c)
        v_out[~mask] = vm_raw_c[~mask]

        v_meas = vm_raw_c[mask]
        v_sfc = vm_raw_c_theo[mask]
        f = factor[mask]

        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RuntimeWarning)
            v_atm = (v_meas - f * v_sfc) / (1. - f)
            v_atm[f>=1] = v_sfc[f>=1]
        v_out[mask] = v_atm
    else:
        # correct masked values
        v_out = np.nan * np.zeros_like(vm_raw_c)
        v_out[~mask] = vm_raw_c[~mask]
        v_out[mask] = vm_raw_c[mask] - vm_raw_c_theo[mask]

    # mod
    v_out= symmod(v_out, 2*vnys)
    # ==================================================== #

    # output
    data['vm_c_bw-corrected'] = v_out
    return data

def get_correction_factor(data, setup={}):
    """Return an array of floats between 0 and 1."""
    Ze_norm_theo = normalize(data, 'ze_theo')
    Ze_norm_real = normalize(data, 'ze')
    f = Ze_norm_theo / Ze_norm_real
    f[np.isnan(f)] = 0.
    f[f>1.] = 1.
    return f

def get_correction_mask(data, setup={}):
    """Return a boolean array."""
    # ========== get mask by threshold  ================== #
    key = 'thresh_Ze_ratio'
    if key in setup.keys():
        thresh = setup[key]
    else:
        thresh = 1e-5
    Ze_norm_theo = normalize(data, 'ze_theo')

    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        mask = Ze_norm_theo > thresh
    # ==================================================== #

    # ========== extend mask by one gate  ================ #
    Nt, Nr = np.shape(mask)
    idx_t = np.arange(Nt)

    # at lower edge
    idx_r = np.argmax(mask, 1) - 1
    # avoid idx_r < 0:
    idx_r[idx_r < 0] - 0
    mask[idx_t, idx_r] = True

    # upper edge
    idx_r = Nr - np.argmax(mask[:, ::-1], 1)
    # avoid idx_R >= Nr:
    idx_r[idx_r >= Nr] = Nr - 1
    mask[idx_t, idx_r] = True
    # ==================================================== #

    return mask

def normalize(data, varname):
    """Return an array."""
    x0 = sfc.get_signal_maximum(data, varname=varname)
    x = data[varname]
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        normalized = x / np.expand_dims(x0, 1)
    return normalized
