#!/usr/bin/python

def main(fid, data, setup):
    """Write target coordinates."""
    write_time(fid, data, setup)
    write_space(fid, data, setup)

def write_time(fid, data, setup):
    """Write time coordinates."""
    varnames = ('secs1970_target', 'time_diff_target')
    dimensions = ('time', setup['space_dim'])

    for varname in varnames:
        if varname not in data:
            continue

        # time_target
        if varname == 'secs1970_target':
            vid = fid.createVariable(varname, 'f8', dimensions)
            vid.long_name = 'time_target'
            vid.comment = 'time when target was actually scanned'
            vid.units = 'seconds since 1970-01-01'
            vid.calendar = 'standard'
            vid.add_offset = data['secs1970'][0]
            vid[:] = data['secs1970_target']

        # time_diff_target
        elif varname == 'time_diff_target':
            vid = fid.createVariable(varname, 'f', dimensions)
            vid.long_name = 'time_difference_target'
            vid.comment = 'time difference between measurement and overflight'
            vid.units = 's'
            vid[:] = data[varname]

def write_space(fid, data, setup):
    """Write space coordinates."""
    space_dim = setup['space_dim']
    varnames = ('lon', 'lat', 'alt', 'range', 'horizontal_distance_target')

    for varname in varnames:
        if varname not in data:
            continue

        if varname == space_dim:
            # The space dimension variable is written elsewhere.
            # It is 'alt' or 'range', depending on the data level.
            continue

        standard_name = ''
        long_name = ''
        comment = ''

        if varname == 'lon':
            standard_name = 'longitude'
            units = 'degree_east'
        elif varname == 'lat': 
            standard_name = 'latitude'
            units = 'degree_north'
        elif varname == 'alt':
            long_name = 'altitude_above_mean_sea_level'
            standard_name = 'altitude'
            units = 'm'
        elif varname == 'range':
            long_name = 'distance_from_sensor'
            units = 'm'
        elif varname == 'horizontal_distance_target':
            long_name = varname
            units = 'm'
            comment = (
                    'horizontal distance between aircraft position'
                    + ' and measurement point'
                    )

        # create & write variable
        vid = fid.createVariable(varname, 'f', ('time', space_dim))
        if any(long_name):
            vid.long_name = long_name
        if any(standard_name):
            vid.standard_name = standard_name
        if any(comment):
            vid.comment = comment
        vid.units = units

        vid[:] = data[varname]
