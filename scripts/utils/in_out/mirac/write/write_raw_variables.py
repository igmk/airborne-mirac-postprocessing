#!/usr/bin/python

# PyPI modules
import numpy as np

def main(fid, data, setup):
    jobs = (
            write_sensor_information, 
            write_reflectivity_variables, 
            write_integrated_variables, 
            write_flags,
            write_filter_parameters,
            )

    for job in jobs:
        job(fid, data, setup)

def write_sensor_information(fid, data, setup):
    """Add sensor information and data."""
    lev_out = setup['lev_out']

    # frequency
    vid = fid.createVariable('freq_sb', 'f', ())
    vid.long_name = 'radar_frequency'
    vid.standard_name = 'radiation_frequency'
    vid.units = 'Hz'
    vid[:] = 94e9

    # cal_mom
    vid = fid.createVariable('cal_mom', 'b', ())
    vid.long_name = 'moment_calculation_method'
    vid.comment_a = '1: from dealiased spectra ' + \
            '2: from raw spectra ' + \
            '3: by RPG software'
    vid.comment_b = 'If AntiAlias == 1 then cal_mom = 3'
    vid[:] = data['cal_mom']

    # SeqAvg
    vid = fid.createVariable('seq_avg', 'i', ('chirp_sequence', ))
    vid.long_name = 'seq_avg'
    vid.comment = 'Number of averaged chrips in each chirp sequence'
    vid[:] = np.array(data['seq_avg'], dtype=int)

    # SeqIntTime
    vid = fid.createVariable('seq_int_time', 'f', ('chirp_sequence', ))
    vid.long_name = 'seq_int_time'
    vid.units = 's'
    vid.comment = 'Integration time of each chirp sequence'
    vid[:] = data['seq_int_time']

    # DoppMax
    if setup['space_dim'] == 'range':
        vid = fid.createVariable('nqv', 'f', ('range',))
        vid.long_name = 'Nyquist_speed'
        vid.units = 'm s-1'
        vid.comment = 'Max. unambigious Doppler velocity for each chirp ' + \
                'sequence. Needed to calculate the Doppler resolution: ' + \
                'DoppRes = 2*DoppMax/DoppLen'
        vid[:] = data['nqv']

    # DoppLen
    vid = fid.createVariable('dopp_len', 'i', ('chirp_sequence', ))
    vid.long_name = 'DoppLen'
    vid.comment = 'Number of samples in Dopppler spectra of each ' + \
            'chirp sequence. Needed to calculate the Doppler ' + \
            'resolution: DoppRes = 2*DoppMax/DoppLen'
    vid[:] = np.array(data['dopp_len'], dtype=int)

    # nAvg
    vid = fid.createVariable('n_avg', 'i', ('chirp_sequence', ))
    vid.long_name = 'nAvg'
    vid.comment = 'Number of spectra averaged'
    vid[:] = np.array(data['n_avg'], dtype=int)

    # range_offsets
    vid = fid.createVariable('range_offsets', 'i', ('chirp_sequence', ))
    vid.long_name = 'range_offsets'
    vid.comment_a = 'Chirp sequence start index array in range array'
    vid.comment_b = 'The command range(range_offsets) will give you ' + \
            'the range where a new chirp sequence starts. ' + \
            'range_offsets counts from 1 to n_levels.'
    vid[:] = np.array(data['range_offsets'], dtype=int)

def write_reflectivity_variables(fid, data, setup):
    """Add target data."""
    dimensions = ('time', setup['space_dim'])

    # Ze
    varname = 'Ze_raw'
    if varname in data.keys():
        vid = fid.createVariable(varname, 'f', dimensions)
        vid.standard_name = 'raw_equivalent_reflectivity_factor'
        vid.ancillary_variables = 'Ze_flag'
        vid.comment_a = 'corrected for all RPG software bugs known as of 2018-10-01'
        vid.comment_b = 'other artifacts not removed'
        vid.units = 'mm6 m-3'
        vid[:] = data[varname]

    # Ze
    varname = 'ze'
    if varname in data.keys():
        vid = fid.createVariable(varname, 'f', dimensions)
        vid.standard_name = 'equivalent_reflectivity_factor'
        vid.comment_a = 'corrected for all RPG software bugs known as of 2018-10-01'
        vid.comment_b = 'artifacts have been removed'
        vid.units = 'mm6 m-3'
        vid[:] = data[varname]

    # vm_raw
    varname = 'vm_raw'
    if varname in data.keys():
        vid = fid.createVariable(varname, 'f', dimensions)
        vid.long_name = 'uncorrected_radial_velocity_of_scatterers_away_from_instrument'
        vid.units = 'm s-1'
        vid.comment_a = 'No modification from raw data other than ' + \
                'reversal of sign'
        vid.comment_b = \
                'NOTE: Albeit its name, this is a speed, not a velocity!'
        vid.comment_c = \
                'NOTE: This is opposite to the lev 1 sign convention!'
        vid[:] = data[varname]

    # v_sigma
    varname = 'v_sigma'
    if varname in data.keys():
        vid = fid.createVariable(varname, 'f', dimensions)
        vid.long_name = 'Doppler_standard_deviation'
        vid.units = 'm s-1'
        vid.comment = 'spectral width of Doppler speed spectrum'
        vid[:] = data[varname]

    # v_skew
    varname = 'v_skew'
    if varname in data.keys():
        vid = fid.createVariable(varname, 'f', dimensions)
        vid.long_name = 'Doppler_skewness'
        vid.units = ''
        vid[:] = data[varname]

