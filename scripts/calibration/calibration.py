#!/usr/bin/python2
"""Optimize parameters for coordinate transformations.

    Calling sequence
    ================
    <scriptname> [setup_file_in] [setup_file_out] [plot_file_out]

    Summary
    =======
    This module tries to optimize parameters of the setup file for the main
    data level processing scripts. 'Optimizing' is used here to mean 'finding
    the most likely true value' for parameters that are not known precisely
    beforehand.


    Prerequisites
    =============
    The module uses the ground peak of the actual measurement to adjust the
    parameters. It tries to adjust the parameters such that the peak position
    and optionally width (according to the output level).

    Data
    ----
    The program needs a contiguous time interval of data where all of these are
    true:
        - The time interval contains no (or very little) faulty measurements.
          Missing (other than faulty) data do not affect the quality of the
          result.
        - The ground height is constant (e. g. flight above calm ocean).
        - The signal persistently has its strongest peak at this height (e. g.
          ground reflection).
    The longer the interval is, the better the optimization will be, but make
    sure it is 'clean' throughout the time interval.


    Parameters
    ----------
    The parameters that are to be calibrated can be chosen by the user as
    described below. Parameters that are to be calibrated must:
        - be numerical
        - be continuous (as opposed to categorical/discrete)
        - affect the retrieved altitude of the ground peak in the coordinate
          transformation.
    It is beneficial if the approximate value of the parameter is known
    beforehand.


    How to
    ======
    Get a setup file
    ----------------
    The best is probably to copy an already existing setup.txt.lev*.calibrate
    file and modify it according to your sensor.

    Modify the setup file
    ---------------------
    Work yourself carefully through the setup file and fill in all values to
    your best knowledge. The setup file should already be commented when you
    receive it.

    Parameters that you wish to be calibrated get three (comma separated) values.
        (1) The first entry is your first guess.
        (2) The second is the uncertainty that you allocate to this value. The
            uncertainty estimate has to be
            - small enough to not cover unwanted side minima of the cost
              function
            - large enough to evade unwanted small-scale 'micro-minima' due to
              noise in the cost function
            In most cases you won't have to worry much about giving a good
            estimate of the uncertainty. If the cost function is sufficiently
            smooth, the script is very stable with respect to the uncertainty
            estimates of the first guess.
        (3) The third entry is the desired precision of the calibration
            ("tolerance").  Calibration will not terminate successfully unless
            the parameter uncertainty is below this value.


    Run the script
    --------------
    (1) Launch the script in either of these ways:
        - Save the setup file as 'setup.txt.lev02.calibrate' in the directory where
          you execute the script and then call the script
        - Save the setup file under some other name and run
            $ <script_name> <setup_file>

    (2) Be patient and pray for convergence at a reasonable point in parameter
        space.


    Method
    ======
    The program currently uses the Nelder-Mead method (downhill simplex method)
    for optimization.

    Modify/add cost function(s) if you don't like them the way they are.


    What is a simplex?
    ==================
    A simplex is the multi-dimensional analogon of a triangle on a plane or a
    tetrahedron in space. A simplex in an N-dimensional hyperspace has N+1
    corners. The Nelder-Mead method iteratively moves and shrinks a simplex in
    parameter-space to approach a local minimum of the cost function.


    Todo
    ====
    The restriction that the calibration time has to be a contiguous interval
    may be troublesome.  Marek Jacob had the idea to implement the possibility
    to somehow flag the desired time steps.


    Author
    ======
    Andreas Anhaeuser (AA) <andreas.anhaeuser@uni-koeln.de>
    Institute for Geophysics and Meteorology
    University of Cologne, Germany
"""

###################################################
# IMPORT                                          #
###################################################
# python modules
import os
import sys
import warnings
import datetime as dt
import numpy as np

# other modules
import step_02_1_coordinates as fwd
import utils.in_out as io
import utils.setup as setup_utils
import utils.surface as sfc
import utils.theory.surface as sfc_theo

# Andreas Anhaeuser's modules
from aa_lib import tables as tab
from aa_lib import nelder_mead
#from aa_lib import nelder_mead_plot

