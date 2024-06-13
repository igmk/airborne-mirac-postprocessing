

import os
import sys
import datetime as dt
import numpy as np
from scipy.interpolate import interp1d
import utils.in_out as io
import utils.setup as setup_utils
import utils.aircraft_transforms as atrans
from utils.coordinates.transform import Vector
import aa_lib.tables as tab
from aa_lib.chronometer import Chronometer


"""
Correct target coordinates of airborne remote sensing data.

Call from command line
======================
(1) Modify setup file.
(2) Then call:
        <scriptname> [<setupfile>]

Purpose
=======
Airborne remote sensing data come in coordinates relative to the sensor
(distance to the sensor). This script computes the global geographic
coordinates (lon, lat, alt) for each measurement point (target) and adds
them to the output file. The output is still on a (time, range) grid. 
New variables are added while all original variables are copied (unchanged)
to the output.

Input
=====
- level 0 airborne remote sensing measurements Z(time, range)
- aircraft position (lon, lat, alt)
- aircraft attitude (head, pitch, roll)
- sensor position and attitude within the aircraft (in the setup file)

Output
======
(level 01a)
netcdf files containing the same data as the level 0, but with added (lon,
lat, alt)
data or the target, along with some more information (sensor attitude,
sensor velocity, ...)

Frames of reference
===================
I tried to keep in line with [1], where possible.

symbol    origin          orientation
-----------------------------------------------------------------
Xs        sensor (radar)  along sensor axes
Xa        aircraft        airframe (right wing, nose, stabilizer)
Xt        aircraft        track-relative (right, forward, zenith)
Xc        aircraft        Earth relative; local East, North, Zenith
Xg        Earth's center  geographic (r, lon, lat)

Notes
-----
* Xt is aligned with the PROJECTION of the trajectory to a horizontal
  surface!
* Xc is named X in [1]
* Xs and Xg are not mentioned in [1]

References
==========
[1] Lee, Dodge, Marks and Hildebrand: Mapping of Airborne Doppler Radar
Data, Journal of Atmospheric and Oceanic Technology, 572-578, (11), 1994.

Author
======
Andreas Anhaeuser (AA) <andreas.anhaeuser@uni-koeln.de>
Institute for Geophysics and Meteorology
University of Cologne, Germany

History
=======
2018-05-17 (AA): Exported target velocity processing to lev_03 script.
2017-12-12 (AA): Created.
"""


_DEBUG = False
_setup_file = '../setup/setup_lev_1a.txt'

# constants
_pos_keys = ('lon', 'lat', 'alt')           # position keys
_att_keys = ('head', 'pitch', 'roll')       # attitude keys
_ins_keys = _pos_keys + _att_keys           # internal navigation system keys

# unit vector in direction of sight in Xs coordinates
# (this is used when correcting the Doppler speed)
_direction_of_sight = Vector((0., 1., 0.))


def main(setup_file=_setup_file, overwrite=True):
    """Main. Return (data, setup) of the last processed loop."""
    
    # preparation
    print('read setup file %s' % setup_file)
    setup = tab.read_namelist(setup_file, convert_to_number=True)
    setup_utils.process_setup(setup, chop_lists=True)

    # list of filenames
    print('get filenames...')
    fnis = io.paths.get_filenames(setup)    # input filenames
    Nfiles = len(fnis)

    # chronometer (performance info)
    header = 'Coordinate transformations'
    info = setup_utils.get_chronometer_info(setup)
    chrono = Chronometer(Nfiles, header=header, info=info)
    setup['chrono'] = chrono    # for re-use in subfunctions

    # date of previous file
    # (used to prevent INS data from being unnecessarily loaded multiple times
    # per day)
    date_prev = None

    if _DEBUG:
        chrono.warning('DEBUG-mode in main')

    # load dropsonde data
    #print('load dropsonde data...')
    #datasets_ds = dropsondes.get_dropsonde_data(setup)

    # loop over all input files
    for fni in fnis:
        chrono.issue('=' * 79)
        chrono.issue('input file: %s' % fni)

        # skip if output file exists
        # Check whether this loop can be skipped. This is the case if both of
        # these are true:
        # - overwrite == False
        # - output file exists already

        skip = True

        # never skip if output file does not exist
        fno = io.paths.get_output_filename(fni, setup=setup)
        if not os.path.isfile(fno):
            skip = False

        # never skip if overwriting is desired
        if overwrite:
            skip = False

        if skip:
            chrono.issue('Skip loop since output file already exists')
            chrono.decrease_total_count()
            continue

        # load
        # load new INS file only if date of current loop is different to
        # previous loop
        time_curr = io.paths.get_start_time(fni, setup)
        date_curr = time_curr.date()
        if date_curr != date_prev:
            chrono.issue('load ins data...')
            data_ins = get_ins_data(date_curr, setup)
            date_prev = date_curr

        # load payload sensor data
        chrono.issue('load payload sensor data...')
        data = get_payload_sensor_data(fni, setup)

        # case: input file very short
        # (less than two time steps)
        Ntime = len(data['secs1970_sensor'])
        if Ntime < 2:
            chrono.issue('WARNING: File contains less than 2 time steps. --> skip.')
            chrono.decrease_total_count()
            continue

        # computations
        chrono.issue('synchronize...')
        data = synchronize(data, data_ins, setup)

        # set up coordinate transforms
        chrono.issue('setup up transforms...')
        transforms = create_coordinate_transforms(data, setup)

        # jobs to be done
        jobs = (compute_sensor_coordinates,
                compute_sensor_attitude,
                compute_sensor_velocity,
                compute_distance_covered_by_sensor,
                compute_vertical_resolution,
                compute_target_coordinates,
                )

        chrono.issue('computations...')

        # perform the jobs
        # Everything happens inside the `data` dict. In each step, further
        # items are added to it.
        for job in jobs:
            job(data, transforms)

        if _DEBUG:
            break

        # add external ancillary data
        #dropsondes.add_dropsonde_data(data, datasets_ds, setup)

        # output
        write = io.write.write_file(data, setup)  # an abbreviation

        chrono.loop()

    chrono.resumee()

    return data, setup


