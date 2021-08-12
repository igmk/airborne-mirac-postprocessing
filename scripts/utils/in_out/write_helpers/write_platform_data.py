#!/usr/bin/python

def main(fid, data, setup):
    """Write position, attitude, velocity of the sensor."""
    jobs = (write_name, 
            write_coordinates,
            write_attitude,
            )

    for job in jobs:
        job(fid, data, setup)

def write_name(fid, data, setup):
    vid = fid.createVariable('platform_name', 'c', ('char_pos',))
    vid.standard_name = 'platform_name'
    vid[:] = data['platform_name']

def write_coordinates(fid, data, setup):
    """Write platform coordinates."""
    varnames = ('lon_platform', 'lat_platform', 'alt_platform')
    for varname in varnames:
        if varname not in data:
            continue

        # lon_platform
        if varname == 'lon_platform':
            long_name = 'platform_longitude'
            units = 'degrees_east'

        # lat_platform
        elif varname == 'lat_platform':
            long_name = 'platform_latitude'
            units = 'degrees_north'

        # alt_platform
        elif varname == 'alt_platform':
            long_name = 'platform_altitude'
            units = 'm'

        vid = fid.createVariable(varname, 'f', ('time',))
        vid.long_name = long_name
        vid.units = units
        vid[:] = data[varname]

def write_attitude(fid, data, setup):
    """Write platform attitude."""
    varnames = (
            'platform_head_angle',
            'platform_pitch_angle',
            'platform_roll_angle',
            )

    for varname in varnames:
        if varname not in data:
            continue

        if varname == 'platform_head_angle':
            comment = 'true heading of the aircraft (0: North, 90: East)'
        elif varname == 'platform_pitch_angle':
            comment = 'aircraft pitch angle (positive if nose points upwards)'
        elif varname == 'platform_roll_angle':
            comment = (
                    'aircraft roll angle'
                    + ' (positive if right wing points downwards)'
                    )

        # create & write variable
        vid = fid.createVariable(varname, 'f', ('time',))
        vid.standard_name = varname
        vid.units = 'degree'
        vid.comment = comment
        vid[:] = data[varname]
