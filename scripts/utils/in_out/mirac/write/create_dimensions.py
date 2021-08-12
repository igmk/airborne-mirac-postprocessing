#!/usr/bin/python

def main(fid, data, setup):
    """Create dimensions."""
    Nchirp = len(data['range_offsets'])
    fid.createDimension('chirp_sequence', Nchirp)

    lev_out = setup['lev_out']
    if 'vm_r' in data:
        Nf = len(data['vm_r'][0, 0])
        fid.createDimension('fold_alternative', Nf)
