#!/usr/bin/python2
"""Remove sensor motion from apparent target speed."""

import numpy as np

from utils.maths import symmod

def main(data, setup):
    """Remove sensor motion from apparent target velocity."""
    # input check 
    varnames = ('vm_raw', 'vm_raw_theo')
    for varname in varnames:
        if varname not in data.keys():
            raise LookupError('data must contain variable %s.' %s)

    # display info message
    chrono = setup['chrono']
    chrono.issue('target velocity: correct for sensor motion...')

    # retrieve varialbes
    vnys = data['nqv']
    v_sensor_r = data['v_sensor_r']

    # ========== main  =================================== #
    for key_raw in ('vm_raw', 'vm_raw_theo'):
        key_c = key_raw.replace('raw', 'raw_c')

        # sum
        vm_raw = data[key_raw]
        v_sum = (vm_raw + np.expand_dims(v_sensor_r, 1))

        # mod
        data[key_c] = symmod(v_sum, vnys)
    # ==================================================== #

    return data
