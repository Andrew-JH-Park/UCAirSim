from models.passenger import Passenger
from scheduler import Scheduler
import pandas as pd
import asyncio


class UAMSimulation:
    def __init__(self, env, network, passenger_data, mission_profile, update_interval=120, start_time=6*3600, end_time=86400, run_mode='visual', websocket_server=None):
        """
        Initializes the UAM Simulation.

        :param env: SimPy environment
        :param network: UAMNetwork instance
        :param passenger_data: DataFrame containing passenger arrival data
        :param update_interval: Time in seconds for periodic network updates
        :param run_mode: "visual" or "fast" - does not do regular update
        """
        self.env = env
        self.network = network
        self.network.simulation = self
        self.passenger_data = passenger_data
        self.update_interval = update_interval
        self.start_time = start_time
        self.end_time = end_time
        self.mission_profile = mission_profile
        self.scheduler = Scheduler(env, network, mission_profile, run_mode=run_mode)
        self.run_mode = run_mode
        self.websocket_server = websocket_server

        if self.run_mode == "fast":
            self.websocket_server = None

        # Start simulation processes
        self.env.process(self.run())
        self.env.process(self.passenger_arrival_process())

        # network state log
        self.distribution_history = []
        self.passenger_trip_log = []
        self.vehicle_trip_log = []

    def run(self):
        """Main simulation loop handling network updates."""
        yield self.env.timeout(self.start_time)

        while self.env.now  <= self.end_time:
            yield self.env.timeout(self.update_interval)  # Perform network check
            self.network.update_network()
            self.scheduler.make_dispatch_decision()

            # logging network state
            dist_state = self.get_aircraft_distribution_state()
            self.distribution_history.append(dist_state)

            # Send updates to WebSocket server at every update_interval
            if self.websocket_server:
                state = self.get_current_state()
                asyncio.create_task(self.websocket_server.send_update(state))  # Send state asynchronously


    def passenger_arrival_process(self):
        """Handles passenger arrivals as a separate process."""
        for _, passenger_info in self.passenger_data.iterrows():
            arrival_time = self.time_to_seconds(passenger_info['arrival_time'])
            if arrival_time > self.end_time:
                break # break if end time is reached

            pid = passenger_info['passenger_id']
            if self.run_mode == "visual":
                print(f'passenger id: {pid} \n \t arrival time: {arrival_time} \t env time: {self.env.now}')

            yield self.env.timeout(arrival_time - self.env.now)  # Pause until passenger arrives
            self.process_passenger_arrival(passenger_info)

    def process_passenger_arrival(self, passenger_info):
        """Handles passenger arrival at a vertiport."""

        itinerary = self.network.compute_itinerary(passenger_info['origin'], passenger_info['destination'])

        passenger = Passenger(
            env=self.env,
            passenger_id=passenger_info['passenger_id'],
            network = self.network,
            itinerary=itinerary
        )

        passenger.journey_process = self.env.process(passenger.journey())
        self.env.process(self.monitor_passenger(passenger))

    @staticmethod
    def time_to_seconds(time_str):
        """Converts time in HH:MM:SS format to seconds past midnight."""
        h, m, s = map(int, time_str.split(':'))
        return (h * 3600) + (m * 60) + s

    def get_current_state(self):
        state=[]

        for _, ac in self.network.aircrafts.items():
            if ac.state == "flying":
                state.append({
                    'vehicle': ac.vehicle,
                    'id': ac.aircraft_id,
                    'lat': ac.position[0],
                    'lon': ac.position[1],
                    'alt': ac.position[2],
                    'v_h': ac.speed_horizontal,
                    'v_v': ac.speed_vertical,
                    'heading': ac.heading,
                    'soc': ac.battery.soc
                })

        return{
            'time': self.env.now,
            'aircrafts': state
        }

    def get_aircraft_distribution_state(self):
        """
        Returns aircraft distribution:
        - aircraft_at_node: dict[node_id] = number of aircraft parked
        - aircraft_inbound_to_node: dict[node_id] = number of aircraft en route to that node
        """
        aircraft_at_node = {node_id: 0 for node_id in self.network.vertiports}
        aircraft_inbound_to_node = {node_id: 0 for node_id in self.network.vertiports}

        for aircraft in self.network.aircrafts.values():
            if aircraft.state == "flying":
                # Aircraft is flying toward a destination
                dest_id = aircraft.destination_vertiport.vertiport_id
                if dest_id in aircraft_inbound_to_node:
                    aircraft_inbound_to_node[dest_id] += 1
                else:
                    aircraft_inbound_to_node[dest_id] = 1  # Just in case not initialized

            elif aircraft.state in ("idle", "charge"):
                # Aircraft is parked at a vertiport
                origin_id = aircraft.origin_vertiport.vertiport_id
                if origin_id in aircraft_at_node:
                    aircraft_at_node[origin_id] += 1
                else:
                    aircraft_at_node[origin_id] = 1  # Just in case

        return {
            "time": self.env.now,
            "aircraft_at_node": aircraft_at_node,
            "aircraft_inbound_to_node": aircraft_inbound_to_node
        }

    def monitor_passenger(self, passenger):
        """Waits for journey to complete, then logs trip result."""
        yield passenger.journey_process  # wait until journey ends
        self.passenger_trip_log.append(passenger.trip_result)
