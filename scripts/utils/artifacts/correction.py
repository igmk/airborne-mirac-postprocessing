#!/usr/bin/python

from utils.artifacts import mirac

def main(data, setup):
    """Delegate job to sensor-specific module.

        Parameters
        ----------
        data : dict
        setup : dict

        Returns
        -------
        data : dict
    """
    sensor_name = setup['payload_sensor_name'].lower()

    if sensor_name == 'mirac':
        return mirac.main(data, setup)
    elif sensor_name == 'amali':
        # No correction to be done --> return to calling function.
        return data
    else:
        raise NotImplementedError(
                'Payload sensor not implemented: %s' % sensor_name)
