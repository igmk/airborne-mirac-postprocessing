#!/usr/bin/python2
"""Helper module to correct_airborne_radar_data. See documentation there."""

import numpy as np

from utils.coordinates.transform import Vector, Rotation, Transform

# ========== # constants  ================================ #
_RE = 6371e3    # (m) mean Earth radius

###################################################
# COORDINATE TRANSFORMS                           #
###################################################
def Xs_to_Xa(
        pos_sensor=Vector(), yaw_sensor=0., pitch_sensor=0.,
        roll_sensor=0., units='deg'
        ):
    """Return Transform from Xs to Xa.

        Parameters
        ----------
        pos_sensor : Vector
            position of sensor in Xa
        yaw_sensor, pitch_sensor, roll_sensor : float
            sensor attitude angles in Xa (analoguously to aircraft angles, see
            Xa_to_Xt()).
        units : {'deg', 'rad'}, optional
            Default: 'deg'

        Returns
        -------
        t : Transform
            t(v) transforms Vector v from Xs to Xa coordinates.

        History
        -------
        2017-12-11 (AA): Created
    """
    trans_shift = Transform(pos_sensor)
    trans_rot = Xa_to_Xt(
            yaw=yaw_sensor, pitch=pitch_sensor, roll=roll_sensor, units=units)
    return trans_shift.after(trans_rot)

def Xa_to_Xt(yaw=0., pitch=0., roll=0., units='deg'):
    """Return Transform from Xt to Xc.

        Parameters
        ----------
        yaw : float or array-like
            positive if aircraft nose is right of track
        pitch : float or array-like
            positive if aircraft nose is upward
        roll : float or array-like
            positive if right wing points downward
        units : {'deg', 'rad'}, optional
            Default: 'deg'

        Returns
        -------
        t : Transform or list of such
            t(v) transforms Vector v from Xa to Xt coordinates.

        History
        -------
        2017-12-11 (AA): Created
        2017-12-19 (AA): List extention
    """
    # input check
    S = np.shape(yaw)
    assert np.shape(pitch) == np.shape(roll) == S

    # list case
    if len(S) > 0:
        N = S[0]
        return [
                Xa_to_Xt(yaw=yaw[n], pitch=pitch[n], roll=roll[n], units=units)
                for n in range(N)]

    # deg --> rad
    if units == 'deg':
        yaw = np.radians(yaw)
        pitch = np.radians(pitch)
        roll = np.radians(roll)
    else:
        assert units == 'rad'

    # roll (y-axis)
    rot1 = Rotation(roll, 1)

    # pitch (x-axis)
    rot2 = Rotation(pitch, 0)

    # yaw (z-axis)
    rot3 = Rotation(-yaw, 2)

    rot = rot1.before(rot2).before(rot3)
    return Transform(rotation=rot)

def Xa_to_Xc(head=0., pitch=0., roll=0., units='deg'):
    """Return Transform from Xa to Xc.

        If head is knows rather than yaw, Xa->Xc can be performed directly
        (without the intermediate transform to Xt).

        Parameters
        ----------
        head : float or array-like
            True heading, i. e. angle from local North, measuring clockwise
            (CAUTION: rotation in mathematically negative direction).
        pitch : float or array-like
            positive if aircraft nose is upward
        roll : float or array-like
            positive if right wing points downward
        units : {'deg', 'rad'}, optional
            Default: 'deg'

        Returns
        -------
        t : Transform or list of such
            t(v) transforms Vector v from Xa to Xt coordinates.

        History
        -------
        2017-01-08 (AA): Created
    """
    # input check
    S = np.shape(head)
    assert np.shape(pitch) == np.shape(roll) == S

    # list case
    if len(S) > 0:
        N = S[0]
        return [
                Xa_to_Xc(
                    head=head[n], pitch=pitch[n], roll=roll[n], units=units)
                for n in range(N)]

    # deg --> rad
    if units == 'deg':
        head = np.radians(head)
        pitch = np.radians(pitch)
        roll = np.radians(roll)
    else:
        assert units == 'rad'

    # roll (y-axis)
    rot1 = Rotation(roll, 1)

    # pitch (x-axis)
    rot2 = Rotation(pitch, 0)

    # yaw (z-axis)
    # Note that, since the y-axis of Xa is aligned with the aircraft nose, and
    # head is 0 at north, the offset is zero. However, the sign is inverted.
    rot3 = Rotation(-head, 2)

    rot = rot1.before(rot2).before(rot3)
    return Transform(rotation=rot)

