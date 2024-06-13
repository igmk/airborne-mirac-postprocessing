#!/usr/bin/python

# standard modules
import datetime as dt

def main(fid, data, setup):
    """Add global attributes."""
    fid.title = get_title(fid, data, setup)
    fid.platform = data['platform_name'].strip('\0')
    fid.source = get_source(fid, data, setup)
    fid.institution = setup['institution']
    fid.history = get_history(fid, data, setup)
    fid.author = get_author(fid, data, setup)
    fid.Conventions = 'CF-1.7'

def get_author(fid, data, setup):
    """Return a str."""
    author = setup['author']
    initials = setup['author_initials']
    return '%s (%s)' % (author, initials)

def get_source(fid, data, setup):
    """Return a str."""
    source = ''
    if 'sensor_name' in data:
        what = 'payload sensor'
        name = data['sensor_name'].strip('\0')
        source = source + ' %s (%s),' % (name, what)
    if 'position_sensor_name' in data:
        what = 'position sensor'
        name = 'gps_ins'  #data['position_sensor_name'].strip('\0')
        source = source + ' %s (%s),' % (name, what)
    if 'attitude_sensor_name' in data:
        what = 'attitude sensor'
        name = 'gps_ins'  #data['attitude_sensor_name'].strip('\0')
        source = source + ' %s (%s),' % (name, what)

    source = source.strip(' ').strip(',')
    return source

def get_title(fid, data, setup):
    """Return a str."""
    sensor = data['sensor_name'].strip('\0')
    platform = data['platform_name'].strip('\0')
    level = setup['lev_out'].strip()
    title = '%s on %s: %s' % (sensor, platform, level)
    return title

def get_history(fid, data, setup):
    """Return a str."""
    previous = data['global:history'].strip('\0')

    # construct current history
    yyyymmdd = dt.datetime.now().strftime('%Y-%m-%d')
    initials = setup['author_initials']
    level = setup['lev_out']
    current = ' %s (%s): Processed to %s.' % (yyyymmdd, initials, level)

    history = (previous + current).strip()
    return history
