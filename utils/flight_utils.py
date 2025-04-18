import numpy as np
from math import sqrt, radians, degrees, atan2, sin, cos
import pandas as pd
from utils.power_model import vtol_power, transition_power, climb_descend_power, cruise_power
from utils.environment_utils import temperature, air_density, weight
from typing import Tuple, Dict
G_CONSTANT = 9.80665  # m/s^2

def compute_heading(current_position, destination_position):
    lat1, lon1, _ = current_position
    lat2, lon2, _ = destination_position
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = sin(dlon) * cos(lat2)
    y = cos(lat1)*sin(lat2) - sin(lat1)*cos(lat2)*cos(dlon)
    initial_bearing = atan2(x, y)

    return (degrees(initial_bearing) + 360) % 360


def create_3d_line(origin: Tuple[float, float, float],
                   destination: Tuple[float, float, float]) -> Dict[str, Tuple[float, float, float]]:
    """
    Returns both (dx, dy, dz) in meters and (dlat, dlon, dalt) in degrees/meters.
    """
    lat1, lon1, alt1 = origin
    lat2, lon2, alt2 = destination

    # Average latitude for scale
    lat_rad = radians((lat1 + lat2) / 2)
    meters_per_deg_lat = 111_132
    meters_per_deg_lon = 111_320 * cos(lat_rad)

    dx = (lon2 - lon1) * meters_per_deg_lon
    dy = (lat2 - lat1) * meters_per_deg_lat
    dz = alt2 - alt1

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    dalt = alt2 - alt1

    return {
        "origin": origin,
        "destination": destination,
        "line_cartesian": (dx, dy, dz),
        "line_geodetic": (dlat, dlon, dalt)
    }


def query_line(line: Dict[str, Tuple[float, float, float]],
               value: float,
               axis: str,
               input_mode: str = 'cartesian',
               output_mode: str = 'cartesian') -> tuple[float, ...] | tuple[float, float, float]:
    """
    Query the line using one value along an axis, and return all 3 variables
    in the specified output_mode ('xyz' or 'coordinate').

    axis: 'x', 'y', 'z' (for xyz) OR 'lat', 'lon', 'alt' (for coordinates)
    value: the value along that axis
    """
    if input_mode == 'cartesian':
        dx, dy, dz = line['line_cartesian']
        if axis == 'x' and dx != 0:
            t = value / dx
        elif axis == 'y' and dy != 0:
            t = value / dy
        elif axis == 'z' and dz != 0:
            t = value / dz
        else:
            raise ValueError("Invalid axis or zero length in that direction.")
    elif input_mode == 'geodetic':
        dlat, dlon, dalt = line['line_geodetic']
        lat0, lon0, alt0 = line['origin']
        if axis == 'lat' and dlat != 0:
            t = (value - lat0) / dlat
        elif axis == 'lon' and dlon != 0:
            t = (value - lon0) / dlon
        elif axis == 'alt' and dalt != 0:
            t = (value - alt0) / dalt
        else:
            raise ValueError("Invalid axis or zero length in that direction.")
    else:
        raise ValueError("input_mode must be 'cartesian' or 'geodetic'")

    if output_mode == 'cartesian':
        return tuple(t * v for v in line['line_cartesian'])
    elif output_mode == 'geodetic':
        lat0, lon0, alt0 = line['origin']
        dlat, dlon, dalt = line['line_geodetic']
        return lat0 + dlat * t, lon0 + dlon * t, alt0 + dalt * t
    else:
        raise ValueError("output_mode must be 'cartesian' or 'geodetic'")


def compute_2d_distance(current_position, next_position):
    lat1, lon1, _ = current_position
    lat2, lon2, _ = next_position

    # Radius of the Earth in meters
    R = 6371000

    # Convert degrees to radians
    lat1_rad, lat2_rad = radians(lat1), radians(lat2)
    delta_lat = lat2_rad-lat1_rad
    delta_lon = radians(lon2 - lon1)

    # Haversine formula
    a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c  # in meters
    return distance