###################################################
# MAIN                                            #
###################################################
def from_command_line(lev_out):
    """Run from command line."""
    print(lev_out)
    assert lev_out in ('1a', '2')  #('02', '03.2')

    ###################################################
    # DEFAULT VALUES                                  #
    ###################################################
    timestamp_beg = dt.datetime.now().strftime('%Y%m%d-%H%M%S')
    plot_path_out = '~/Documents'
    plot_file_out = None # '%s/lev_%s_calibrate_%s.eps' % (
        # plot_path_out, lev_out, timestamp_beg)

    defaults = {
        'scriptname' : 'step_%s_0_calibration.py' % lev_out,
        'setup_file_in' : '../setup/setup_lev_%s.calibrate.txt' % lev_out,
        'setup_file_out' : '../setup/setup_lev_%s.calibrated.txt' % lev_out,
        'plot_file_out' : plot_file_out,
        }

    ###################################################
    # COMMAND LINE ARGUMENT                           #
    ###################################################
    # override defaults
    argv = sys.argv
    args = []

    # get un-dashed parameters
    for arg in argv:
        if arg[:1] == '-':
            continue
        args.append(arg)

    scriptname = defaults['scriptname']
    setup_file_in = defaults['setup_file_in']
    setup_file_out = defaults['setup_file_out']
    plot_file_out = defaults['plot_file_out']

    if len(args) > 1:
        setup_file_in = args[1]
    if len(args) > 2:
        setup_file_out = args[2]
    if len(args) > 3:
        plot_file_out = args[3]

    ###################################################
    # CALL MAIN                                       #
    ###################################################
    opt = main(setup_file_in, setup_file_out, plot_file_out, scriptname)

def main(setup_file_in, setup_file_out, plot_file_out=None, scriptname=None):
    """Return opt."""
    ###################################################
    # SETUP                                           #
    ###################################################
    setup = get_setup(setup_file_in)

    setup['scriptname'] = scriptname

    ###################################################
    # PREPARATION                                     #
    ###################################################
    calibrate_parameters = setup['calibrate_parameters']

    # data
    args = get_args(setup)

    # parameters
    x0 = get_x(setup)

    # optimizer
    method = 'Nelder-Mead'

    # options
    options = {
        'disp': True,               # display messages while minimizing
        'return_all': True,
        'maxiter': 10**3,
        'maxfev': 10**3,
        'maxtime_sec' : setup['calibrate_max_time'],
        'xatol': get_x_tolerance(setup),
        'fatol': setup['calibrate_tol_cost_function'],
        'x0_uncert' : get_x_uncertainty(setup),
        'parameter_names' : calibrate_parameters,
        }

    ###################################################
    # PERFORM OPTIMIZATION                            #
    ###################################################
    opt = nelder_mead.minimize(
            forward, x0=x0, args=args, method=method, options=options)

    ###################################################
    # WRITE OUTPUT FILE                               #
    ###################################################
    write_calibrated_setup_file(opt, setup, setup_file_in, setup_file_out)

    if plot_file_out is not None:
        plot_result(opt, setup, plot_file_out)

    return opt

###################################################
# SETUP                                           #
###################################################
def get_setup(setup_file):
    """Return processed setup as dict."""
    # load raw file
    setup = tab.read_namelist(setup_file, convert_to_number=True)

    with open(setup_file, 'r') as fid:
        setup['_original_setup_file'] = fid.readlines()

    # process
    process_setup(setup)

    return setup

def process_setup(setup):
    """Process setup after loading to make it usable by main()."""
    setup_utils.process_setup(setup)

    ###################################################
    # TUNING PARAMETERS                               #
    ###################################################
    calibrate_parameters = []
    for key in sorted(setup.keys()):
        if not isinstance(setup[key], list):
            continue
        if key[:1] == '_':
            continue

        L = len(setup[key])
        if L > 1:
            calibrate_parameters.append(key)
            setup[key + '_uncertainty'] = setup[key][1]
            setup[key + '_tolerance'] = np.inf
        if L > 2:
            setup[key + '_tolerance'] = setup[key][2]

        setup[key] = setup[key][0]

    setup['calibrate_parameters'] = calibrate_parameters

    return setup

