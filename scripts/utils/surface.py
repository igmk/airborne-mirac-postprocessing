#!/usr/bin/python
"""Utilities related to Earth surface."""

from copy import deepcopy as copy
import numpy as np

###################################################
# SIGNAL MAXIMUM                                  #
###################################################
def get_signal_maximum(
        data, setup={}, varname=None, gate_min=None, gate_max=None):
    """Return the strongest signal as a 1d-time dependent array."""
    idx = get_index_of_signal_maximum(
            data, setup, varname, gate_min, gate_max)
    nt = range(len(idx))

    if varname is None:
        varname = get_
    return data[varname][nt, idx]

def get_height_of_signal_maximum(
        data, setup={}, varname=None, gate_min=None, gate_max=None):
    """Return a 1D time-dependent array.
    
        Parameters
        ----------
        data : dict with entries:
            'alt' : 1d-array 
                (m) altitude
            varname : 2d-array
                signal variable
        setup : dict, optional
            entry: 'payload_sensor_name'
            either `setup` or `varname` must be given
        varname : str, optional
            name of the signal variable in `data`
            either `setup` or `varname` must be given
        gate_min : int, optional
            lowest gate to be considered (inclusive)
        gate_max : int, optional
            highest gate to be considered (exclusive)

            
        Returns
        -------
        alt_max : array
            time-dependent height of the gate strongest signal.
    """
    idx = get_index_of_signal_maximum(
            data, setup, varname, gate_min, gate_max)
    nt = range(len(idx))
    return data['alt'][nt, idx]

def get_index_of_signal_maximum(
        data, setup={}, varname=None, gate_min=None, gate_max=None):
    """Return a 1d-array.
    
        Parameters
        ----------
        data : dict with entries:
            varname : 2d-array
                signal variable
        setup : dict, optional
            entry: 'payload_sensor_name'
            either `setup` or `varname` must be given
        varname : str, optional
            name of the signal variable in `data`
            either `setup` or `varname` must be given
        gate_min : int, optional
            lowest gate to be considered (inclusive)
        gate_max : int, optional
            highest gate to be considered (exclusive)

        Returns
        -------
        i_sfc : 1d-array
            index of signal peak
    """
    # name of signal variable
    if varname is None:
        varname = setup['signal_variable']

    assert varname in data
    signal = copy(data[varname])

    # unable gates beyond bounds
    if gate_min is not None:
        signal[:, :gate_min] = - np.inf
    if gate_max is not None:
        signal[:, gate_max:] = - np.inf

    # unable nan's
    signal[np.isnan(signal)] = - np.inf

    return np.argmax(signal, 1)

###################################################
# SURFACE GATE                                    #
###################################################
def get_value_at_surface(data, setup={}, varname=None):
    """Return the signal at surface as a 1d-time dependent array."""
    idx = get_index_of_surface_gate(data, setup)
    nt = range(len(idx))

    if varname is None:
        varname = setup['signal_variable']

    assert varname in data
    return data[varname][nt, idx]

# alias (deprecated)
get_signal_at_surface = get_value_at_surface

def get_height_of_surface_gate(data, setup={}):
    """Return the gate closest to surface as a 1d-time dependent array.
    
        Parameters
        ----------
        data : dict
        setup : dict, optional
            (unused)
            
        Returns
        -------
        alt_sfc : array
            time-dependent height of the gate closest to surface
    """
    idx = get_index_of_surface_gate(data, setup)
    nt = range(len(idx))
    return data['alt'][nt, idx]

def get_index_of_surface_gate(data, setup={}):
    """Return gate closest to surface as a 1d-array.
    
        Parameters
        ----------
        data : dict with entries:
            'alt' : 1d-array 
                (m) altitude
        setup : dict, optional
            (unused)

        Returns
        -------
        i_sfc : 1d-array
            index of the surface gate.
    """
    alts = data['alt']
    return np.argmin(np.abs(alts), 1)