def Xt_to_Xc(vel):
    """Return Transform from Xt to Xc.

        Parameters
        ----------
        vel : Vector or list of such
            velocity of the aircraft as seen in Xc.

        Returns
        -------
        t : Transform or list of such
            t(v) transforms Vector v from Xt to Xc coordinates.

        History
        -------
        2017-12-11 (AA): Created
        2017-12-19 (AA): Implemented lists
    """
    # list case:
    if len(np.shape(vel)) > 0:
        return [Xt_to_Xc(vel=v) for v in vel]

    # This is done by a rotation about the z-axis. In Xt, the y-axis points
    # forward. Thus, an additional rotation by -90deg must be applied.
    angle_track = vel.get_spheric()[1]
    angle_forward = - np.pi/2.     # angle between forward direction and x-axis
    angle = angle_track + angle_forward
    rot = Rotation(angle, 2)
    return Transform(rotation=rot)

def Xc_to_Xg(lon, lat, alt, units='deg'):
    """Return Transform from Xc to Xg.

        Parameters
        ----------
        lon: float or array-like
            (deg) longitude of local coordinate system
        lat: float or array-like
            (deg) latitude of local coordinate system
        alt : float or array-like
            (m) altitude of local coordinate system above mean sea level
        units : {'deg', 'rad'}, optional
            Default: 'deg'

        Returns
        -------
        t : Transform or list of such
            t(v) transforms Vector v from Xc to Xg coordinates.

        History
        -------
        2017-12-11 (AA): Created
        2017-12-19 (AA): List extention
    """
    # list case:
    S = np.shape(lon)
    if len(S) > 0:
        assert np.shape(lat) == np.shape(alt) == S
        N = S[0]
        return [
                Xc_to_Xg(lon=lon[n], lat=lat[n], alt=alt[n], units=units)
                for n in range(N)]

    # normalize coordinates
    r = alt + _RE
    if units == 'deg':
        lon = np.radians(lon)
        lat = np.radians(lat)
    else:
        assert units == 'rad'

    # shift
    local_origin = Vector((r, lon, lat), 'spheric')

    # first, rotate about x-axis to align z-axes in Xc and Xg
    rot1 = Rotation(np.pi/2 - lat, 0)

    # then, rotate about new z-axis to align x-axes in Xc and Xg
    rot2 = Rotation((lon + np.pi/2), 2)

    # combine rotations
    rot = rot1.before(rot2)

    # create Transform
    return Transform(local_origin, rot)

def global_spheric_to_canonical_geographic(r, phi, theta):
    """Return lon, lat (both in degrees), alt.

        Parameters
        ----------
        r : float
            (m) distance from Earth center
        phi : float
            (rad) as defined above
        theta : float
            (rad) as defined above

        Returns
        -------
        lon : float
            (deg) geographical longitude
        lat : float
            (deg) geographical latitude
        alt : float
            (m) elevation above mean sea level

        Notes
        -----
        The Earth is assumed to be spherical here.

        History
        -------
        2017-12-11 (AA): Created
    """
    lon = np.degrees(phi)
    lat = np.degrees(theta)
    z = r - _RE
    return lon, lat, z

