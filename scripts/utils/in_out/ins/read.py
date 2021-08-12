#!/usr/bin/python

import os
import datetime
from netCDF4 import Dataset

from aa_lib import netcdf as aa_netcdf
from aa_lib import datetime_utils as aa_dt

# default
_path_ins = '/data/obs/campaigns/acloud/ins'


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
