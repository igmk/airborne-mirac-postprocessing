#!/usr/bin/python
"""Remove artifacts from MIRAC signal during 2017 ACLOUD campaign.

    How to add new filters
    ----------------------
    If you want to add a new filter, create a sub-module and include it in the
    main-routine. The submodule MUST contain:
        check_input(data, setup) : callable 
            Perform preliminary data check. Return None if everyting is fine.
            Raise an exception otherwise.
        main(data, setup) : callable
            apply the filter
        NAME : str
            a meaningful and concise name of the filter

    Authors
    -------
    (AA) Andreas Anhaeuser      <andreas.anhaeuser@uni-koeln.de>
    (LK) Leif-Leonard Kliesch   <lkliesc1@uni-koeln.de>
    (MM) Mario Mech             <mario.mech@uni-koeln.de>
    (PK) Pavlos Kollias         <pkollias@uni-koeln.de>
    Institute for Geophysics and Meteorology
    University of Cologne, Germany


    History
    -------
    2018-12-11  (AA) Rename filters

    2018-12-11  (AA) Re-implement subsurface_reflection filter

    2018-11-21  (AA, LK) Further clean up.

    2018-11-21  (AA) Refactoring: create sub-modules.

    2018-11-01  (AA) Cleaned up the code: style, refactoring, export of magic
                numbers, bugs, etc. 

    2018-10-04  (LK) Shortened code to the essential.

    2018-09     (LK) Implemented (this code).

    2018        (LK, PK, MM) Developed solution algorithms.

    2018        (LK, PK, MM, AA) Identified and analysed the artifact types.
"""

# standard modules
from copy import deepcopy as copy
import datetime as dt

# PyPI modules
import numpy as np

# sub-modules
from utils.artifacts import mirac_subsurface_reflection_filter as subsurface_reflection
from utils.artifacts import mirac_snr_filter as snr
from utils.artifacts import mirac_speckle_filter as speckle
from utils.artifacts import mirac_defective_gate_filter as defective_gates

_DEBUG = False

_filters = (subsurface_reflection, snr, speckle, defective_gates)

###################################################
# MAIN                                            #
###################################################
def main(data, setup):
    """Apply artifact filters to Ze_raw.

        Parameters
        ----------
        data : dict with entries:
            'Ze_raw' : uncorrected reflectivity
            'Ze_sensitivity'
            'time' : list of datetime.datetime
        setup : dict

        Returns
        -------
        data : dict with added entry
            'ze' : corrected reflectivity
    """
    chrono = setup['chrono']
    print('chrono')

    check_input(data, setup)

    initialize(data, setup)

    for filt in _filters:
        chrono.issue(filt.NAME)
        filt.main(data, setup)

    merge_flags(data, setup)

    return data


###################################################
# SUB-FUNCTIONS                                   #
###################################################
def initialize(data, setup):
    """Do some trivial preparation."""
    if _DEBUG:
        # issue warning on if running in debug-mode
        setup['chrono'].debug_warning()

    data['ze'] = copy(data['Ze_raw'])

    return data

def check_input(data, setup):
    """Do nothing if input is ok, throw error otherwise."""
    check_date(data, setup)
    
    # perform checks in sub-modules
    for filt in _filters:
        filt.check_input(data, setup)

def check_date(data, setup):
    """Check whether corrections for this data set are implemented.
    
        Parameters
        ----------
        data : dict
        setup : dict
        
        Returns
        -------
        None
        
        Raises
        ------
        NotImplementedError
    """
    # only corrections for times in these intervals are implemented
    # ( (start1, end1), (start2, end2), ...)
    # start: inclusive, end: exclusive
    intervals = (
            (dt.datetime(2017, 5, 23), dt.datetime(2022, 4, 30)),
            # (another_start_time, another_end_time),
            )

    time_min = min(data['time'])
    time_max = max(data['time'])

    # check whether `time` is in any of the intervals
    implemented = False
    for interval in intervals:
        time_beg, time_end = interval
        if time_beg <= time_min and time_max < time_end:
            implemented = True
            break

    if not implemented:
        # ========== construct a nice intervals string  == #
        Nindent = len('Implemented intervals: ') 
        indent = Nindent * ' '

        intervals_strings = ['%s to %s\n%s'  % (str(i[0]), str(i[1]), indent)
                for i in intervals]

        # remove last '\n' and indent
        intervals_string = ''.join(intervals_strings)[:-(1+Nindent)]
        # ================================================ #

        message = (
            'The time interval of the file is outside the implemented range.'
            + '\n'
            + '\nDetails'
            + '\n-------'
            + '\nRequested interval:    %s to %s' % (
                str(time_min), str(time_max))
            + '\nImplemented intervals: %s' % intervals_string
            + '\n'
            + '\nHow to fix this'
            + '\n---------------'
            + '\na) If you are sure that all the corrections'
            + ' -- as they are currently implemented --'
            + ' apply also to your file, then you can simply include the time'
            + ' interval here. (in the function that throws this error).'
            + '\nb) Otherwise,'
            + '\n   - implement the corrections that apply to your case and'
            + '\n   - create branches to the appropriate corrections'
            + ' (e. g. conditional on time).'
            )
        raise NotImplementedError(message)

def merge_flags(data, setup):
    """Merge all flags into one byte-coded flag."""
    shape = np.shape(data['ze'])
    bit = 0
    description = ''
    all_flags = np.zeros(shape, dtype=int)
    masks = []

    for key in sorted(data):
        if not key.startswith('flag_'):
            continue

        # value of this bit
        mask = 2**bit
        masks.append(mask)

        # add to description
        word = key.lstrip('flag_').replace(' ', '_') + ' '
        description = description + word

        # add to flag
        this_flag = data[key]
        to_add = this_flag * mask
        all_flags += to_add

        # update bit position
        bit += 1

        # remove this flag
        del data[key]

    data['Ze_flag'] = all_flags
    data['Ze_flag_masks'] = np.array(masks, dtype=int)
    data['Ze_flag_meanings'] = description.strip()

    return data
