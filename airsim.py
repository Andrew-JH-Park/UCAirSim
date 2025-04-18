from models.passenger import Passenger
from scheduler import Scheduler
import asyncio

class UAMSimulation:
    def __init__(self, env, network, passenger_data, mission_profile, update_interval=120, end_time=86400, run_mode='visual', websocket_server=None):
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
        self.passenger_data = passenger_data
        self.update_interval = update_interval
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

    def run(self):
        """Main simulation loop handling network updates."""
        while self.env.now  <= self.end_time:
            yield self.env.timeout(self.update_interval)  # Perform network check
            self.network.update_network()
            self.scheduler.make_dispatch_decision()

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
        origin_vertiport = self.network.vertiports.get(passenger_info['origin'])
        destination_vertiport = self.network.vertiports.get(passenger_info['destination'])

        passenger = Passenger(
            passenger_id=passenger_info['passenger_id'],
            origin=origin_vertiport,
            destination=destination_vertiport,
            arrival_time=self.env.now
        )

        origin_vertiport.add_passenger(passenger)
        if self.run_mode == "visual":
            print(f"{self.env.now}: Passenger {passenger.passenger_id} arrived at {passenger.origin.vertiport_id}")

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