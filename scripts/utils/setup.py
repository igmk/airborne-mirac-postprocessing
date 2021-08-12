#!/usr/bin/python

import datetime as dt

def process_setup(setup, chop_lists=False):
    """Call sub-routines.

        Parameters
        ----------
        setup : dict
        chop_lists : bool, optional
            if True, lists are replaced by their first value
    
        Returns
        -------
        setup : dict
    """
    process_time(setup)
    add_signal_name(setup)

    if chop_lists:
        chop_list_entries(setup)

    return setup

def process_time(setup):
    """Add 'time_beg' and 'time_end' to setup."""

    # start (inclusive)
    if 'time_beg' not in setup.keys():
        ybeg = setup['year_beg']
        mbeg = setup['month_beg']
        dbeg = setup['day_beg']
        Hbeg = setup['hour_beg']
        Mbeg = setup['minute_beg']
        Sbeg = setup['second_beg']
        setup['time_beg'] = dt.datetime(ybeg, mbeg, dbeg, Hbeg, Mbeg, Sbeg)

    # end (exclusive)
    if 'time_end' not in setup.keys():
        yend = setup['year_end']
        mend = setup['month_end']
        dend = setup['day_end']
        Hend = setup['hour_end']
        Mend = setup['minute_end']
        Send = setup['second_end']
        setup['time_end'] = dt.datetime(yend, mend, dend, Hend, Mend, Send)

    return setup

def add_signal_name(setup):
    """Add 'signal_variable' to setup."""
    sensor_name = setup['payload_sensor_name']

    if sensor_name == 'amali':
        varname = 'channel_1'
    elif sensor_name == 'hampmira':
        varname = 'mira_signal'
    elif sensor_name == 'mirac':
        varname = 'ze'
    else:
        raise NotImplementedError('Unknown sensor name: %s' % sensor_name)

    setup['signal_variable'] = varname

    return setup

def chop_list_entries(setup, ignore_keys=()):
    """Replace lists by their first value.

        Parameters
        ----------
        setup : dict
        ignore_keys : iterable
            keys that are to be kept unchanges
    
        Returns
        -------
        setup : dict
    """
    for key in setup:
        if key in ignore_keys:
            continue
        if not isinstance(setup[key], list):
            continue
        if len(setup[key]) < 1:
            raise IndexError('Setup entry %s in an empty list.' % key)
        setup[key] = setup[key][0]

    return setup

def get_chronometer_info(setup):
    """Return a str."""
    cw = 24

    keys = (
        'payload_sensor_name', 'lev_in', 'lev_out', 'path_base_in',
        'path_base_out', 'time_beg', 'time_end')
    s = {}

    for key in keys:
        if key in setup:
            s[key] = setup[key]
        else:
            s[key] = 'N/A'

    text = (''
        + 'Sensor:'.ljust(cw) + s['payload_sensor_name'] + '\n'
        + 'Input level:'.ljust(cw) + s['lev_in'] + '\n'
        + 'Ouput level:'.ljust(cw) + s['lev_out'] + '\n'
        + 'Input path:'.ljust(cw) + s['path_base_in'] + '\n'
        + 'Output path:'.ljust(cw) + s['path_base_out'] + '\n'
        + 'Start time:'.ljust(cw) + str(s['time_beg']) + '\n'
        + 'End time:'.ljust(cw) + str(s['time_end']) + '\n'
        )[:-1]

    return text
