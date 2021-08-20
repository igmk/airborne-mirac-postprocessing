#!/usr/bin/python3

import os
import datetime
from netCDF4 import Dataset

from aa_lib import netcdf as aa_netcdf
from aa_lib import datetime_utils as aa_dt

_path_ins = '/data/obs/campaigns/'

def get_data(name, date, flight, platform='polar5', path_ins=_path_ins):
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
    # PATH                                            #
    ###################################################
    yyyy = date.strftime('%Y')
    mm   = date.strftime('%m')
    dd   = date.strftime('%d')
    yyyymmdd = yyyy + mm + dd
    path = path_ins + '%s/gps_ins/%s/%s/%s/' % (name.lower(), yyyy, mm, dd)
    print(path)
    if not os.path.isdir(path):
        raise IOError()

    fn = path + '%s_%s_%s_%s.nc' % (name, platform, yyyymmdd, flight)
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
