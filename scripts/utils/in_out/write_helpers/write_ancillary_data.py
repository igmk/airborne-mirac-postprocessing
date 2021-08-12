#!/usr/bin/python

def main(fid, data, setup):
    """Write position, attitude, velocity of the sensor."""
    write_dropsonde_data(fid, data, setup)
    write_beam_width(fid, data, setup)

def write_dropsonde_data(fid, data, setup):
    varnames = (
        'v_dropsonde_x', 'v_dropsonde_y',
        'wind_speed_dropsonde', 'wind_to_direction_dropsonde',
        'v_dropsonde_x_unc', 'v_dropsonde_y_unc',
        'wind_speed_dropsonde_unc', 'wind_to_direction_dropsonde_unc',
        'time_since_last_dropsonde', 'time_till_next_dropsonde',
        )

    for varname in varnames:
        if varname not in data:
            continue

        long_name = varname
        dimensions = ('time', setup['space_dim'])
        units = 'm s-1'
        comments = []

        # *_unc
        if varname[-4:] == 'unc':
            long_name = 'uncertainty_of_' + varname[:4]

        # time
        if varname.startswith('time'):
            units = 's'
            dimensions = ('time',)

        vid = fid.createVariable(varname, 'f', dimensions)
        vid.long_name = long_name
        vid.units = units
        vid[:] = data[varname]

def write_beam_width(fid, data, setup):
    """Add beam width."""
    varname = 'beam_fwhm'
    if varname in data:
        vid = fid.createVariable(varname, 'f', ())
        vid.long_name = 'beam_full_width_at_half_maximum'
        vid.units = 'degree'
        vid[:] = data[varname]
