#!/usr/bin/python

# standard modules
import string

# PyPI modules
import numpy as np

def main(fid, data, setup):
    jobs = (
            write_velocity_data,
            write_wind_averaging_data,
            write_more_velocity_data,
            )

    for job in jobs:
        job(fid, data, setup)

def write_velocity_data(fid, data, setup):
    """Write processed target velocity data."""
    varnames = (
                'vm_raw_c', 'vm_r',
                'vm_x', 'vm_y', 'vm_z', 'vm',
                'vm_x_unc', 'vm_y_unc', 'vm_z_unc', 'vm_unc',
                'v_dropsonde_z', 'v_dropsonde_z_unc',
                'v_dropsonde', 'v_dropsonde_unc',
                'wind_speed', 'wind_speed_unc',
                'wind_to_direction', 'wind_to_direction_unc',
                )

    for varname in varnames:
        long_name = None
        standard_name = None
        units = 'm s-1'
        comments = []

        if varname not in data:
            continue

        # vm_raw_c
        if varname == 'vm_raw_c':
            long_name = 'radial_velocity_of_scatterers_away_from_instrument'
            comments = []

        # vm_r
        if varname == 'vm_r':
            standard_name = (
            'corrected_radial_velocity_of_scatterers_away_from_instrument'
            )
            comments = [
                    'corrected for sensor motion and beam width; de-aliased',
                    'NOTE: Sign convention opposite to the raw files!',
                    ]

        # vm_x
        if varname == 'vm_x':
            long_name = 'velocity_of_scatterers_in_zonal_direction'
            comments = [
                    'de-aliased and corrected for sensor motion and attitude',
                    ]

        # vm_y
        if varname == 'vm_y':
            long_name = 'velocity_of_scatterers_in_meridional_direction'
            comments = [
                    'de-aliased and corrected for sensor motion and attitude',
                    ]

        # vm_z
        if varname == 'vm_z':
            long_name = 'velocity_of_scatterers_in_vertical_direction'
            comments = [
                    'de-aliased and corrected for sensor motion and attitude',
                    'derived using wind from mirac',
                    ]

        # v_dropsonde_z
        if varname == 'v_dropsonde_z':
            long_name = 'velocity_of_scatterers_in_vertical_direction'
            comments = [
                    'de-aliased and corrected for sensor motion and attitude',
                    'derived using wind from dropsondes',
                    ]

        # v_dropsonde
        if varname == 'v_dropsonde':
            long_name = 'velocity_of_scatterers'
            comments = [
                    'de-aliased and corrected for sensor motion and attitude',
                    'derived using wind from dropsondes',
                    ]

        # vm
        if varname == 'vm':
            long_name = 'velocity_of_scatterers'
            comments = [
                    'de-aliased and corrected for sensor motion and attitude',
                    ]

        # wind_speed
        if varname == 'wind_speed':
            standard_name = varname

        # wind_to_direction
        if varname == 'wind_to_direction':
            standard_name = varname

        # *_unc
        if varname[-4:] == 'unc':
            long_name = 'uncertainty_of_' + varname[:4]

        ###################################################
        # WRITE                                           #
        ###################################################
        shape = np.shape(data[varname])
        Ndim = len(shape)
        dimensions = ('time', setup['space_dim'], 'fold_alternative')[:Ndim]
        
        vid = fid.createVariable(varname, 'f', dimensions)
        if standard_name is not None:
            vid.standard_name = varname
        if long_name is not None:
            vid.long_name = long_name
        vid.units = units
        for ncomment, comment in enumerate(comments):
            name = 'comment_%s' % string.ascii_lowercase[ncomment]
            vid.setncattr(name, comment)

        vid[:] = data[varname]

def write_wind_averaging_data(fid, data, setup):
    """Add wind averaging data."""
    varnames = (
        'wind_averaging_time', 'wind_averaging_horizontal',
        'wind_averaging_vertical', 'wind_averaging_weighted')

    for varname in varnames:
        if varname not in data:
            continue

        long_name = varname + '_tolerance'
        type = 'f'

        # wind_averaging_time_tolerance
        if varname == 'wind_averaging_time':
            units = 's'
            comment = 'data points up to this temporal distance have ' + \
                    'been taken into account'

        # wind_averaging_horizontal_tolerance
        if varname == 'wind_averaging_horizontal':
            units = 'm'
            comment = 'data points up to this horizontal distance have ' + \
                    'been taken into account'

        # wind_averaging_vertical_tolerance
        if varname == 'wind_averaging_vertical':
            units = 'm'
            comment = 'data points up to this vertical distance have ' + \
                    'been taken into account'

        # wind_averaging_weighted
        if varname == 'wind_averaging_weighted':
            dimensions = ()
            type = 'i'
            long_name = varname
            units = ''
            comment = '0: no weighting \n' + \
                '1: data points are weighted by their spatio-temporal distance'

        vid = fid.createVariable(varname, type, ('time', setup['space_dim']))
        vid.long_name = long_name
        vid.units = units
        vid.comment = comment
        vid[:] = data[varname]

def write_more_velocity_data(fid, data, setup):
    """Add intermediate velocity variables for debugging."""
    varnames = ('vm_raw_theo', 'vm_raw_c_theo', 'vm_sigma_theo',
            'vm_skew_theo', 'vm_c_bw-corrected', 'ze_theo')
    for varname in varnames:
        if varname not in data:
            continue
        if varname[:3] == 'vm_':
            units = 'm s-1'
        elif varname[:3] == 'Ze_':
            units = 'mm6 m-3'
        vid = fid.createVariable(varname, 'f', ('time', setup['space_dim']))
        vid[:] = data[varname]