def write_calibrated_setup_file(opt, setup, fni, fno):
    """Write setup file with calibrated parameters."""
    if os.path.isfile(fno):
        os.remove(fno)

    # original file
    lines = setup['_original_setup_file']

    ###################################################
    # MODIFY                                          #
    ###################################################
    cps = setup['calibrate_parameters']
    for nline, line in enumerate(lines):
        # check whether any of the calibrate parameters is in `line`
        skip = True
        for ncp, cp in enumerate(cps):
            if line.startswith(cp):
                # found a calibration parameter
                skip = False
                value = opt['x'][ncp]
                unc = opt['x_unc'][ncp]
                break

        if skip:
            # no calibrate parameter found
            continue

        # find second occurence of ','
        count = 0
        idx = -1
        while count < 2:
            count += 1
            if ',' not in line[idx+1:]:
                idx = -1
                break
            idx = line.index(',', idx+1)
        tail = line[idx+1:].strip()

        # re-build line
        line = '%s : %s, %s, %s\n' % (cp, str(value), str(unc), tail)
        lines[nline] = line

    # add header line
    if setup['scriptname'] is not None:
        by_str = ' by %s' % setup['scriptname']
    else:
        by_str = ''

    time_str = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = '# This file was automatically created%s on %s.\n' % \
            (by_str, time_str)
    lines = [line] + lines

    ###################################################
    # WRITE                                           #
    ###################################################
    with open(fno, 'w') as fo:
        fo.writelines(lines)
    print('Optimized setup file written to: %s' % fno)

###################################################
# LOAD                                            #
###################################################
def get_args(setup):
    """Return arguments for forward opterator as tuple"""
    lev_out = setup['lev_out']
    if lev_out in ('1a', '1a_and_2'):
        return get_args_lev_1a(setup)
    elif lev_out == '2':
        return get_args_lev_2(setup)
    raise NotImplementedError(
        'Cannot handle output data level %s' % lev_out)

def get_args_lev_1a(setup):
    """Return sensor and INS data as two dict."""
    # sensor data

    fnis_abs = io.paths.get_filenames(setup)
    assert any(fnis_abs)

    datasets = []
    for fni_abs in fnis_abs:
        fdata = fwd.get_payload_sensor_data(fni_abs, setup)
        if len(fdata['time_sensor']) < 2:
            continue
        datasets.append(fdata)

    assert (datasets[0]['time_sensor'][0].date()
            == datasets[-1]['time_sensor'][-1].date()
            )

    # INS data
    date = io.paths.get_start_time(fni_abs, setup).date()
    data_ins = fwd.get_ins_data(date, setup)

    return datasets, setup, data_ins

def get_args_lev_2(setup):
    """Return data and setup as tuple of dict."""
    # sensor data
    fnis_abs = io.paths.get_filenames(setup)
    assert any(fnis_abs)

    datasets = []
    for fni_abs in fnis_abs:
        fdata = io.read.get_data(fni_abs, setup)
        if len(fdata['time']) < 2:
            continue
        datasets.append(fdata)

    assert datasets[0]['time'][0].date() == datasets[-1]['time'][-1].date()

    return datasets, setup

###################################################
# X-FUNCTIONS                                     #
###################################################
def get_x(setup):
    """Return an array."""
    keys = setup['calibrate_parameters']
    I = len(keys)
    x = np.nan * np.zeros(I)
    for i in range(I):
        key = keys[i]
        x[i] = setup[key]
    return x

def get_x_uncertainty(setup):
    """Return an array."""
    keys = setup['calibrate_parameters']
    I = len(keys)
    x_unc = np.nan * np.zeros(I)
    for i in range(I):
        key = keys[i]
        unc_key = key + '_uncertainty'
        unc = setup[unc_key]
        x_unc[i] = unc

    return x_unc

