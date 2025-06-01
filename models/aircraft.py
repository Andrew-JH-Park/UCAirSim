from models.battery import Battery
import utils.flight_utils as fl
import logging

0
UPDATE_INTERVAL = 10 # for visualization update interval
STATIC_SOC_FOR_FLIGHT = 0.9 # static charge policy

class Aircraft:
    def __init__(self, env, vehicle, aircraft_id, network, origin_vertiport, specification):
        self.env = env
        self.network = network
        self.vehicle = vehicle
        self.origin_vertiport = origin_vertiport
        self.destination_vertiport = None
        self.aircraft_id = aircraft_id
        self.aircraft_params = specification # dataframe or dict storing all aircraft specifications
        self.flying_route = None #pointer to airspace currently occupying
        self.current_passengers = [] # list of current passengers

        self.flight_ready = True
        self.state = "idle" # idle, charge, flying
        self.flight_mode = None #hover climb, climb, cruise, descent, hover descent
        self.flight_plan = None
        self.current_waypoint = None
        self.battery = Battery(battery_capacity=160)  # 100% SoC
        self.tom = self.aircraft_params['mass'] #empty mass
        self.disk_area = self.aircraft_params['mtom']/self.aircraft_params['disk_load']
        self.min_soc = 20  # Minimum SoC reserve for landing sequence
        self.charging_start_time = 0

        self.position = self.origin_vertiport.location
        self.speed_horizontal = 0  # m/s
        self.speed_vertical = 0 # m/s
        self.travel_time = 0
        self.heading = 0

    def fly(self, destination, run_mode):
        """Triggers flight to a new vertiport."""

        # logging
        start_time = self.env.now
        start_soc = self.battery.soc
        origin_id = self.origin_vertiport.vertiport_id
        dest_id = destination.vertiport_id
        num_passengers = len(self.current_passengers)

        # departure logic
        self.state = "flying"
        self.flight_ready = False
        self.destination_vertiport = destination
        self.position = self.origin_vertiport.location
        if (self.origin_vertiport.vertiport_id == 'UCD' and self.destination_vertiport.vertiport_id == 'NASA'):
            print('debug')
        self.flying_route = self.network.airspaces[self.origin_vertiport.vertiport_id, self.destination_vertiport.vertiport_id]
        self.flight_plan = self.flying_route.mission_profile[self.vehicle] # flight plan based on waypoints - use mission profiling in the future
        self.origin_vertiport.remove_aircraft(self)  # Aircraft leaves vertiport
        self.tom = self.tom + len(self.current_passengers)*100 # calculate mass based on current passengers

        flight_time = 0.0

        # fly in sequence
        if run_mode == "visual":
            print(
                f"{self.env.now}: {self.aircraft_id} taking off from {self.origin_vertiport.vertiport_id} to {destination.vertiport_id}")


        # enter airspace
        enter_flag = self.flying_route.enter_airspace(self)
        if not enter_flag:
            yield self.env.timeout(self.flying_route.compute_time_until_availability())
            enter_flag = self.flying_route.enter_airspace(self)

            if not enter_flag:
                raise Exception(f"{self.env.now}: {self.aircraft_id} unable to enter airspace - exception flag")


        for _, row in self.flight_plan.iterrows():
            next_position = (row['latitude'], row['longitude'], row['altitude'])
            self.current_waypoint = row['waypoint_id']
            self.flight_mode = row['phase']
            self.travel_time = row['time']
            self.speed_vertical = row['v_vertical']
            self.speed_horizontal = row['v_horizontal']
            self.heading = row['heading']

            average_power = row['average_power']*1e-3
            energy_spent = row['energy_budget']

            if run_mode == "visual":
                print(
                    f"{self.env.now}: {self.aircraft_id} in transit at flight time: {flight_time}, position: {self.position}, phase: {self.flight_mode}, remaining soc: {self.battery.soc}")
                steps = self.travel_time // UPDATE_INTERVAL

                # create trajectory
                for _ in range(int(steps)):
                    flight_time += UPDATE_INTERVAL
                    yield self.env.timeout(UPDATE_INTERVAL)
                    self.position = fl.update_position(self.position, next_position,
                                                       self.speed_horizontal, self.speed_vertical, UPDATE_INTERVAL)
                    print(
                        f"{self.env.now}: {self.aircraft_id} in transit at flight time: {flight_time}, position: {self.position}, phase: {self.flight_mode}")

                remaining_time = round(self.travel_time % UPDATE_INTERVAL)
                flight_time += remaining_time
                yield self.env.timeout(remaining_time)
                self.position = next_position

            else:
                yield self.env.timeout(self.travel_time)
                flight_time += self.travel_time

            self.battery.update_soc_energy(energy_spent)

        # Arrival logic
        if run_mode == "visual":
            print(f"{self.env.now}: {self.aircraft_id} arrived at {self.destination_vertiport.vertiport_id} with remaining soc: {self.battery.soc}")

        self.flight_mode = None
        self.flight_plan = None
        self.current_waypoint = None
        self.position = destination.location
        self.tom = self.aircraft_params['mass'] # empty a/c

        # airspace control
        self.flying_route.exit_airspace(self)
        self.flying_route = None

        # destination control
        destination.park_aircraft(self)  # park ac at destination
        self.origin_vertiport = destination
        self.destination_vertiport = None

        # Remove passengers and mark them as served
        current_passengers = self.current_passengers.copy()
        for passenger in current_passengers:
            passenger.unboard_aircraft()
            if hasattr(passenger, "current_leg_complete"):
                passenger.current_leg_complete.succeed()
            else:
                logger.debug(f"[{self.env.now}] Aircraft id ({self.aircraft_id}) does not unboard passengers correctly : passengers {passenger.passenger_id}")

        if self.current_passengers:
            logger.debug(f"[{self.env.now}] Aircraft id ({self.aircraft_id}) does not unboard passengers correctly : current passenger number {len(self.current_passengers)}")

        self.tom = self.aircraft_params['mass']
        # self.network.log_served_passengers(served_passengers)

        # logging
        end_soc = self.battery.soc
        flight_time = self.env.now - start_time
        energy_consumed = (start_soc - end_soc) * self.battery.capacity

        trip_record = {
            "time": self.env.now,
            "aircraft_id": self.aircraft_id,
            "origin": origin_id,
            "destination": dest_id,
            "start_soc": start_soc,
            "end_soc": end_soc,
            "flight_time": flight_time,
            "num_passengers": num_passengers,
            "energy_consumed": energy_consumed
        }
        self.network.simulation.vehicle_trip_log.append(trip_record)

        # start charging
        self.state = "charge"
        self.charging_start_time = self.env.now


    def update_soc(self):
        charge_time = self.env.now - self.charging_start_time

        if self.state != "charge":
            logger.error(f"[{self.env.now}]: update soc called while vehicle state is not charge {self.aircraft_id}")

        self.battery.soc = self.origin_vertiport.charger.query_final_soc(
            initial_soc=self.battery.soc,
            charge_time_sec=charge_time
        )

        self.charging_start_time = self.env.now

        if self.battery.soc >= 0.99:
            self.state = "idle"
            self.flight_ready = True

        elif self.battery.soc >= 0.8:
            self.flight_ready = True

    def get_expected_arrival_time(self):
        if self.state != "flying":
            logger.warning(f"[{self.env.now}]: aircraft {self.aircraft_id} - get_expected_arrival_time queried when not flying")
            raise Warning("get_expected_arrival_time queried when not flying")

        else:
            row_ind = self.flight_plan.index[self.flight_plan['waypoint_id']==self.current_waypoint][0]
            remaining_flight_plan = self.flight_plan.iloc[row_ind:,:]
            remaining_time = remaining_flight_plan['time'].sum()
            energy_expectation = remaining_flight_plan['energy_budget'].sum()
            soc_expectation = self.battery.soc - (energy_expectation/self.battery.capacity)

            return remaining_time, soc_expectation

    def reserve_aircraft(self):
        if self.state == "charge":
            self.update_soc()
        self.flight_ready = False
        self.state = "idle"