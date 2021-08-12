#!/usr/bin/python
"""Write dimension variables."""

###################################################
# MAIN                                            #
###################################################
def main(fid, data, setup):
    """Write dimension variables."""
    write_time(fid, data, setup)
    write_space_dim_variable(fid, data, setup)

###################################################
# WRITERS                                         #
###################################################
def write_time(fid, data, setup):
    vid = fid.createVariable('time', 'f8', ('time',))
    vid.standard_name = 'time'
    vid.units = 'seconds since 1970-01-01'
    vid.calendar = 'standard'
    vid.add_offset = data['secs1970'][0]
    vid[:] = data['secs1970']

def write_space_dim_variable(fid, data, setup):
    """Create spatial dimension variable."""
    # determine which is the spatial variable
    varname = setup['space_dim']

    if varname == 'range':
        long_name = 'distance_from_senor'
        standard_name = None
    elif varname == 'alt':
        long_name = None
        standard_name = 'altitude'
    else:
        raise NotImplementedError('Unknown space dimension: %s' % varname)

    # write variable
    vid = fid.createVariable(varname, 'f', (varname,))
    if standard_name is not None:
        vid.standard_name = standard_name
    if long_name is not None:
        vid.long_name = long_name
    vid.units = 'm'
    print(varname)
    vid[:] = data[varname]