def compute_delta_altitude(current_position, next_position):
    _,_, alt1 = current_position
    _,_, alt2 = next_position

    delta_altitude = alt2 - alt1

    return delta_altitude


def compute_vertical_time_to_climb(current_position, next_position, vertical_velocity):
    distance = compute_delta_altitude(current_position, next_position)
    time_to_climb = round(distance / vertical_velocity)

    return time_to_climb

def lift_induced_drag_coef(cd_0: float, ld_max: float) -> float:
    """
    From the paper:
    The promise of energy-efficient battery-powered urban aircrafts
    """
    return 1 / (4*cd_0*ld_max**2)

def climb_power_consumption_for_lift(tom, vertical_velocity):
    """
    From the paper:
    The promise of energy-efficient battery-powered urban aircrafts

    tom: take-off mass in kg
    """
    return weight(tom)*vertical_velocity

def climb_power_consumption_for_drag(altitude, atmosphere_condition, wing_area, cd_0, ld_max, tom, horizontal_speed):
    """
    From the paper:
    The promise of energy-efficient battery-powered urban aircrafts
    """
    term2 = 1/2 * air_density(altitude, atmosphere_condition) * wing_area * cd_0 * horizontal_speed ** 3
    term3 = lift_induced_drag_coef(cd_0, ld_max) * weight(tom)**2 / (1/2*air_density(altitude, atmosphere_condition) \
                                    * wing_area * horizontal_speed)
    return term2 + term3



def rotor_disk_area(mtom, disk_load):
    """
    Computes the rotor disk area given the maximum take-off mass and the disk load
    :param mtom: in kg
    :param disk_load: in kg/m^2
    :return: rotor disk area in m^2
    """
    return mtom / disk_load

def stall_speed(atmosphere_condition, altitude, mtom, wing_area, cl_max):
    """
    Computes the stall speed of an aircrafts given its mass
    :param mass: in kg
    :return: stall speed in m/s
    """
    return round(np.sqrt((2*weight(mtom))/(air_density(altitude, atmosphere_condition)*wing_area*cl_max)))

def compute_max_ld(aircraft):
    aspect_ratio = aircraft.aspect_ratio
    Cd0 = aircraft.Cd0
    e_osw = aircraft.oswald_efficiency

    Cl_max = np.sqrt(np.pi * e_osw * aspect_ratio * Cd0)
    l_d_max = Cl_max/(Cd0*2)

    return  l_d_max

def compute_cruise_speed(aircraft, altitude):
    """
    numerically solve for optimal airspeed given altitude
    assume fly at max L/D for max range (ideal level-flight performance)

    :param aircraft: Class Aircraft instance
    :param altitude: float altitude
    :return: float airspeed for max range flight
    """
    w = aircraft.weight
    s = aircraft.wingspan
    Cd0 = aircraft.Cd0
    l_d_max = aircraft.l_d_max
    Cl_max = l_d_max*Cd0*2
    rho = air_density(altitude)

    V_max_ld = np.sqrt(w / (.5 * rho * s *Cl_max))

    return V_max_ld

def update_position(current_position, next_position, v_h, v_v, delta_t):
    """Computes updated aircrafts position using Euclidean distance interpolation.

    :param current_position: Tuple (lat, lon) of the current position
    :param next_position: Tuple (lat, lon) of the destination
    :param v_h: Horizontal speed in m/s
    :param v_v: Vertical speed in m/s
    :param delta_t: Time interval for update in seconds
    :return: New position (lat, lon) after delta_t
    """
    lat1, lon1, alt1 = current_position
    lat2, lon2, alt2  = next_position

    horizontal_distance = compute_2d_distance(current_position, next_position)
    vertical_distance = compute_delta_altitude(current_position, next_position)

    if np.sign(vertical_distance) != np.sign(v_v):
        print("Warning: vertical and sign mismatch")

    # if np.sign(vertical_distance) < 0:
    #     print('debug')
    # Compute movement step based on speed and delta_t

    step_h = min(v_h * delta_t, horizontal_distance)  # Don't overshoot
    step_v = min(np.abs(v_v * delta_t), np.abs(vertical_distance))*np.sign(vertical_distance)
    # Compute new lat, lon using interpolation

    ratio = step_h / horizontal_distance if horizontal_distance > 0 else 0

    new_lat = lat1 + ratio * (lat2 - lat1)
    new_lon = lon1 + ratio * (lon2 - lon1)
    new_alt = alt1 + step_v

    return new_lat, new_lon, new_alt