def write_integrated_variables(fid, data, setup):
    """Add meteorological data."""
    # lwp
    vid = fid.createVariable('lwp', 'f', ('time',))
    vid.long_name = 'liquid_water_path'
    vid.standard_name = 'atmosphere_mass_content_of_cloud_liquid_water'
    vid.units = 'kg m-2'
    vid[:] = data['lwp']

    # Tb
    vid = fid.createVariable('tb', 'f', ('time',))
    vid.standard_name = 'brightness_temperature'
    vid.units = 'K'
    vid[:] = data['tb']

def write_flags(fid, data, setup):
    space_dim = setup['space_dim']

    varname = 'Ze_flag'
    vid = fid.createVariable(varname, 'i', ('time', space_dim))
    vid.standard_name = 'Ze status_flag'
    vid.flag_masks = data[varname + '_masks']
    vid.flag_meanings = data[varname + '_meanings']
    vid[:] = data[varname]

def write_filter_parameters(fid, data, setup):
    """Add filter parameters."""
    # snr_filter_threshold
    varname = 'snr_filter_threshold'
    vid = fid.createVariable(varname, 'f', ())
    vid.long_name = varname
    vid.units = ''
    vid[:] = data[varname]

    # subsurface_reflection_filter_full_width_time
    varname = 'subsurface_reflection_filter_full_width_time'
    vid = fid.createVariable(varname, 'i', ())
    vid.long_name = varname
    vid.units = ''
    vid.comment = 'expressed in pixels on the native time-grid'
    vid[:] = data[varname]

    # subsurface_reflection_filter_full_width_range
    varname = 'subsurface_reflection_filter_full_width_range'
    vid = fid.createVariable(varname, 'i', ())
    vid.long_name = varname
    vid.units = ''
    vid.comment = 'expressed in pixels on the native range-grid'
    vid[:] = data[varname]

    # subsurface_reflection_filter_min_frac_finite
    varname = 'subsurface_reflection_filter_min_frac_finite'
    vid = fid.createVariable(varname, 'f', ())
    vid.long_name = varname
    vid.units = ''
    vid[:] = data[varname]

    # subsurface_reflection_filter_min_dist_to_surface
    varname = 'subsurface_reflection_filter_min_dist_to_surface'
    vid = fid.createVariable(varname, 'i', ())
    vid.long_name = varname
    vid.units = ''
    vid.comment = 'expressed in pixels on the native range-grid'
    vid[:] = data[varname]

    # subsurface_reflection_filter_max_dist_to_surface
    varname = 'subsurface_reflection_filter_max_dist_to_surface'
    vid = fid.createVariable(varname, 'i', ())
    vid.long_name = varname
    vid.units = ''
    vid.comment = 'expressed in pixels on the native range-grid'
    vid[:] = data[varname]

    # speckle_filter_min_frac_finite
    varname = 'speckle_filter_min_frac_finite'
    vid = fid.createVariable(varname, 'f', ())
    vid.long_name = 'speckle_filter_minimal_fraction_of_finite_values_in_window'
    vid.units = ''
    vid[:] = data[varname]

    # speckle_filter_full_width_time
    varname = 'speckle_filter_full_width_time'
    vid = fid.createVariable(varname, 'i', ())
    vid.long_name = 'speckle_filter_full_width_in_time_dimension'
    vid.units = ''
    vid.comment = 'expressed in pixels on the native time-grid'
    vid[:] = data[varname]

    # speckle_filter_full_width_range
    varname = 'speckle_filter_full_width_range'
    vid = fid.createVariable(varname, 'i', ())
    vid.long_name = 'speckle_filter_full_width_in_range_dimension'
    vid.units = ''
    vid.comment = 'expressed in pixels on the native range-grid'
    vid[:] = data[varname]