def get_payload_sensor_data(fni, setup):
    """Return as dict."""

    print(fni)

    data = io.read.get_data(fni, setup)

    move_table = [                      # replace (old, new)
        ('time', 'time_sensor'),
        ('secs1970', 'secs1970_sensor'),
        ]

    for line in move_table:
        oldkey, newkey = line
        data[newkey] = data[oldkey]
        del data[oldkey]

    return data


def get_ins_data(date, setup):
    """Return ins data of the whole day as dict.

        Parameters
        ----------
        date : datetime.date
        setup : dict

        Returns
        -------
        ins_data : dict
            contains interpolation functions (time) for INS data
    """

    # preparation
    # create list of all INS which need to be loaded
    ins_names = []                  # e.g. ['gps1', 'ins1']
    for key in ('position_sensor_name', 'attitude_sensor_name'):
        ins_name = setup[key]
        if ins_name not in ins_names:
            ins_names.append(ins_name)

    # initialize
    data_ins = {}   # INS raw data will be stored here
    meta_ins = {}
    intp_ins = {}   # interpolation functions for _ins_keys

    # Explanation
    # -----------
    # The following is a bit complicated, but not beyond coprehensibility if
    # you are willing to try.
    #
    # `data_ins` is a dict that itself contains dicts. The first index is the
    # device name, the second index is the measured variable. E. g.
    #   data_ins['gps1']['lat'] == np.array([...])
    #   data_ins['ins1']['pitch'] == np.array([...])
    #
    # `meta_ins` also is a dict of dicts, but can be ignored (is not used at
    # the moment).
    #
    # `intp_ins` is a dict that contains functions. These functions interpolate
    # to INS data from their native time grid onto another one (which is
    # specified upon calling the function).

    # load data
    get_one_ins = io.ins.read.get_data
    path_ins = setup['path_base_ins']
    research_flight = setup['research_flight']
    campaign = setup['campaign']
    for ins_name in ins_names:
        data_ins[ins_name], meta_ins[ins_name] = get_one_ins(
            ins_name, date, research_flight, campaign, path_ins)
    
    # create interpolation functions
    for key in _ins_keys:
        intp_key = 'intp_' + key

        if key in _pos_keys:
            setup_key = 'position_sensor_name'
        elif key in _att_keys:
            setup_key = 'attitude_sensor_name'
        else:
            raise Exception()
        ins_name = setup[setup_key]

        x = data_ins[ins_name]['secs1970']
        y = data_ins[ins_name][key]

        # store interpolation function for each INS variable in dict
        intp_ins[intp_key] = interp1d(x, y, kind='linear', copy=False,
                                      assume_sorted=True)
        
    return intp_ins


