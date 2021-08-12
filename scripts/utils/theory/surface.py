#!/usr/bin/python
"""Synthesize surface reflection."""

from copy import deepcopy as copy
import numpy as np
from numpy import sin, cos, arccos, sqrt, exp

if __name__ == '__main__':
    from coordinates.transform import Vector
else:
    from ..coordinates.transform import Vector

###################################################
# MAIN FUNCTIONS                                  #
###################################################
def add_synthesized_signal(data, setup):
    """Add theoretical signal for several times steps to data.

        Parameters
        ----------
        data : dict with entries
            'range' : array of shape (Nr,)
            'alt_sensor' : array of shape (Nt,)
            'sensor_azimuth_angle' : array of shape (Nt,)
            'sensor_view_angle' : array of shape (Nt,)
            'v_sensor_x' : array of shape (Nt,)
            'v_sensor_y' : array of shape (Nt,)
            'v_sensor_z' : array of shape (Nt,)
        setup : dict with entries
            'beam_fwhm_deg' : float
                (deg) full width at half maximum of beam

        Returns
        -------
        data : dict with additional keys
            'ze_theo'
            'vm_theo'
            'v_sigma_theo'
            'v_skew_theo'

        Author
        ------
        Andreas Anhaeuser (AA) <anhaeus@meteo.uni-koeln.de>
        Institute for Geophysics and Meteorology
        University of Cologne, Germany

        History
        -------
        2018-06-07 (AA): Created
    """
    _max_rel_distance_to_beam_center = 3.   # only point up to this * FWHM from
                                            # beam center are considered

    ###################################################
    # INPUT CHECK                                     #
    ###################################################
    varnames_input = (
            'range', 'sensor_azimuth_angle', 'sensor_view_angle',
            'v_sensor_x', 'v_sensor_y', 'v_sensor_z', 'alt_sensor')
    for varname in varnames_input:
        if not varname in data.keys():
            raise KeyError("`data` must contain '%s'." % varname)

    ###################################################
    # PREPARATION                                     #
    ###################################################
    # ========== initialize  ============================= #
    Nt = len(data['sensor_azimuth_angle'])
    Nr = len(data['range'])
    varnames = ('ze', 'vm_raw', 'v_sigma', 'v_skew')
    varnames_theo = tuple([vn + '_theo' for vn in varnames])
    for varname in varnames_theo:
        data[varname] = np.zeros((Nt, Nr))
        if varname != 'ze_theo':
            data[varname] *= np.nan
    # ==================================================== #

    # get beam function
    fwhm = np.radians(setup['beam_fwhm_deg'])
    beam_function = get_gaussian_beam_function(fwhm)

    delta_max = _max_rel_distance_to_beam_center * fwhm

    for nt in range(Nt):
        # attitude angles
        alpha = np.radians(data['sensor_azimuth_angle'][nt])
        beta = np.radians(data['sensor_view_angle'][nt])

        # direction of sight
        dos_sensor = Vector().from_azimuth_and_view_angle((1., alpha, beta))

        # sensor velocity
        vx = data['v_sensor_x'][nt]
        vy = data['v_sensor_y'][nt]
        vz = data['v_sensor_z'][nt]
        v_sensor = Vector((vx, vy, vz))

        # altitude
        h_sensor = data['alt_sensor'][nt]

        # skip loop if value is missing
        skip = False
        for x in (alpha, beta, vx, vy, vz, h_sensor):
            if np.isnan(x):
                skip = True
                break
        if skip:
            continue

        # ========== select range gates ================== #
        # view angle bounds
        beta_lo = max(beta - delta_max, 0)
        beta_hi = min(beta + delta_max, np.pi/2)
        
        # range bounds
        rlo = h_sensor / np.cos(beta_lo)
        rhi = h_sensor / np.cos(beta_hi)

        # select range gates
        idx_lo = data['range'] >= rlo
        idx_hi = data['range'] <= rhi
        idx = idx_lo & idx_hi
        if np.sum(idx) == 0:
            continue
        ranges = data['range'][idx]
        # ================================================ #

        # synthesize theoretical values
        data_theo = synthesized_signal(
                r=ranges, h_sensor=h_sensor, dos_sensor=dos_sensor,
                v_sensor=v_sensor, beam_function=beam_function)

        for varname_theo in varnames_theo:
            varname = varname_theo[:-5]
            data[varname_theo][nt][idx] = data_theo[varname]

    return data