###################################################
# DOPPLER VELOCITY CORRECTION                     #
###################################################
def velocity_of_reference_frame(transforms_mf, times):
    """Return a list of Vector.

        Compute velocity of a reference frame (Xm) moving relative to another
        (Xf). Velecities are expressed in coordinates of the moving frame (Xm).

        Parameters
        ----------
        transforms_mf : list of Transform
            transformations from moving reference frame (Xm) to fixed reference
            frame (Xf) at different time steps
        times : array of float
            (s) times corresponding to elements of T_dg

        Returns
        -------
        list of Vector
            velocity of Xm relative to Xf at each time step, expressed in
            coordinates of Xm

        History
        -------
        2017-12-19 (AA): Created.
        2017-12-30 (AA): Bug-fix (convert int -> float). Comments.
    """
    # Procedure
    # =========
    # - From transforms_mf, the position of Xm relative to Xf is retrieved.
    # - Then, the velocity of Xm relative to Xf (expressed in Xf coordinates)
    #   in computed.
    # - Finally, the velocity is transformed to Xm coordinates.
    #
    # Note
    # ====
    # A cheaper algorithm can be thought of: compute the (negative of the)
    # apparent velocity of Xf as seen in Xm. This renders the final
    # re-transformation from Xf to Xm unnecessary. However, the solution that
    # is actually used here appears more intuitive to me (and thus more easy to
    # check for errors). (AA)

    # ========== input check ============================= #
    N = len(transforms_mf)
    assert N > 2
    assert len(times) == N

    # ========== positions of Xm in Xf =================== #
    origin = Vector()
    pos = [T(origin) for T in transforms_mf]
    dpos = [pos[n+1] - pos[n] for n in range(N-1)]

    # ========== velocities of Xm in Xf ================== #
    # The two adjacent velocities just before and after the cosidered time
    # steps are averaged. This average is taken to be the instantaneous
    # velocity.
    dtimes = times[1:] - times[:-1]     # len N-1
    vel = [None] * N
    for n in range(N):
        # *** low and high indices ***
        # regular case
        ilo = n - 1
        ihi = n

        # special case: first time step (no lower neighbour)
        if n == 0:
            ilo = ihi

        # special case: last time step (no upper neighbour)
        elif n == N - 1:
            ihi = ilo

        # *** increments ***
        dp_lo = 1. * dpos[ilo]
        dp_hi = 1. * dpos[ihi]
        dt_lo = 1. * dtimes[ilo]
        dt_hi = 1. * dtimes[ihi]

        # sometimes, this happens in the lev1a files:
        if dt_lo == 0:
            dt_lo = np.inf
        if dt_hi == 0:
            dt_hi = np.inf

        # *** velocities ***
        v_lo = dp_lo / dt_lo
        v_hi = dp_hi / dt_hi

        # *** weights ***
        w_lo = dt_hi / (dt_lo + dt_hi)
        w_hi = 1. - w_lo

        vel[n] = w_lo * v_lo + w_hi * v_hi

    # ========== transform from Xm to Xf coordinates ============= #
    vel_m = [transforms_mf[n].get_rotation().inverse().apply_to(vel[n]) for n in range(N)]

    return vel_m

def remove_sensor_motion_from_doppler_speed(pos_target, speed_target, vel_sensor):
    """Return an array.

        Parameters
        ----------
        pos_target : 3xN Vector
            position of the measurement points in Xs
        speed_target : array of length N
            uncorrected Doppler speed measured by the moving sensor. Positive
            if pointing away from the sensor
        vel_sensor : Vector
            velocity of the sensor expressed in Xs coordinates

        Returns
        -------
        array of length N
            corrected Doppler speed (effect of sensor motion is removed)

        History
        -------
        2017-12-19 (AA): Created
    """
    ###################################################
    # INPUT CHECK                                     #
    ###################################################
    # vel_sensor
    assert isinstance(vel_sensor, Vector)
    assert not vel_sensor.is_array()

    # speed_target
    assert isinstance(speed_target, np.ndarray)

    # pos_target
    assert isinstance(pos_target, Vector)
    assert pos_target.is_array()
    assert pos_target.length() == len(speed_target)

    ###################################################
    # COMPUTATIONS                                    #
    ###################################################
    # unit vector pointing in target direction
    u = pos_target.unit_vector()

    # speed of the sensor along the measurement direction
    speed_sensor = u.dot(vel_sensor)

    # remove from Doppler velocity
    return speed_target - speed_sensor
