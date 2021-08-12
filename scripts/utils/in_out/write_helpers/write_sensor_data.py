#!/usr/bin/python

def main(fid, data, setup):
    """Write position, attitude, velocity of the sensor."""
    jobs = (write_name, 
            write_coordinates,
            write_velocity,
            write_attitude,
            write_ancillary,
            )

    for job in jobs:
        job(fid, data, setup)

def write_name(fid, data, setup):
    vid = fid.createVariable('sensor_name', 'c', ('char_pos',))
    vid.standard_name = 'sensor_name'
    vid[:] = data['sensor_name']

def write_coordinates(fid, data, setup):
    """Write sensor coordinates."""
    varnames = ('lon_sensor', 'lat_sensor', 'alt_sensor')
    for varname in varnames:
        if varname not in data:
            continue

        # lon_sensor
        if varname == 'lon_sensor':
            long_name = 'sensor_longitude'
            units = 'degrees_east'

        # lat_sensor
        elif varname == 'lat_sensor':
            long_name = 'sensor_latitude'
            units = 'degrees_north'

        # alt_sensor
        elif varname == 'alt_sensor':
            long_name = 'sensor_altitude'
            units = 'm'

        vid = fid.createVariable(varname, 'f', ('time',))
        vid.long_name = long_name
        vid.units = units
        vid[:] = data[varname]

def write_velocity(fid, data, setup):
    """Write sensor velocity."""
    varnames = (
            'v_sensor_x', 'v_sensor_y', 'v_sensor_z',
            'v_sensor_r', 'v_sensor', 'sensor_course',
            )

    for varname in varnames:
        if varname not in data:
            continue

        # units
        if varname.startswith('v_sensor'):
            units = 'm s-1'
        elif varname == 'sensor_course':
            units = 'degree'

        # long_name & comment
        comment = ''
        comment_a = ''
        comment_b = ''
        if varname == 'v_sensor_x':
            long_name = 'eastward_sensor_speed_wrt_ground'
        elif varname == 'v_sensor_y':
            long_name = 'northward_sensor_speed_wrt_ground'
        elif varname == 'v_sensor_z':
            long_name = 'upward_sensor_speed_wrt_ground'
        elif varname == 'v_sensor_r':
            long_name = 'radial_velocity_of_sensor_away_from_sensor'
            comment_a = (
                    'projection of the sensor velocity wrt. ground onto'
                    + 'the line of sight of the sensor itself'
                    )
            comment_b = 'negative if sensor velocity is towards sensor'
        elif varname == 'v_sensor':
            long_name = 'sensor_speed_wrt_ground'
        elif varname == 'sensor_course':
            long_name = varname
            comment = 'course of the sensor (0: North, 90: East)'

        # create and write variable
        vid = fid.createVariable(varname, 'f', ('time',))
        vid.long_name = long_name
        vid.units = units
        if any(comment):
            vid.comment = comment
        if any(comment_a):
            vid.comment_a = comment_a
        if any(comment_b):
            vid.comment_b = comment_b
        vid[:] = data[varname]

def write_attitude(fid, data, setup):
    """Write sensor attitude."""
    varnames = (
            'sensor_azimuth_angle', 'sensor_zenith_angle', 'sensor_view_angle')

    for varname in varnames:
        if varname not in data:
            continue

        if varname == 'sensor_azimuth_angle':
            comment = (
                    'distance between North and the projection of the'
                    + ' sensor line of sight to a horizontal plane'
                    + ' (0: North, 90: East)'
                    )
        elif varname == 'sensor_zenith_angle':
            comment = 'distance from zenith of the sensor line of sight'

        elif varname == 'sensor_view_angle':
            comment = 'distance from nadir of the sensor line of sight'

        # create & write variable
        vid = fid.createVariable(varname, 'f', ('time',))
        vid.standard_name = varname
        vid.units = 'degree'
        vid.comment = comment
        vid[:] = data[varname]

def write_ancillary(fid, data, setup):
    """Add other sensor data."""
    varnames = ('distance_covered_by_sensor', 'effective_vertical_resolution')

    for varname in varnames:
        if varname not in data:
            continue

        if varname == 'distance_covered_by_sensor':
            dims = ('time',)
            comment = 'distance covered by sensor since beginning of the file'

        elif varname == 'effective_vertical_resolution':
            dims = ('time', setup['space_dim'])
            comment = (
                    'distance between consecutive range gates'
                    + ' projected to the vertical')

        vid = fid.createVariable(varname, 'f', dims)
        vid.long_name = varname
        vid.units = 'm'
        vid.comment = comment
        vid[:] = data[varname]
