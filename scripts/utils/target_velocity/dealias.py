#!/usr/bin/python2
"""Dealias target velocity."""

from copy import deepcopy as copy
import numpy as np

import utils.surface as sfc

from aa_lib import string_utils

###################################################
# MAIN                                            #
###################################################
def main(data, setup):
    """Unfold/de-alias Doppler velocity and remove sensor motion."""
    chrono = setup['chrono']

    ###################################################
    # INPUT CHECK                                     #
    ###################################################
    varname = 'vm_c_bw-corrected' 
    if varname not in data.keys():
        raise LookupError('data must contain variable %s.' % varname)

    ###################################################
    # PREPARATION                                     #
    ###################################################
    vm_folded = data['vm_c_bw-corrected']
    Nt, Nr = np.shape(vm_folded)

    # initialize
    vm_unfolded = np.nan * np.ones((Nt, Nr))

    # Nyquist speed
    vnys = data['nqv']
    vnys_matrix = np.ones((Nt, Nr)) * vnys

    # surface index
    n_sfc = sfc.get_index_of_surface_gate(data, setup)

    ###################################################
    # UNFOLD AT GROUND                                #
    ###################################################
    chrono.issue('target velocity: unfold at ground...')
    for nt in range(Nt):
        # surface index
        nr = n_sfc[nt]
        measured = vm_folded[nt, nr]
        first_guess = 0.
        fold = vnys[nr]

        vm_unfolded[nt, nr] = unfold_one_value(measured, first_guess, fold)

    ###################################################
    # UNFOLD ARRAY                                    #
    ###################################################
    chrono.issue('target velocity: unfold columnwise...')
    vm_unfolded = unfold_columnwise(vm_folded, vnys_matrix, vm_unfolded, setup)

    DEBUG = False
    if DEBUG:
        chrono.debug_warning(__name__)
    else:
        chrono.issue('target velocity: unfold whole domain...')
        vm_unfolded = unfold_2d_array(vm_folded, vnys_matrix, vm_unfolded, setup)

    ###################################################
    # COMPUTE ALTERNATIVES                            #
    ###################################################
    Nf = setup['unfold_number_of_alternatives']
    vm_unfolded_3d = get_alternative_unfolds(vm_unfolded, vnys_matrix, Nf)

    data['vm_r'] = vm_unfolded_3d
    return data

###################################################
# HELPERS                                         #
###################################################
def unfold_columnwise(x_folded, x_ny, x_unfolded_start, setup):
    """Return the unfolded 2d-array.

        Parameters
        ----------
        x_folded : 2d-array with dimensions (time, range)
            the aliased/folded measurement
        x_ny : 2d-array with same shape as x_folded
            the Nyquist-value for each element (i. e. the folding half-width)
        x_unfolded_start : 2d-array with same shape as x_folded
            array where at each time step, 0 or 1 entries are non-nan
        setup : dict
            used entries : 'chrono'

        Returns
        -------
        x_unfolded : 2d-array with same shape as x_folded
    """
    chrono = setup['chrono']

    assert np.shape(x_folded) == np.shape(x_ny) == np.shape(x_unfolded_start)

    Nt, Nr = np.shape(x_folded)

    x_unfolded = copy(x_unfolded_start)

    for nt in range(Nt):
        progress = 1. * nt / Nt
        ps = 'unfold columnwise ' + string_utils.percentage_string(progress)
        pb = string_utils.progress_bar(progress, 40, fillcolor=string_utils._YELLOW)
        chrono.show(ps + '\n' + pb)

        vd = x_unfolded[nt]
        idx = np.where(~np.isnan(vd))[0]
        if not any(idx):
            continue
        assert len(idx) == 1

        x_folded_col = x_folded[nt]
        x_ny_col = x_ny[nt]
        n_pivot = idx[0]
        x_unfolded_pivot = x_unfolded[nt, n_pivot]

        x_unfolded[nt] = unfold_column(x_folded_col, x_ny_col, x_unfolded_pivot, n_pivot)

    return x_unfolded

def unfold_column(x_folded, x_ny, x_unfolded_pivot, n_pivot):
    """Return unfolded column.

        Parameters
        ----------
        x_folded : 1d-array with dimension range
            the aliased/folded measurement
        x_ny : 1d-array with same shape as x_folded
            the Nyquist-value for each element (i. e. the folding half-width)
        x_unfolded_pivot : float
            a known unfolded value that is used as starting point
        n_pivot : int
            the position of `x_unfolded_pivot` in the column

        Returns
        -------
        x_unfolded : 1d-array with same shape as x_folded
    """
    N = len(x_folded)

    # input check
    assert len(x_ny) == N
    assert 0 <= n_pivot < N

    # initialize
    x_unfolded = np.nan * np.ones(N)

    # unfold pivot
    measured = x_folded[n_pivot]
    first_guess = x_unfolded_pivot
    fold = x_ny[n_pivot]
    x_unfolded[n_pivot] = unfold_one_value(measured, first_guess, fold)

    # unfold above pivot
    for n in range(n_pivot + 1, N):

        # case: nan
        if np.isnan(x_unfolded[n-1]):
            x_unfolded[n:] = np.nan
            break

        # regular case
        measured = x_folded[n]
        first_guess = x_unfolded[n-1]
        fold = x_ny[n]

        x_unfolded[n] = unfold_one_value(measured, first_guess, fold)

    # unfold below pivot
    for n in range(0, n_pivot)[::-1]:

        # case: nan
        if np.isnan(x_unfolded[n+1]):
            x_unfolded[:n+1] = np.nan
            break

        # regular case
        measured = x_folded[n]
        first_guess = x_unfolded[n+1]
        fold = x_ny[n]

        x_unfolded[n] = unfold_one_value(measured, first_guess, fold)

    return x_unfolded

