import numpy as np
from utils.environment_utils import air_density, weight

def vtol_power(params, start_altitude, end_altitude, vertical_velocity):
    tow = weight(params['mtom'])
    disk_area = params['mtom']/params['disk_load']

    start_density = air_density(altitude=start_altitude)
    end_density = air_density(altitude=end_altitude)

    # calculate power consumption
    term1 = params['f'] * tow / params['FoM']
    term2_start = np.sqrt(params['f'] * tow / disk_area / (2 * start_density))
    term2_end = np.sqrt(params['f'] * tow / disk_area / (2 * end_density))
    term3 = tow * vertical_velocity / 2

    start_power = max((term1 * term2_start + term3) / params['eta_hover'], 0)
    end_power = max((term1 * term2_end + term3) / params['eta_hover'], 0)

    power_consumption = (start_power + end_power) / 2

    return power_consumption

def transition_power(altitude, params):
    """
    Returns transition start or end power in kW
    """
    tow = weight(params['mtom'])
    density = air_density(altitude=altitude)
    disk_area = params['mtom'] / params['disk_load']

    term1 = params['f'] * tow / params['FoM']
    term2 = np.sqrt(params['f'] * tow / disk_area / (2 * density))

    return (term1 * term2) / params['eta_hover']


def climb_descend_power(params, altitude, vertical_velocity, horizontal_velocity):
    """
    Returns general climb power in kW
    """
    density = air_density(altitude=altitude)
    tow = weight(params['mtom'])
    e_osw = params['oswald_efficiency']
    s = params['wing_area']
    b = params['wingspan']
    Cd0 = params['cd_0']
    aspect_ratio = b**2/s

    V_air_spd = np.sqrt(vertical_velocity ** 2 + horizontal_velocity ** 2)
    P_weight = tow * vertical_velocity  # power needed to lift the weight with some speed

    Cl = tow * horizontal_velocity / ((0.5 * density * V_air_spd ** 3) * s)
    Cd_induced = Cl ** 2 / (np.pi * e_osw * aspect_ratio)

    D_parasitic = 0.5 * density * (V_air_spd ** 2) * s * Cd0
    D_induced = 0.5 * density * (V_air_spd ** 2) * s * Cd_induced
    Drag = D_parasitic + D_induced
    P_req = Drag * V_air_spd

    P_climb = (P_weight + P_req)/params['eta_descend']

    return P_climb

def climb_transition_phase_power(start_altitude, end_altitude, aircraft_params, vertical_velocity, horizontal_velocity):
    climb_transition_start_power = transition_power(altitude=start_altitude, params=aircraft_params)
    climb_transition_start_power = max(climb_transition_start_power, 0)
    climb_transition_end_power = climb_descend_power(aircraft_params, end_altitude, vertical_velocity, horizontal_velocity)
    climb_transition_end_power = max(climb_transition_end_power, 0)
    return (climb_transition_start_power + climb_transition_end_power)/2

def cruise_power(params, altitude, horizontal_velocity):
    density = air_density(altitude=altitude)
    tow = weight(params['mtom'])
    e_osw = params['oswald_efficiency']
    s = params['wing_area']
    b = params['wingspan']
    Cd0 = params['cd_0']
    aspect_ratio = b**2/s

    Cl = tow / (.5 * density * horizontal_velocity ** 2 * s)
    q_air = .5 * density * horizontal_velocity ** 2
    Cd_induced = Cl**2/(np.pi*e_osw*aspect_ratio)
    Cd = Cd0 + Cd_induced
    l_d = Cl/Cd

    P_req = (tow/l_d)*horizontal_velocity/params['eta_cruise']

    return l_d, P_req