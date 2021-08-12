#!/usr/bin/python
"""Create dimensions."""

def main(fid, data, setup):
    """Create dimensions."""
    space_dim = setup['space_dim']

    Nt = len(data['secs1970'])
    Nspace = len(data[space_dim])
    Nchar = setup['nc_string_length']

    fid.createDimension('time', Nt)
    fid.createDimension(space_dim, Nspace)
    fid.createDimension('char_pos', Nchar)