def synchronize(data, data_ins, setup):
    """Map all data onto same time grid accounting for offsets.

        Parameters
        ----------
        data : dict
        data_ins : dict
        setup : dict

        Returns
        -------
        data : dict with additional keys:
            time            # 'real' time (corrected for offset)
            secs1970        # 'real' seconds (corrected for offset)
            lon_platform
            lat_platform
            alt_platform
            head
            pitch
            roll

        Author
        ------
        Andreas Anhaeuser (AA) <anhaeus@meteo.uni-koeln.de>
        Institute for Geophysics and Meteorology
        University of Cologne, Germany

        History
        -------
        2018-01-28 (AA): Created
    """

    # BUILD 'REAL' TIME LIST
    # seconds since 1970
    t_offset_sec = setup['time_offset_payload_sensor']
    data['secs1970'] = data['secs1970_sensor'] - t_offset_sec

    # datetime
    t_offset_dt = dt.timedelta(seconds=t_offset_sec)
    data['time'] = [t - t_offset_dt for t in data['time_sensor']]

    # MAP INS DATA TO 'REAL' TIMES
    # this is done by interpolation
    secs = data['secs1970']
    for key in _ins_keys:
        if key in _pos_keys:
            data_key = key + '_platform'
            ins = 'position_sensor'
        elif key in _att_keys:
            data_key = key
            ins = 'attitude_sensor'
        else:
            raise Exception()

        time_offset_key = 'time_offset_%s' % ins

        # select appropriate interpolation function
        intp_key = 'intp_' + key

        f = data_ins[intp_key]

        # account for ins time offset
        t_offset_sec = setup[time_offset_key]
        secs_ins = secs + t_offset_sec
        data[data_key] = f(secs_ins)

    return data


def create_coordinate_transforms(data, setup):
    """Return transforms as a dict.

        Parameters
        ----------
        data : dict with keys:
            - secs1970
            - time
            - lon_platform
            - lat_platform
            - alt_platform
            - head
            - pitch
            - roll
            - range
        setup : dict with keys:
            - payload_sensor_x
            - payload_sensor_y
            - payload_sensor_z
            - position_sensor_x
            - position_sensor_y
            - position_sensor_z
            - attitude_sensor
            - payload_sensor_azimuth_deg
            - payload_sensor_view_angle_deg
    """
    # Nomenclature
    # ============
    # tr_ij : transform from system Xi to system Xj
    # Tr_ij : list of transforms (time dependent)

    Ntime = len(data['secs1970'])

    # device
    # sensor attitude in Xa
    yaw_sensor_deg = setup['payload_sensor_azimuth_deg']
    pitch_sensor_deg = -90. + setup['payload_sensor_view_angle_deg']
    roll_sensor_deg = 0.

    # sensor position in Xa
    sensor_x = setup['payload_sensor_x'] - setup['position_sensor_x']     # (m)
    sensor_y = setup['payload_sensor_y'] - setup['position_sensor_y']     # (m)
    sensor_z = setup['payload_sensor_z'] - setup['position_sensor_z']     # (m)

    pos_sensor_Xa = Vector((sensor_x, sensor_y, sensor_z))

    # retrieve position and attitude
    # INS position
    lon_platform_deg = data['lon_platform']
    lat_platform_deg = data['lat_platform']
    alt_platform = data['alt_platform']

    # sensor attitude
    head_deg = data['head']
    pitch_deg = data['pitch']
    roll_deg = data['roll']

    # create transforms
    # Xs -> Xa  (sensor -> airframe)
    tr_sa = atrans.Xs_to_Xa(
        pos_sensor=pos_sensor_Xa,
        yaw_sensor=yaw_sensor_deg,
        pitch_sensor=pitch_sensor_deg,
        roll_sensor=roll_sensor_deg,
        units='deg',
        )

    # Xa -> Xc  (airframe -> local)
    Tr_ac = atrans.Xa_to_Xc(head_deg, pitch_deg, roll_deg)

    # Xc -> Xg  (local Earth-relative -> global geographic)
    Tr_cg = atrans.Xc_to_Xg(
        lon=lon_platform_deg, lat=lat_platform_deg, alt=alt_platform,
        units='deg')

    # ========== Xa -> Xt -> Xc ====================== #
    # This is currently not used because the INS provides heading instead of
    # yaw, which makes things much easier.
    #
    # However, if you change the code and have yaw rather than heading, you
    # may want to activate this paragraph.

    if False:
        # Xa -> Xt  (airframe -> track-relative)
        Tr_at = atrans.Xa_to_Xt(yaw_deg, pitch_deg, roll_deg)

        # Compute aircraft velocity (as seen from Earth at rest), expressed in
        # local coordinates.  As the local Earth-relative airframe Xc is
        # attached to the aircraft Xa, it differs from it only by rotation;
        # which is irrelevant for velocity. Therefore, this works:
        Vel_agc = atrans.velocity_of_reference_frame(Tr_cg, secs)

        # Xt -> Xc
        Tr_tc = atrans.Xt_to_Xc(Vel_agc)
    # ================================================ #

    # Xs -> Xc and
    # Xs -> Xg
    Tr_sc = [None] * Ntime
    Tr_sg = [None] * Ntime
    for n in range(Ntime):
        tr_cg = Tr_cg[n]
        tr_ac = Tr_ac[n]
        tr_sc = tr_sa.before(tr_ac)
        Tr_sc[n] = tr_sc
        Tr_sg[n] = tr_sc.before(tr_cg)

    # a dictionary containing all transforms that are used lateron
    # (add more transform if you need them)
    transforms = {
        # single step:
        'sa' : tr_sa,
        'ac' : Tr_ac,
        'cg' : Tr_cg,
        # 'at' : Tr_at,
        # 'tc' : Tr_ct,

        # combined:
        'sc' : Tr_sc,
        'sg' : Tr_sg,
        }

    return transforms