def unfold_2d_array(x_folded, x_ny, x_unfolded_start, setup, hw_r=1, hw_t=1):
    """Return the unfolded array.

        Parameters
        ----------
        x_folded : array, shape (Nt x Nr)
            folded/aliased values
        x_ny : array, shape (Nt x Nr)
            fold half width
        x_unfolded_start : array, shape (Nt x Nr)
            array with some unfolded values to start with. Missing values must
            be nan.

        Returns
        -------
        x_unfolded : array of shape (Nt, Nr)

        Author
        ------
        Andreas Anhaeuser (AA) <anhaeus@meteo.uni-koeln.de>
        Institute for Geophysics and Meteorology
        University of Cologne, Germany

        History
        -------
        2018-03-07 (AA): Created
    """
    assert np.shape(x_folded) == np.shape(x_ny) == np.shape(x_unfolded_start)
    Nt, Nr = np.shape(x_folded)

    chrono = setup['chrono']

    x_unfolded = copy(x_unfolded_start)

    # r_start
    r_start = np.argmax(~np.isnan(x_unfolded), 1)
    nr_min = min(r_start)
    nr_max = max(r_start)

    Ntodo = np.sum(np.isnan(x_unfolded))
    Ndone = 0

    while nr_min > 0 or nr_max < Nr:
        something_has_changed = True
        nr_min = max(0, nr_min - 1)
        nr_max = min(Nr, nr_max + 1)

        while something_has_changed:
            something_has_changed = False
            x_fg = copy(x_unfolded)

            # progress bar
            progress = 1. * Ndone / Ntodo
            ps = 'unfold 2d ' + string_utils.percentage_string(progress)
            pb = string_utils.progress_bar(progress, 40, fillcolor=string_utils._YELLOW)
            chrono.show(ps + '\n' + pb)

            # find nans
            layer = x_unfolded[:, nr_min:nr_max]
            idx_t, idx_r_shifted = np.where(np.isnan(layer))
            idx_r = idx_r_shifted + nr_min

            Ni = len(idx_t)
            for i in range(Ni):
                nt = idx_t[i]
                nr = idx_r[i]

                # measured
                measured = x_folded[nt, nr]
                if np.isnan(measured):
                    continue

                # first guess
                nt_lo = max(0, nt - hw_t)
                nt_hi = min(Nt, nt + hw_t + 1)
                nr_lo = max(0, nr - hw_r)
                nr_hi = min(Nr, nr + hw_t + 1)

                first_guess, isnan = nanmean(x_fg[nt_lo:nt_hi, nr_lo:nr_hi])
                if isnan:
                    continue

                # fold
                fold = x_ny[nt, nr]

                # unfolded
                x_unfolded[nt, nr] = unfold_one_value(measured, first_guess, fold)

                Ndone += 1
                if not something_has_changed:
                    something_has_changed = True

    return x_unfolded

def unfold_one_value(measured, first_guess, fold):
    """Return unfolded/dealiased value.

        Parameters
        ----------
        x_raw : float
            measured
        x_fg : float
            first guess
        fold : float
            folding half width
    """
    x = measured
    fg = first_guess
    while x - fg > fold:
        x -= 2 * fold
    while fg - x > fold:
        x += 2 * fold
    return x

def get_alternative_unfolds(best_guess, x_ny, N):
    """Return a 3d-array.

        Parameters
        ----------
        best_guess : 2d-array (time, range)
            best guess
        x_ny : 2d-array (time, range)
            Nyquist speeds

        Returns
        -------
        all_guesses : 3d-array (time, range, alternatives)
            alternative guesses. Index of vm_unfolded (best guess):
                (N-1)/2 if N is even
                N/2 - 1 if N is odd            
    """
    if not isinstance(N, int):
        raise TypeError('N must be a positive int.')
    if N < 1:
        raise ValueError('N must be a positive int.')

    alternatives = []
    N = int(N)
    for n in range(N):
        Nfolds = n - (N-1) / 2
        alternative = best_guess + Nfolds * (2 * x_ny)
        alternatives.append(alternative)

    return np.stack(alternatives, 2)

def nanmean(x):
    """Return mean, isnan.

        For a 3x3 array, this is 3-6 times faster than numpy.
    """
    array = x.flatten()
    invalid = np.isnan(array)
    N = len(array) - np.sum(invalid)
    if N == 0:
        return np.nan, True
    S = np.sum(array[~invalid])
    mean = S / N
    return mean, False
