#!/usr/bin/python
"""Decompose target velocity into x-, y-, z-components."""

# Acloud modules
from utils.target_velocity import horizontal_motion
from utils.target_velocity import vertical_motion

def main(data, setup, idx_time=None, idx_range=None):
    """Decompose into x-, y-, z-components and return a dict.

        Parameters
        ----------
        data : dict
            must contain
            'secs1970', 'alt', 'vm_r',
            'sensor_azimuth_angle', 'sensor_view_angle'
        setup : dict
        idx_time : list of int
            time indices to be decomposed
        idx_range : list of int
            range indices to be decomposed

        Returns
        -------
        data : dict
            These variables are added:
            vm_x : array
                target velocity in x-direction (eastward wind component)
            vm_y : array
                target velocity in y-direction (northward wind component)
            vm_z : array
                target velocity in z-direction (upward motion)
            vm : array
                magnitude of the target velocity

        History
        -------
        2018-03-12 (AA): Created
        2018-05-16 (AA): Accurate indexing on temporal, vertical and horizontal
                         distance
    """
    data = horizontal_motion.compute_horizontal_motion(
            data, setup, idx_time=idx_time, idx_range=idx_range)
    data = vertical_motion.compute_vertical_motion(
            data, setup, idx_time=idx_time, idx_range=idx_range)
    return data