def compute_sensor_coordinates(data, transforms):
    """Add target coordinates to data.

        Returns
        -------
        data : dict with additional keys:
            - lon_sensor
            - lat_sensor
            - alt_sensor
    """
    Ntime = len(data['time'])
    origin = Vector()

    # initialize
    lon_sensor = np.nan * np.zeros(Ntime)
    lat_sensor = np.nan * np.zeros(Ntime)
    alt_sensor = np.nan * np.zeros(Ntime)

    # transforms at all time steps
    Tr_sg = transforms['sg']

    for ntime in range(Ntime):
        # transform at this time step
        tr_sg = Tr_sg[ntime]

        # ========== compute sensor coordinates  ========= #
        # in spherical coordinates (distance from Earth center, radians)
        coords_sph = tr_sg(origin).get_spheric()

        # in canonical coordinates (above sea level, degrees)
        coords_geo = atrans.global_spheric_to_canonical_geographic(*coords_sph)

        lon_sensor[ntime] = coords_geo[0]
        lat_sensor[ntime] = coords_geo[1]
        alt_sensor[ntime] = coords_geo[2]
        # ================================================ #

    # add to dict
    data['lon_sensor'] = lon_sensor
    data['lat_sensor'] = lat_sensor
    data['alt_sensor'] = alt_sensor

    return data

def compute_sensor_attitude(data, transforms):
    """Add sensor attitude to data.

        Returns
        -------
        data : dict with additional keys:
            - sensor_azimuth_angle
            - sensor_zenith_angle
            - sensor_view_angle
    """
    Nt = len(data['time'])

    ###################################################
    # COMPUTE ORIENTATION                             #
    ###################################################
    # initialize orientation angles
    sensor_azimuth_angle = np.nan * np.zeros(Nt)
    sensor_zenith_angle = np.nan * np.zeros(Nt)

    # unit vector in direction of sight in Xs coordinates
    u_s = _direction_of_sight    # just an abbrev.

    # transforms at all time steps
    Tr_sc = transforms['sc']

    for n in range(Nt):
        # transform at this time step
        tr_sc = Tr_sc[n]

        # orientation is wanted --> ignore shift
        r_sc = tr_sc.get_rotation()

        # transform orientation from Xs to Xc coordinates
        u_c = r_sc(u_s)

        # retrieve orientation angles
        sensor_azimuth_angle[n] = u_c.get_azimuth()
        sensor_zenith_angle[n] = u_c.get_zenith_angle()

    # rad --> deg
    sensor_azimuth_angle_deg = np.degrees(sensor_azimuth_angle)
    sensor_zenith_angle_deg = np.degrees(sensor_zenith_angle)

    # zenith angle --> view angle
    sensor_view_angle_deg = 180. - sensor_zenith_angle_deg

    # add to dict
    data['sensor_azimuth_angle'] = sensor_azimuth_angle_deg
    data['sensor_zenith_angle'] = sensor_zenith_angle_deg
    data['sensor_view_angle'] = sensor_view_angle_deg

    return data