def create_departure_fix(waypoints, origin_position, transition_time, vtol_speed):
    new_waypoints = pd.DataFrame()
    wp_vto_end = waypoints.iloc[1]
    wp_origin = waypoints.iloc[0]

    vto_end_alt = wp_vto_end['altitude']
    transition_end_alt = vto_end_alt+(transition_time*vtol_speed)

    for ind, row in waypoints[2:].iterrows():
        wp_alt = row['altitude']
        if wp_alt <= transition_end_alt:
            waypoints.loc[ind, 'flight_mode'] = 'climb_transition'

        else:
            prev_wp = waypoints.iloc[ind-1]
            current_position = (row['latitude'], row['longitude'], row['altitude'])
            previous_position = (prev_wp['latitude'], prev_wp['longitude'], prev_wp['altitude'])

            line = create_3d_line(previous_position, current_position)
            query_z = transition_end_alt-previous_position[2]
            updated_position = query_line(line, value=query_z, axis='z', input_mode='cartesian', output_mode='geodetic')

            departure_fix = {
                "origin": row['origin'],
                "destination": row['destination'],
                "latitude": updated_position[0],
                "longitude": updated_position[1],
                "altitude": updated_position[2],
                "waypoint_id": prev_wp['waypoint_id']+'-2',
                "flight_mode": 'climb_transition'}

            upper = waypoints.iloc[:ind]  # includes index 10
            lower = waypoints.iloc[ind:]  # from index 11 onward

            # add arrival fixture to the waypoints
            new_waypoints = pd.concat([upper, pd.DataFrame([departure_fix]), lower], ignore_index=True)
            break

    return new_waypoints

def create_arrival_fix(waypoints, destination_position, transition_time, vtol_speed):
    # assume descent starts at altitude = transition time * descent speed (2*30) + destination altitude + hover descent altitude
    # assume hover descent position at iloc[-2]
    new_waypoints = pd.DataFrame()
    wp_vl_start = waypoints.iloc[-2]
    wp_destination = waypoints.iloc[-1]

    vl_start_alt = wp_vl_start['altitude']

    if (np.abs(wp_vl_start['latitude']-destination_position[0])>=1e-4) or (np.abs(wp_vl_start['longitude']-destination_position[1])>=1e-4):
        raise ValueError(f"Destination latlon mismatch for waypoint {wp_destination['origin']}-{wp_destination['destination']} between the last and second last waypoints")

    # descent transition must start
    transition_start_alt = vl_start_alt+(transition_time*vtol_speed)

    for ind, row in waypoints[-3::-1].iterrows():
        wp_alt = row['altitude']
        if wp_alt <= transition_start_alt:
            waypoints.loc[ind+1, 'flight_mode'] = 'descent_transition'
        else:
            # create a split point
            next_wp = waypoints.iloc[ind+1]
            current_position = (row['latitude'], row['longitude'], row['altitude'])
            next_position = (next_wp['latitude'], next_wp['longitude'], next_wp['altitude'])

            line = create_3d_line(current_position, next_position)
            query_z = transition_start_alt-current_position[2]
            updated_position = query_line(line, value=query_z, axis='z', input_mode='cartesian', output_mode='geodetic')

            arrival_fix = {
                "origin": row['origin'],
                "destination": row['destination'],
                "latitude": updated_position[0],
                "longitude": updated_position[1],
                "altitude": updated_position[2],
                "waypoint_id": row['waypoint_id']+'-2',
                "flight_mode": 'descent'}

            waypoints.loc[ind + 1, 'flight_mode'] = 'descent_transition'

            upper = waypoints.iloc[:ind+1]  # includes index 10
            lower = waypoints.iloc[ind+1:]  # from index 11 onward

            # add arrival fixture to the waypoints
            new_waypoints = pd.concat([upper, pd.DataFrame([arrival_fix]), lower], ignore_index=True)
            break

    return new_waypoints


