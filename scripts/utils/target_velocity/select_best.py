#!/usr/bin/python

import numpy as np

def main(data, setup):
    """Select best target velocity guess.
        
        So far, a very simple approach is taken:
        Select those values where vm_z is closest to 0.
    """
    vm_z_3d = data['vm_z']
    shape3 = np.shape(vm_z_3d)

    # create index for axis 2
    dist = np.abs(vm_z_3d)
    dist[np.isnan(dist)] = np.inf
    idx = np.argmin(dist, 2)

    # create index for axes 0 and 1 (trivial)
    N, M, K = shape3
    m, n = np.meshgrid(np.arange(M), np.arange(N))

    # select
    keys = data.keys()
    for key in keys:
        shape = np.shape(data[key])
        if shape != shape3:
            continue

        key2 = key + '_best'
        data[key2] = data[key][n, m, idx]

    return data