def get_x_tolerance(setup):
    """Return an array."""
    keys = setup['calibrate_parameters']
    I = len(keys)
    x_tol = np.nan * np.zeros(I)
    for i in range(I):
        key = keys[i]
        tol_key = key + '_tolerance'
        tol = setup[tol_key]
        x_tol[i] = tol

    return x_tol

def adjust_setup(x, setup):
    """Modify setup entries according to current parameters."""
    keys = setup['calibrate_parameters']
    assert len(x) == len(keys)
    for i, key in enumerate(keys):
        setup[key] = x[i]

###################################################
# Y-FUNCTIONS                                     #
###################################################
def forward(x, *args):
    """Return a float."""
    # adjust setup
    setup = args[1]
    adjust_setup(x, setup)

    lev_out = setup['lev_out']

    if '1a' in lev_out:
        forward_lev_1a(x, *args)
    if '2' in lev_out:
        forward_lev_2(x, *args)

    return cost_function(*args)

def forward_lev_1a(x, *args):
    """Return datasets, setup."""
    datasets = args[0]
    setup = args[1]
    data_ins = args[2]

    adjust_setup(x, setup)

    # coordinate transforms
    for data in datasets:
        fwd.synchronize(data, data_ins, setup)
        transforms = fwd.create_coordinate_transforms(data, setup)
        fwd.compute_sensor_coordinates(data, transforms)
        fwd.compute_sensor_attitude(data, transforms)
        fwd.compute_sensor_velocity(data, transforms)
        fwd.compute_target_coordinates(data, transforms)

    return args

def forward_lev_2(x, *args):
    """Return datasets, setup."""
    datasets = args[0]
    setup = args[1]

    # theoretical surface peak
    for data in datasets:
        sfc_theo.add_synthesized_signal(data, setup)

    return args

def cost_function(*args):
    """Return a float."""
    datasets = args[0]
    setup = args[1]

    lev_out = setup['lev_out']
    if lev_out == '1a':
        return cost_function_peak_position(datasets, setup)
    elif lev_out in ('2', '1a_and_2'):
        return cost_function_peak_shape(datasets, setup)
    else:
        raise NotImplementedError('Output level not implemented: %s' % lev_out)

def cost_function_peak_position(datasets, setup):
    """Return a float."""
    # initialize
    all_z_max = np.array([])
    all_z_sfc = np.array([])

    # concatenate
    for data in datasets:
        z_max = sfc.get_height_of_signal_maximum(data, setup)
        z_sfc = sfc.get_height_of_surface_gate(data, setup)
        all_z_max = np.concatenate((all_z_max, z_max))
        all_z_sfc = np.concatenate((all_z_sfc, z_sfc))

    # compute RMSD
    diff2 = (all_z_max - all_z_sfc)**2
    z_rmsd = np.sqrt(np.nanmean(diff2))
    badness = z_rmsd

    # post-condition
    assert np.isfinite(badness)

    return np.array(badness)

def cost_function_peak_shape(datasets, setup):
    """Return a float."""
    all_costs = np.array([])
    for data in datasets:
        sfc_theo.add_synthesized_signal(data, setup)
        Z_real = get_normalized_Z_peak(data, 'ze')
        Z_theo = get_normalized_Z_peak(data, 'ze_theo')
        costs = np.nanmean((Z_real - Z_theo)**2, 1)
        all_costs = np.concatenate((all_costs, costs))

    cost = np.sqrt(np.nanmean(costs))
    return cost

def get_normalized_Z_peak(data, varname, thresh_log10=-4):
    """Return a 2d-array."""
    # select
    Ze = data[varname]

    Ze_max = np.expand_dims(np.nanmax(Ze, 1), 1)

    # catch nan- and div-0-warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)

        # normalize
        Ze_norm = Ze / Ze_max

        # logarithm
        Z = np.log10(Ze_norm)

        # remove weak signal
        Z[Z < thresh_log10] = np.nan

    return Z

###################################################
# PLOT FUNCTIONS                                  #
###################################################
#def plot_result(opt, setup, plot_file_out):
#    nelder_mead_plot.plot_all_parameters(
#        opt, plot_file_out, parameter_names=setup['calibrate_parameters'])