def hover_climb(aircraft_params, current_position, next_position, vertical_velocity):
    _,_,alt1 = current_position
    _,_,alt2 = next_position

    time = compute_vertical_time_to_climb(current_position, next_position, vertical_velocity)
    power_consumption = vtol_power(aircraft_params, alt1, alt2, vertical_velocity)
    return power_consumption, time

def transition(aircraft_params, current_position, next_position, v_v, v_h1, v_h2):
    lat1,lon1,alt1 = current_position
    lat2,lon2,alt2 = next_position

    # power 1
    if v_h1 == 0:
        transition_start_power = transition_power(altitude=alt1, params=aircraft_params)
    else:
        transition_start_power = climb_descend_power(aircraft_params, alt1, v_v, v_h1)

    # power 2
    if v_h2 == 0:
        transition_end_power = transition_power(altitude=alt2, params=aircraft_params)
    else:
        transition_end_power = climb_descend_power(aircraft_params, alt1, v_v, v_h1)

    return (transition_start_power+transition_end_power)/2

def climb_descent(aircraft_params, current_position, next_position, h_speed_range=np.linspace(10, 100, 901)):
    """
    For each horizontal speed, calculate required vertical speed to match end altitude
    over the ground distance, then compute climb power.
    """

    lat1,lon1,alt1 = current_position
    lat2,lon2,alt2 = next_position

    dz = alt2 - alt1
    d_xy = compute_2d_distance(current_position, next_position)

    best_power = np.inf
    best_speeds = (0, 0)
    best_time = 0

    for v_h in h_speed_range:
        if v_h == 0:
            continue
        t = d_xy / v_h
        v_v = dz / t  # required vertical speed

        power1 = climb_descend_power(aircraft_params, altitude=alt1, vertical_velocity=v_v, horizontal_velocity=v_h)
        power2 = climb_descend_power(aircraft_params, altitude=alt2, vertical_velocity=v_v, horizontal_velocity=v_h)
        power = (power1+power2)/2
        if (power < best_power) & (power >= 0):
            best_power = power
            best_speeds = (v_v, v_h)
            best_time = t
        elif power < 0:
            print(f"warning: negative power {current_position}: speeds {(v_v, v_h)} and best time {t}")

    return best_time, best_speeds, best_power

def cruise(aircraft_params, current_position, next_position, h_speed_range = np.linspace(20, 120, 100)):
    lat, lon, alt = current_position
    l_d, P_req = cruise_power(aircraft_params, alt, h_speed_range)

    V_max_ld = h_speed_range[np.argmax(l_d)]
    V_min_power = h_speed_range[np.argmin(P_req)]

    l_d_max, P_max_ld = cruise_power(aircraft_params, alt, V_max_ld)
    l_d_min_power, P_min_power = cruise_power(aircraft_params, alt, V_min_power)

    distance = compute_2d_distance(current_position, next_position)
    time_max_ld = distance/V_max_ld
    time_min_power = distance / V_min_power

    return (time_max_ld, V_max_ld, P_max_ld), (time_min_power, V_min_power, P_min_power)


def descent_transition():
    """
    transition from fixed wing to vtol before hover descent phase
    :return:
    """
    return 0

def hover_descent():
    return 0

