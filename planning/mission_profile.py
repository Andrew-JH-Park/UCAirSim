"""
Creating mission profile given
1) waypoints
2) Aircraft specifications
3) Flight modes
4) Weather conditions
"""

import os
import pandas as pd
import numpy as np
from utils.flight_utils import (compute_heading, create_departure_fix, create_arrival_fix,
                                hover_climb, compute_vertical_time_to_climb, compute_2d_distance,
                                compute_delta_altitude, climb_descent, cruise, transition)

WAYPOINT_PATH = os.path.join(os.curdir, 'input/waypoints')
OUTPUT_PATH = os.path.join(os.curdir, 'output/mission_plans')
PARAM_PATH = os.path.join(os.curdir, 'input/specifications')

TRANSITION_TIME = 30 # assume 30 second transition
VTOL_VERTICAL_SPEED = 2 # assume 2 m/s vertical speed
TRANSITION_HORIZONTAL_SPEED = 20 # assume 20 m/s horizontal speed at the end of transition
TRANSITION_VERTICAL_SPEED = 2 # assume 2 m/s vertical speed at the end of transition

def create_mission_profile(nodes_df, edges_df, save_result=True):

    aircraft_params = pd.read_csv(os.path.join(PARAM_PATH, 'evtol_spec.csv'), index_col=0)

    mission_profile = {}
    # for each edge, for each aircrafts, create a mission profile
    for _, row in edges_df.iterrows():
        waypoint_file = os.path.join(WAYPOINT_PATH, row['waypoints']+'.csv')
        wp = pd.read_csv(waypoint_file)

        for aircraft in aircraft_params.columns:
            param = aircraft_params[aircraft].to_dict()

            # create flight profile for each flight phase
            # Aircraft must be LPC

            mission_profile_df = flight_profile(wp, param)
            file_name = row['waypoints']+'_'+aircraft+'.csv'
            if save_result:
                mission_profile_df.to_csv(os.path.join(OUTPUT_PATH, file_name))

            mission_profile[row["waypoints"]] = {aircraft: mission_profile_df}

    return mission_profile


def flight_profile(waypoints, aircraft_parameter):

    def update_row():
        nonlocal flight_profile_df
        nonlocal accumulated_time

        accumulated_time += time

        new_row = {
            "waypoint_id": row['waypoint_id'],
            "latitude": next_position[0],
            "longitude": next_position[1],
            "altitude": next_position[2],
            "time": time,
            "accumulated time": accumulated_time,
            "phase": flight_mode,
            "average_power": power,
            "energy_budget": energy,
            "v_vertical": vertical_speed,
            "v_horizontal": horizontal_speed,
            "heading": heading
        }

        flight_profile_df = pd.concat([flight_profile_df, pd.DataFrame([new_row])], ignore_index=True)

    origin_position = (waypoints['latitude'].iloc[0], waypoints['longitude'].iloc[0], waypoints['altitude'].iloc[0])
    destination_position = (waypoints['latitude'].iloc[-1], waypoints['longitude'].iloc[-1], waypoints['altitude'].iloc[-1])
    current_position = origin_position

    flight_profile_df = pd.DataFrame()

    phase = ''
    time, power, energy, accumulated_time, vertical_speed, horizontal_speed = (0, 0, 0, 0, 0, 0)
    transition_timer = TRANSITION_TIME

    # calculate departure and arrival fix
    waypoints = create_departure_fix(waypoints, origin_position, TRANSITION_TIME, VTOL_VERTICAL_SPEED)
    waypoints = create_arrival_fix(waypoints, destination_position, TRANSITION_TIME, VTOL_VERTICAL_SPEED)

    for ind, row in waypoints.iterrows():
        flight_mode = row['flight_mode']
        next_position = (row['latitude'], row['longitude'], row['altitude'])

        heading = compute_heading(current_position, next_position)

        if flight_mode == 'idle':
            update_row()
            continue

        elif flight_mode == 'hover_climb' or flight_mode == 'hover_descent':

            direction = np.sign(next_position[2]-current_position[2])

            vertical_speed = VTOL_VERTICAL_SPEED*direction
            horizontal_speed = 0
            power, time = hover_climb(aircraft_parameter, current_position, next_position, vertical_speed)

        elif flight_mode == 'climb_transition' or flight_mode == 'descent_transition':

            direction = np.sign(next_position[2] - current_position[2])
            vertical_speed = VTOL_VERTICAL_SPEED * direction
            time = compute_vertical_time_to_climb(current_position, next_position, vertical_speed)
            horizontal_distance = compute_2d_distance(current_position, next_position)

            v_h1, v_h2 = 0.0,0.0
            if horizontal_speed <= 1e-3: # transitioning from hover climb
                v_h1 = 0.0
            else:
                v_h1 = horizontal_speed

            # if waypoints.iloc[ind+1]['flight_mode']=='hover_descent': # transition to hover descent
            #     v_h2 = 0
            # else:
            v_h2 = horizontal_distance / time

            # limit transition speed to within 20 mps
            # ==> slower vertical speed
            if v_h2 > 20.0:
                v_h2 = 20.0
                time = horizontal_distance/v_h2
                delta_altitude = compute_delta_altitude(current_position, next_position)
                vertical_speed = delta_altitude/time

            horizontal_speed = v_h2
            power = transition(aircraft_parameter, current_position, next_position, vertical_speed, v_h1, v_h2)

        elif flight_mode == 'climb' or flight_mode == 'descent':
            # check if next is descent transition - limit descent rate
            delta_distance = compute_2d_distance(current_position, destination_position)
            delta_altitude = np.abs(compute_delta_altitude(current_position, destination_position))
            # print(f'evaluating OD@{row["origin"]}-{row["destination"]} wp_id: {row["waypoint_id"]}\n'
            #       f'\t delta_distance:{delta_distance} \t delta_altitude: {delta_altitude}')
            if delta_distance <= 1000 and delta_altitude <= 300:
                h_speed_range = np.linspace(10, 20, 101)
            elif delta_distance<= 2000:
                h_speed_range = np.linspace(10, 30, 201)
            else:
                h_speed_range = np.linspace(10, 80, 701)

            time, best_speeds, power = climb_descent(aircraft_parameter, current_position, next_position, h_speed_range=h_speed_range)
            vertical_speed = best_speeds[0]
            horizontal_speed = best_speeds[1]

            if power < 0:
                raise Warning(f"check {row['waypoint_id']}; the rate of descent is not appropriate and outputting negative descent power. Consider adjusting the waypoint")

        elif flight_mode == 'cruise':
            # assume flying at max range (max ld)
            max_ld, min_power = cruise(aircraft_parameter, current_position, next_position)
            time = max_ld[0]
            horizontal_speed = max_ld[1]
            vertical_speed = 0
            power = max_ld[2]

        else:
            raise ValueError(f'check waypoints from {waypoints["origin"][0]} to {waypoints["destination"][0]} flight mode: {flight_mode} is not valid')

        energy = power * 1e-3 * time / 3600  # conversion to kWh

        update_row()
        #update current position
        current_position = next_position


    return flight_profile_df
