#!/usr/bin/python

# standard modules
import os
from copy import deepcopy as copy

# PyPI modules
from netCDF4 import Dataset

# Acloud modules
from utils.in_out import init
from utils.in_out import paths
from utils.in_out import write_helpers as helpers

###################################################
# MAIN FUNCTION                                   #
###################################################
def write_file(data, setup, filename=None):
    """Write data to file."""
    chrono = setup['chrono']

    # leave the original dict untouched:
    data = copy(data)

    # prepare setup
    init.import_sensor(setup)
    add_space_dim_variable(setup)

    # get sensor module
    sensor = setup['io_sensor'].write

    # prepare data
    helpers.prepare_data.main(data, setup)
    sensor.prepare_data.main(data, setup)

    # get filename
    if filename is None:
        filename = paths.get_output_filename(data=data, setup=setup)
    create_folder(filename)
    delete_old_file(filename)

    chrono.issue('write %s' % filename)
    with Dataset(filename, 'w', format=setup['nc_format']) as fid:
        jobs = (
                helpers.create_dimensions,
                sensor.create_dimensions,
                helpers.write_dimension_variables,
                sensor.write_dimension_variables,
                sensor.write_raw_variables,
                helpers.write_platform_data,
                helpers.write_sensor_data,
                helpers.write_target_data,
                helpers.write_ins_data,
                helpers.write_ancillary_data,
                sensor.write_ancillary_data,
                sensor.write_derived_data,
                helpers.write_global_attributes,
                sensor.write_global_attributes,
                )

        for job in jobs:
            job.main(fid, data, setup)

###################################################
# HELPERS                                         #
###################################################
def create_folder(filename):
    """Create folder if it does not yet exist."""
    idx = filename.rfind('/')
    if idx < 0:
        return

    path = filename[:idx]
    if not os.path.isdir(path):
        os.makedirs(path)

def delete_old_file(filename):
    """Delete old file if existant."""
    if os.path.isfile(filename):
        os.remove(filename)

def add_space_dim_variable(setup):
    lev_out = setup['lev_out']
    if lev_out == 'lev_3':
        varname = 'alt'
    else:
        varname = 'range'
    setup['space_dim'] = varname
    return varname