def compute_sensor_velocity(data, transforms):
    """Add sensor velocity to data.

        Returns
        -------
        data : dict with additional keys:
    """
    # Nomenclature
    # ============
    # vel_ijk : velocity of Xi relative to Xj, expressed in Xk coordinates
    # Vel_ijk : list of velocities

    secs = data['secs1970']
    Nt = len(secs)

    ###################################################
    # EXTRACT TRANSFORMS                              #
    ###################################################
    Tr_sg = transforms['sg']
    Tr_sc = transforms['sc']

    ###################################################
    # COMPUTE VELOCITIES                              #
    ###################################################
    # sensor velocity in sensor coordinates
    Vel_sgs = atrans.velocity_of_reference_frame(Tr_sg, secs)

    # sensor velocity in Xc coordinates
    Vel_sgc = [None] * Nt
    for n in range(Nt):
        r_sc = Tr_sc[n].get_rotation()
        vel_sgs = Vel_sgs[n]
        Vel_sgc[n] = r_sc(vel_sgs)

    ###################################################
    # COMPUTE SPEED AND COURSE                        #
    ###################################################
    # initialize
    v_sensor = np.nan * np.zeros(Nt)
    course_sensor = np.nan * np.zeros(Nt)
    v_sensor_x = np.nan * np.zeros(Nt)
    v_sensor_y = np.nan * np.zeros(Nt)
    v_sensor_z = np.nan * np.zeros(Nt)
    v_sensor_r = np.nan * np.zeros(Nt)

    # direction of sight
    u_s = _direction_of_sight.unit_vector()

    for n in range(Nt):
        vel_sgc = Vel_sgc[n]
        vel_sgs = Vel_sgs[n]

        # sensor speed
        v_sensor[n] = abs(vel_sgc)

        # sensor course
        course_sensor[n] = vel_sgc.get_azimuth()

        # cartesian coordinates
        vx, vy, vz = vel_sgc.get_cart()
        v_sensor_x[n] = vx
        v_sensor_y[n] = vy
        v_sensor_z[n] = vz

        # projection onto line of sight
        v_sensor_r[n] = vel_sgs.dot(u_s)

    course_sensor_deg = np.degrees(course_sensor)

    ###################################################
    # ADD DATA TO DICT                                #
    ###################################################
    data['sensor_course'] = course_sensor_deg
    data['v_sensor'] = v_sensor
    data['v_sensor_x'] = v_sensor_x
    data['v_sensor_y'] = v_sensor_y
    data['v_sensor_z'] = v_sensor_z
    data['v_sensor_r'] = v_sensor_r

    return data

def compute_distance_covered_by_sensor(data, transforms):
    """Add distance covered by sensor to data."""
    if 'v_sensor' not in data.keys():
        data = compute_sensor_velocity(data, transforms)

    # Rationale
    # ---------
    # x == integral(v * Dt)
    seconds = data['secs1970']
    v = data['v_sensor']

    Dt = np.gradient(seconds)
    data['distance_covered_by_sensor'] = np.cumsum(v * Dt)
    return data

def compute_vertical_resolution(data, transforms):
    """Add vertical resolution to data."""
    if not 'sensor_view_angle' in data.keys():
        data = compute_sensor_attitude(data, transforms)

    # read
    r = data['range']
    vas_deg = data['sensor_view_angle']

    # computations
    dr = np.gradient(r)
    vas = np.radians(vas_deg)

    # initialize
    Nt = len(vas)
    Nr = len(r)
    vres = np.nan * np.zeros((Nt, Nr))

    for nt in range(Nt):
        vres[nt] = np.cos(vas[nt]) * dr

    data['effective_vertical_resolution'] = vres
    return data

def compute_target_coordinates(data, transforms):
    """Add target coordinates to data.

        Returns
        -------
        data : dict with additional keys:
            - lon
            - lat
            - alt
    """
    Ntime = len(data['time'])
    Nrange = len(data['range'])

    # points in sensor coordinates
    # TODO: make this more elegant (possibly implement np.array * Vector)
    # measurement points (Vector list)
    co = _direction_of_sight.get_cart()
    x = co[0] * data['range']
    y = co[1] * data['range']
    z = co[2] * data['range']
    points_s = Vector((x, y, z))

    # initialize
    lon = np.nan * np.zeros((Ntime, Nrange))
    lat = np.nan * np.zeros((Ntime, Nrange))
    alt = np.nan * np.zeros((Ntime, Nrange))

    Tr_sg = transforms['sg']
    for ntime in range(Ntime):
        tr_sg = Tr_sg[ntime]

        # points in geographic coordinates
        coords_sph = tr_sg(points_s).get_spheric()
        coords_geo = atrans.global_spheric_to_canonical_geographic(*coords_sph)
        lon[ntime] = coords_geo[0]
        lat[ntime] = coords_geo[1]
        alt[ntime] = coords_geo[2]

    data['lon'] = lon
    data['lat'] = lat
    data['alt'] = alt

    return data


if __name__ == '__main__':
    
    # If script is called from command line, then the first argument (if
    # present) is the setup file
    argv = sys.argv
    args = []

    for arg in argv:
        if arg[:1] == '-':
            continue
        args.append(arg)

    if len(args) > 1:
        setup_file = args[1]
    else:
        setup_file = _setup_file

    data, setup = main(setup_file=setup_file)
