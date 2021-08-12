#!/usr/bin/python

def main(data, setup):
    """Bring data into standard form."""
    jobs = (
            normalize_varnames,
            convert_strings,
            create_history,
            )

    for job in jobs:
        job(data, setup)

def normalize_varnames(data, setup):
    """Establish data with necessary varnames."""
    ###################################################
    # copy setup -> data                              #
    ###################################################
    copy_keys = (
            'platform_name',
            'position_sensor_name',
            'attitude_sensor_name',
            'time_offset_position_sensor',
            'time_offset_attitude_sensor',
            )
    for key in copy_keys:
        if key in setup:
            data[key] = setup[key]

    ###################################################
    # rename setup -> data                            #
    ###################################################
    # (setup_key, data_key)
    pairs = (
                ('payload_sensor_name', 'sensor_name'),
                ('payload_sensor_view_angle_deg',
                    'sensor_view_angle_wrt_attitude_sensor'),
                ('payload_sensor_azimuth_deg',
                    'sensor_azimuth_angle_wrt_attitude_sensor'),
                ('position_sensor_x',
                    'sensor_position_x_wrt_position_sensor'),
                ('position_sensor_y',
                    'sensor_position_y_wrt_position_sensor'),
                ('position_sensor_z',
                    'sensor_position_z_wrt_position_sensor'),
                ('time_offset_payload_sensor', 'time_offset_sensor'),
                ('beam_fwhm_deg', 'beam_fwhm'),
            )
    for setup_key, data_key in pairs:
        if setup_key in setup:
            data[data_key] = setup[setup_key]

    ###################################################
    # rename data -> data                             #
    ###################################################
    # (old_key, new_key)
    pairs = (
            ('global:platform', 'platform_name'),
            ('head', 'platform_head_angle'),
            ('pitch', 'platform_pitch_angle'),
            ('roll', 'platform_roll_angle'),
            )
    for old_key, new_key in pairs:
        if old_key in data:
            data[new_key] = data[old_key]

def convert_strings(data, setup):
    """Pad strings with null-characters."""
    Nchar = setup['nc_string_length']
    for varname in data:
        value = data[varname]
        if not isinstance(value, str):
            continue

        value = value.ljust(Nchar, '\0')[:Nchar]
        data[varname] = value

def create_history(data, setup):
    """Add global history if not present."""
    if 'global:history' not in data:
        data['global:history'] = ''
