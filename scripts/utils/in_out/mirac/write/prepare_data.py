#!/usr/bin/python2

import numpy as np

def main(data, setup):
    normalize_varnames(data, setup)
    
def normalize_varnames(data, setup):
    """Establish data with necessary keys."""
    ###################################################
    # copy setup -> data                              #
    ###################################################
    copy_keys = (
            'snr_filter_threshold',
            'subsurface_reflection_filter_full_width_time',
            'subsurface_reflection_filter_full_width_range',
            'subsurface_reflection_filter_min_frac_finite',
            'subsurface_reflection_filter_min_dist_to_surface',
            'subsurface_reflection_filter_max_dist_to_surface',
            'speckle_filter_min_frac_finite',
            'speckle_filter_full_width_time',
            'speckle_filter_full_width_range',
            )
    for key in copy_keys:
        if key in setup:
            data[key] = setup[key]

    ###################################################
    # rename setup -> data                            #
    ###################################################
    # (setup_key, data_key)
    pairs = (
                ('wind_averaging_use_weights', 'wind_averaging_weighted'),
            )

    for setup_key, data_key in pairs:
        if setup_key in setup:
            data[data_key] = setup[setup_key]
