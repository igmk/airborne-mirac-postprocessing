#!/usr/bin/python
"""Compute z-component of target velocity."""

# built-in modules
import itertools

# PyPI modules
import numpy as np

def compute_vertical_motion(data, setup, idx_time=None, idx_range=None):
    sources = ('self', 'dropsonde')[::-1]
    for source in sources:
        data = compute_vertical_motion_one_source(
                data, setup, idx_time=idx_time, idx_range=idx_range,
                source=source)

    return data

def compute_vertical_motion_one_source(
        data, setup, idx_time=None, idx_range=None,
        source='self'):
    """Compute z-component and return a dict.

        Parameters
        ----------
        data : dict
            must contain
            'vm_x',
            'vm_y',
            'vm_x_unc',
            'vm_y_unc'
            'sensor_azimuth_angle',
            'sensor_view_angle'
        setup : dict
        idx_time : list of int
            time indices to be decomposed
        idx_range : list of int
            range indices to be decomposed

        Returns
        -------
        data : dict
            These variables are added:
            vm_z : array
                target velocity in z-direction (eastward wind component)
            vm_z_unc : array
                uncertainties

        History
        -------
        2018-03-12 (AA): Created
        2018-05-16 (AA): Accurate indexing on temporal, vertical and horizontal
                         distance
    """
    chrono = setup['chrono']
    chrono.issue('target velocity: compute vertical motion...')
    Nt, Nr, Nf = np.shape(data['vm_r'])

    ###################################################
    # DEFAULT                                         #
    ###################################################
    if idx_time is None:
        idx_time = range(Nt)

    if idx_range is None:
        idx_range = range(Nr)

    ###################################################
    # INITIALIZE                                      #
    ###################################################
    vm_z = np.nan * np.zeros((Nt, Nr, Nf))
    vm_z_unc = np.nan * np.zeros((Nt, Nr, Nf))

    ###################################################
    # READ OUT VARIABLES                              #
    ###################################################
    vm_r = data['vm_r']

    if source == 'self':
        prefix = 'vm'
    elif source == 'dropsonde':
        prefix = 'v_dropsonde'
    else:
        raise NotImplementedError('Unexpected source: %s' % source)

    vm_x = data['%s_x' % prefix]
    vm_y = data['%s_y' % prefix]
    vm_x_unc = data['%s_x_unc' % prefix]
    vm_y_unc = data['%s_y_unc' % prefix]

    # make these variable have same dimension as v_r
    if source != 'self':
        f = lambda x: np.repeat(np.expand_dims(x, 2), Nf, 2)
        vm_x = f(vm_x)
        vm_y = f(vm_y)
        vm_x_unc = f(vm_x_unc)
        vm_y_unc = f(vm_y_unc)

    ###################################################
    # ANGLES                                          #
    ###################################################
    azis = np.radians(data['sensor_azimuth_angle'])
    vas = np.radians(data['sensor_view_angle'])
    sin_azis = np.sin(azis)
    cos_azis = np.cos(azis)
    sin_vas = np.sin(vas)
    cos_vas = np.cos(vas)
    tan_vas = np.tan(vas)

    ###################################################
    # MATHS                                           #
    ###################################################
    for nt, nf in itertools.product(idx_time, range(Nf)):
        vx = vm_x[nt, :, nf]
        vy = vm_y[nt, :, nf]
        vr = vm_r[nt, :, nf]
        vx_unc = vm_x_unc[nt, :, nf]
        vy_unc = vm_y_unc[nt, :, nf]
        sin_azi = sin_azis[nt]
        cos_azi = cos_azis[nt]
        sin_va = sin_vas[nt]
        cos_va = cos_vas[nt]
        tan_va = tan_vas[nt]

        # MATHS: instantaneous vertical motion
        vz = (vx * sin_va * sin_azi + vy * sin_va * cos_azi - vr) / cos_va

        # ...and uncertainty
        radicand = vx_unc**2 * sin_azi**2 + vy_unc**2 * cos_azi**2
        vz_unc = tan_va * np.sqrt(radicand)

        vm_z[nt, :, nf] = vz
        vm_z_unc[nt, :, nf] = vz_unc

    ###################################################
    # TOTAL SPEED                                     #
    ###################################################
    # ========== abbreviations  ========================== #
    vx = vm_x
    vy = vm_y
    vz = vm_z
    vx_unc = vm_x_unc
    vy_unc = vm_y_unc
    vz_unc = vm_z_unc

    # ========== total speed ============================= #
    # value
    v = np.sqrt(vx**2 + vy**2 + vz**2)

    # uncertainty
    radicand = (vx * vx_unc)**2 + (vy * vy_unc)**2 + (vz * vz_unc)**2
    v_unc = np.sqrt(radicand) / np.abs(v)

    ###################################################
    # WRITE TO DICT                                   #
    ###################################################
    data['%s_z' % prefix] = vz
    data['%s_z_unc' % prefix] = vz_unc
    data['%s' % prefix] = v
    data['%s_unc' % prefix] = v_unc

    return data
