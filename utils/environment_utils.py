G_CONSTANT = 9.80665  # m/s^2

def weight(mass):
    """
    Computes the weight of an aircrafts given its mass
    :param mass: in kg
    :return: weight in N
    """
    return round(mass * G_CONSTANT)

def temperature(altitude: float) -> float:
    """
    Computes the temperature at a given altitude
    :param altitude: in m
    :return: temperature in K
    """
    return 288.16 - 6.5*10**-3 * altitude

def atmosphere_params(condition: str):
    if condition == 'good':
        tgl = 288.15 # Ground temperature [K]
        dgl = 1.225 # Ground density [kg/m^3]
        return tgl, dgl
    elif condition == 'bad':
        tgl = 300 # Ground temperature [K]
        dgl = 0.974 # Ground density [kg/m^3]
        return tgl, dgl
    else:
        raise ValueError('Invalid atmosphere condition. Choose between "good" and "bad"')

def air_density(altitude: float, atmosphere_condition: str='good'):
    """
    Computes the air density at a given altitude
    :param atmosphere_condition: default: good
    :param altitude: in m
    :return: air density in kg/m^3
    """
    tgl, dgl = atmosphere_params(atmosphere_condition)
    return round(dgl * (temperature(altitude)/tgl)**((G_CONSTANT/(287*6.5*10**-3))-1), 4)
