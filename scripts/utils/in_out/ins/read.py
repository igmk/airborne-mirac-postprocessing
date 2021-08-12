#!/usr/bin/python

import os
import datetime
from netCDF4 import Dataset

from aa_lib import netcdf as aa_netcdf
from aa_lib import datetime_utils as aa_dt

# default
_path_ins = '/data/obs/campaigns/mosaic-aca/ins'


def get_data(name, date, path_ins=None, platform='P5'):
    """Return INS data in form of two dict.

        Parameters
        ----------
        name : str
            name of the INS, e. g. 'ins1', 'gps1', 'smart'
        date : datetime.date

        Returns
        -------
        data : dict
        meta : dict

        History
        -------
        2018-01-06 (AA): Created
    """
    if name.startswith('bahamas'):
        return get_data_bahamas(date, name)

    ###################################################
    # DEFAULT                                         #
    ###################################################
    if path_ins is None:
        path_ins = _path_ins

    ###################################################
    # PATH                                            #
    ###################################################
    yyyymmdd = date.strftime('%Y%m%d')
    path = _path_ins + '/%s/%s' % (platform, name)
    print(path)
    if not os.path.isdir(path):
        raise IOError()
    
    fn = path + '/%s_%s_%s.nc' % (platform, name, yyyymmdd)
    print(fn)
    if not os.path.isfile(fn):
        raise IOError()

    ###################################################
    # LOAD                                            #
    ###################################################
    data, meta = aa_netcdf.read_file(fn)

    ###################################################
    # CONVERT TIME                                    #
    ###################################################
    data['secs1970'] = data['time']
    meta['secs1970'] = meta['time']
    data['time'] = aa_dt.seconds_to_datetime(data['secs1970'])
    meta['time'] = {}

    return data, meta


def get_data_bahamas(date, name):
    """Return data in form of two dict."""
    path = '/data/hamp/flights/narval2/uniformGrid'
    filename = date.strftime(path + '/bahamas_%Y%m%d_v2.1.nc')

    with Dataset(filename) as nc:
        secs1970 = nc.variables['time'][:]
        time = [aa_dt.seconds_to_datetime(s) for s in secs1970]

        data = {
            'time' : time, # list of datetime.datetime
            'secs1970' : secs1970, # 1d-array of seconds since 1970
            'lon' : nc.variables['lon'][:],
            'lat' :  nc.variables['lat'][:],
            'alt' :  nc.variables['altitude'][:],
            'head' :  nc.variables['heading'][:],
            'pitch' :  nc.variables['pitch'][:],
            'roll' :  nc.variables['roll'][:],
        }

    if name == 'bahamas_pos':
        data.pop('head')
        data.pop('pitch')
        data.pop('roll')

    if name == 'bahamas_ins':
        data.pop('lon')
        data.pop('lat')
        data.pop('alt')

    return data, {}
