#!/usr/bin/python3

import os
import datetime
from netCDF4 import Dataset

from aa_lib import netcdf as aa_netcdf
from aa_lib import datetime_utils as aa_dt

_path_ins = '/data/obs/campaigns/'

def get_data(name, date, research_flight, campaign, path_ins=_path_ins, platform='polar5'):
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
    if not os.path.isdir(path_ins):
        raise IOError()

    fn = path_ins + f'/{campaign}_P5_GPS_INS_{date.strftime("%Y%m%d")}_{research_flight}.nc'
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
    data['speed'] = 0,514444*data.pop('gs') #convert knts to m s
    data['head'] = data.pop('heading')

    return data, meta
