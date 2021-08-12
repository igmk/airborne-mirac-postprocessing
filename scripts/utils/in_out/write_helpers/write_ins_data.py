#!/usr/bin/python

def main(fid, data, setup):
    """Write position, attitude, velocity of the sensor."""
    jobs = (write_names, 
            write_position,
            write_attitude,
            write_time_offsets,
            )

    for job in jobs:
        job(fid, data, setup)

def write_names(fid, data, setup):
    """Write INS sensor names."""
    for sensor in ('position', 'attitude'):
        varname = '%s_sensor_name' % sensor
        if varname not in data:
            continue

        vid = fid.createVariable(varname, 'c', ('char_pos',))
        vid.long_name = varname
        vid[:] = data[varname]

def write_position(fid, data, setup):
    """Write position of payload sensor relative to position sensor."""
    varnames = (
        'sensor_postition_x_wrt_position_sensor',
        'sensor_postition_y_wrt_position_sensor',
        'sensor_postition_z_wrt_position_sensor',
        )

    for varname in varnames:
        if varname not in data:
            continue

        if '_x_' in varname:
            comment = 'x-axis points along the right wing of the aircraft'
        elif '_y_' in varname:
            comment = (
                    'y-axis points "forward" (towards the "nose") of'
                    + ' the aircraft'
                    )
        elif '_z_' in varname:
            comment = (
                    'z-axis points "upward" (along the stablizer)'
                    + ' in the aircraft frame of reference'
                    )

        # create & write variable
        vid = fid.createVariable(varname, 'f', ())
        vid.long_name = varname
        vid.units = 'm'
        vid.comment = comment
        vid[:] = data[varname]

def write_attitude(fid, data, setup):
    """Write attitude of payload sensor relative to attitude sensor."""
    varnames = (
        'sensor_view_angle_wrt_attitude_sensor',
        'sensor_azimuth_angle_wrt_attitude_sensor',
        )

    for varname in varnames:
        if varname not in data:
            continue

        if varname == 'sensor_view_angle_wrt_attitude_sensor':
            comment = (
                    'distance of the line of sight of the sensor'
                    + ' from the yaw axis of the attitude sensor'
                    )
        elif varname == 'sensor_azimuth_angle_wrt_attitude_sensor':
            comment = (
                    'clockwise rotation of the line of sight of the sensor'
                    + ' with respect to the "forward" direction of the'
                    + ' attitude sensor'
                    )

        # create & write variable
        vid = fid.createVariable(varname, 'f', ())
        vid.long_name = varname
        vid.units = 'degree'
        vid.comment = comment
        vid[:] = data[varname]

def write_time_offsets(fid, data, setup):
    """Write time offsets of the sensors."""
    varnames = (
        'time_offset_sensor',
        'time_offset_position_sensor',
        'time_offset_attitude_sensor',
        )

    for varname in varnames:
        if varname not in data:
            continue

        if varname == 'time_offset_sensor':
            long_name = 'time_offset_payload_sensor'
        else:
            long_name = varname
        
        # create & write variable
        vid = fid.createVariable(varname, 'f', ())
        vid.long_name = long_name
        vid.units = 's'
        vid.comment = 'negatve means that data of the past are recorded'
        vid.note = 'offsets have already been taken into account.'
        vid[:] = data[varname]