def synthesized_signal(
        r, h_sensor, dos_sensor, v_sensor, beam_function,
        alpha_deg_dist=10., alpha_deg_inc=0.1):
    """Return theoretical signal for one time step as a dict.

        Parameters
        ----------
        r : array, length N
            (m) range grid for the output
        h_sensor : float
            (m) altitude of the sensor above ground
        dos_sensor : Vector
            direction of sight of the sensor
        v_sensor : Vector
            (m/s) sensor velocity
        beam_function : callable
            must return the relative beam intensity of (r, delta), where  `r`
            is the radial distance to the sensor and `delta` is the distance to
            the beam axis
        alpha_deg_dist : float, optional
            maximum azimuth distance from beam center to consider in
            integration
        alpha_deg_inc : float, optional
            integration discretization increment

        Returns
        -------
        data : dict with keys
            'range'
            'ze'
            'vm_raw'
            'v_sigma'
            'v_skew'

        Author
        ------
        Andreas Anhaeuser (AA) <anhaeus@meteo.uni-koeln.de>
        Institute for Geophysics and Meteorology
        University of Cologne, Germany

        History
        -------
        2018-05-26 (AA): Created
    """
    # initialize
    Nr = len(r)
    nans = np.nan * np.ones(Nr)
    data = {}
    data['range'] = r
    data['ze'] = np.zeros(Nr)
    data['vm_raw'] = copy(nans)
    data['v_sigma'] = copy(nans)
    data['v_skew'] = copy(nans)

    # range of azimuth angles (this is the integration variable, shape (Na,))
    alpha_sensor = dos_sensor.get_azimuth()
    alpha_dist = np.radians(alpha_deg_dist)
    alpha_min = alpha_sensor - alpha_dist
    alpha_max = alpha_sensor + alpha_dist
    alpha_inc = np.radians(alpha_deg_inc)
    alphas = np.arange(alpha_min, alpha_max + alpha_inc, alpha_inc)
    Na = len(alphas)
    ones_a = np.ones(Na)                # shape (Na,)

    # view angle for each r
    cos_betas = 1. * h_sensor / r       # shape (Nr,)

    # unit vector on beam axis
    er0 = dos_sensor.unit_vector()      # shape ()

    for nr in range(Nr):
        # skip if beam not in contact with surface
        cos_beta = cos_betas[nr]
        if abs(cos_beta) > 1:
            continue

        # select view angle
        # (and repeat it `Na` times)
        betas = ones_a * arccos(cos_beta)       # shape (Na,)

        # construct unit vectors on cone around nadir
        ers = Vector.from_azimuth_and_view_angle((ones_a, alphas, betas))   # shape (Na,)

        # distance to beam center
        deltas = arccos(er0.dot(ers))           # shape (Na,)

        # signal strength on each point of the integral
        Zs = beam_function(r[nr], deltas)       # shape (Na,)

        # apparent ground speed on each point of the integral
        vs = - v_sensor.dot(ers)                # shape (Na,)

        # ========== compute integrals  ================== #
        # zeroth moment (Ze)
        Ze = np.sum(Zs * alpha_inc)            # shape ()
        data['ze'][nr] = Ze

        # first moment (vm)
        num = np.sum(vs * Zs * alpha_inc)       # shape ()
        vm = num / Ze
        data['vm_raw'][nr] = vm

        # second moment (sigma)
        num = np.sum((vs - vm)**2 * Zs * alpha_inc)
        sigma = np.sqrt(num / Ze)
        data['v_sigma'][nr] = sigma

        # third moment (skew)
        num = np.sum((vs - vm)**3 * Zs * alpha_inc)
        den = sigma**3 * Ze
        skew = num / den
        data['v_skew'][nr] = skew
        # ================================================ #
    
    return data

def get_gaussian_beam_function(fwhm, Z0=1.):
    """Return a callable.
    
        Parameters
        ----------
        fwhm : float
            (rad) full width at half maximum (angular distance from axis)
        Z0 : float
            (beam units / m^2) normalization factor
            
        Returns
        -------
        callable :
            the beam function called with arguments (r, delta)
            r : (m) distance to sensor
            delta : (rad) distance to beam axis
    """
    Delta2 = fwhm**2 / (8. * np.log(2))
    f = lambda r, delta: Z0 / r**2 * exp(-delta**2/(2*Delta2))
    return f


###################################################
# TESTING                                         #
###################################################
if __name__ == '__main__':
    import matplotlib.pyplot as plt
    h = 3000
    r = np.arange(2900, 3500, 15)
    fwhm_deg = 2.
    v_sensor = Vector([-2., -51, 0.4])
    dos_sensor = Vector([1, 1.4, -1.2], 'sph')

    # test surface_reflection()
    if False:
        bf = get_gaussian_beam_function(np.radians(fwhm_deg))
        data = surface_reflection(r, h, dos_sensor, v_sensor, bf)

        count = 0
        varnames = ('ze', 'vm_raw', 'v_sigma', 'v_skew')
        for vn in varnames:
            count += 1
            plt.subplot(2, 2, count)
            plt.plot(data[vn], -data['range'], 'r.-')
            plt.title(vn)

        plt.show()

    # test add_synthesized_signal()
    if True:
        Nt = 200
        vx = 40
        vy = 600
        vz = 0.1
        data = {}
        data['range'] = np.arange(0., 5000., 15.)
        data['alt_sensor'] = h * (1. + 0.01 * np.random.randn(Nt))
        data['v_sensor_x'] = vx * (1. + 0.03 * np.random.randn(Nt))
        data['v_sensor_y'] = vy * (1. + 0.03 * np.random.randn(Nt))
        data['v_sensor_z'] = vz + 0.2 * np.random.randn(Nt)
        azi_deg = np.arctan2(data['v_sensor_x'], data['v_sensor_y'])
        va_deg = 22.
        data['sensor_azimuth_angle'] = azi_deg + 2. * np.random.randn(Nt)
        data['sensor_view_angle'] = va_deg + 2. * np.random.randn(Nt)

        setup = {'beam_fwhm_deg' : 1.}
        data = add_synthesized_signal(data, setup)

        count = 0
        varnames = ('ze', 'vm_raw', 'v_sigma', 'v_skew')
        for vn in varnames:
            count += 1
            plt.subplot(2, 2, count)
            plt.title(vn)
            for nt in range(5):
                color = 'brkmg'[nt]
                y = data[vn + '_theo'][nt]
                if vn == 'ze':
                    y = np.log10(y/np.nanmax(y))
                plt.plot(y, -data['range'], '.-', color=color)
        plt.show()
