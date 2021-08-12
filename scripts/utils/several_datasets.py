#!/usr/bin/python
"""Utilities for tuples of datasets."""

from copy import deepcopy as copy
import numpy as np

def get_idx_current(datasets, ncurr=1):
    """Return time and range indices as a pair of lists."""
    assert 0 <= ncurr < len(datasets)

    # ============ time index  =========================== #
    nt_beg = 0
    for ndata, data in enumerate(datasets):
        # skip empty data
        if data is None:
            assert ndata != ncurr
            continue

        Nt = len(data['secs1970'])
        if ndata < ncurr:
            nt_beg += Nt
        elif ndata == ncurr:
            nt_end = nt_beg + Nt
            break
        else:
            raise Exception('This should not happen. Is `ncurr` an int?')

    idx_time = range(nt_beg, nt_end)
    # ==================================================== #

    # ========== range index  ============================ #
    Nr = len(datasets[ncurr]['range'])
    idx_range = range(Nr)
    # ==================================================== #

    return idx_time, idx_range

def merge_datasets(datasets, setup, ncurr=1):
    """Return a dict."""
    # find maximum number of range gates
    Nr_max = 0
    for data in datasets:
        if data is None:
            continue
        Nr = np.shape(data['range'])[0]
        Nr_max = max(Nr, Nr_max)

    # merge
    data_merged = {}
    for nd, data in enumerate(datasets):
        if data is None:
            continue
        for key in data:
            dep_t = time_axis(data, key, setup) is not None
            dep_r = range_axis(data, key, setup) is not None
            val_raw = data[key]
            shape_raw = np.shape(val_raw)

            init = key in data_merged.keys()

            # time and range dependent
            if dep_t and dep_r:
                Nt, Nr_raw = shape_raw[:2]
                shape_new = (Nt, Nr_max) + shape_raw[2:]
                val_new = np.nan * np.ones(shape_new)
                val_new[:, :Nr_raw] = val_raw
                if init:
                    data_merged[key] = np.concatenate(
                            (data_merged[key], val_new), 0)
                else:
                    data_merged[key] = val_new

            # only time dependent
            elif dep_t and not dep_r:
                if init:
                    data_merged[key] = np.concatenate(
                            (data_merged[key], val_raw), 0)
                else:
                    data_merged[key] = val_raw

            # only range dependent
            elif (not dep_t) and dep_r:
                if nd != ncurr:
                    continue
                Nr_raw = shape_raw[0]
                shape_new = (Nr_max,) + shape_raw[1:]
                val_new = np.nan * np.ones(shape_new)
                val_new[:Nr_raw] = val_raw
                data_merged[key] = val_new

            # neither of the two
            elif nd == ncurr:
                data_merged[key] = val_raw

    return data_merged

def select_current(data, setup, idx_time=None, idx_range=None):
    """Return current data set."""
    varnames = data.keys()
    data_out = copy(data)

    for varname in varnames:
        t_axis = time_axis(data, varname, setup=setup)
        r_axis = range_axis(data, varname, setup=setup)

        # time dependent
        if t_axis is not None and idx_time is not None:
            data_out[varname] = np.take(data_out[varname], idx_time, t_axis)

        # range dependent
        if r_axis is not None and idx_range is not None:
            data_out[varname] = np.take(data_out[varname], idx_range, r_axis)

    return data_out

def time_axis(data, key, setup={}):
    """Return an int or None."""
    found = False
    if 'time' in data:
        Nt = len(data['time'])
        found = True
    elif 'signal_variable' in setup:
        signal_key = setup['signal_variable']
        Nt, Nr = np.shape(data[signal_key])
        found = True

    if not found:
        raise KeyError('Cannot find a key with known time dimension in data.')

    shape = np.shape(data[key])
    if Nt in shape:
        axis = shape.index(Nt)
    else:
        axis = None
    return axis

def range_axis(data, key, setup={}):
    """Return an int or None."""
    found = False
    if 'range' in data:
        Nr = len(data['range'])
        found = True
    elif 'signal_variable' in setup:
        signal_key = setup['signal_variable']
        Nt, Nr = np.shape(data[signal_key])
        found = True

    if not found:
        raise KeyError('Cannot find a key with known time dimension in data.')

    shape = np.shape(data[key])
    if Nr in shape:
        axis = shape.index(Nr)
    else:
        axis = None
    return axis
