#!/usr/bin/python2
"""I/O initializiation."""

def import_sensor(setup):
    """Add payload sensor I/O module as 'io_sensor' to setup."""
    if 'io_sensor' not in setup:
        sensor_name = setup['payload_sensor_name']

        if sensor_name == 'amali':
            import utils.in_out.amali as io_sensor
        elif sensor_name == 'hampmira':
            import utils.in_out.hampmira as io_sensor
        elif sensor_name == 'mirac':
            import utils.in_out.mirac as io_sensor

        setup['io_sensor'] = io_sensor

    return setup

def get_io_sensor(setup):
    """Return payload sensor I/O submodule."""
    if 'io_sensor' not in setup:
        import_sensor(setup)
    return setup['io_sensor']
