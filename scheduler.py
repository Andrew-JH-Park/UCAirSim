class Scheduler:
    def __init__(self, env, network, mission_profile, passenger_threshold=4, max_wait_time=900, run_mode="visual"):
        """
        Initializes the Scheduler.

        :param env: SimPy environment
        :param network: UAMNetwork instance
        :param passenger_threshold: Number of passengers required to dispatch an aircraft (default 4)        :param max_wait_time: Maximum wait time in seconds before forcing dispatch (default 900s = 15 minutes)
        """
        self.env = env
        self.network = network
        self.passenger_threshold = passenger_threshold
        self.mission_profile = mission_profile
        self.max_wait_time = max_wait_time
        self.run_mode = run_mode

    def make_dispatch_decision(self):
        """
        Static Policy based dispatch decision
        """
        """Checks demand at each vertiport and dispatches aircrafts based on static policy."""
        for vertiport in self.network.vertiports.values():
            demand_summary = vertiport.check_demand()

            for destination, demand_info in demand_summary.items():  # Corrected `.items()`
                passenger_count = demand_info["count"]
                max_wait_time = demand_info["max_wait_time"]
                passengers = demand_info["passengers"]  # List of passengers

                if passenger_count >= self.passenger_threshold or max_wait_time >= self.max_wait_time:
                    if passengers is None:
                        print('debug')
                    self.env.process(self.dispatch_aircraft(vertiport, destination, passengers))

    def dispatch_aircraft(self, vertiport, destination, passengers):
        """Dispatch an aircraft if available."""

        passengers_to_board = min(len(passengers), self.passenger_threshold)  # remove up to 4 or max pax below that
        available_aircraft = vertiport.get_available_aircraft()
        flying_route = self.network.airspaces[vertiport.vertiport_id, destination.vertiport_id]

        skip_flag = False
        aircraft = None

        if available_aircraft:
            aircraft = available_aircraft[0]

        else: # check aircraft that can fly
            if len(vertiport.aircrafts)==0:
                # no aircraft is in the vertiport
                expected_wait_time = self.compute_expected_waiting_time(vertiport, destination)
                skip_flag = True

            else:
                for ac in vertiport.aircrafts:
                    if ac.state == "charge":
                        flight_plan = flying_route.mission_profile[ac.vehicle]
                        total_energy = flight_plan["energy_budget"].sum()*1.3 + (ac.min_soc*ac.battery.capacity/100)
                        soc_requirement = total_energy/ac.battery.capacity

                        if ac.battery.soc >= soc_requirement:
                            aircraft = ac
                            break

                        else:
                            skip_flag = True

        if not skip_flag:
            if aircraft is None:
                print('debug')
            for i in range(passengers_to_board):
                passenger = passengers[i]
                vertiport.remove_passenger(passenger) # Remove from vertiport
                passenger.board_aircraft(aircraft)  # Assign passenger to aircraft
                # aircrafts.current_passengers.append(passenger) # assign passenger to aircrafts redundant

            if not flying_route.can_accommodate(): # air traffic control
                print(f"{self.env.now}: Airspace {(vertiport.vertiport_id, destination.vertiport_id)} full. waiting...")
                wait_time = flying_route.compute_time_until_availability()
                yield self.env.timeout(wait_time)

            print(
                f"{self.env.now}: Aircraft {aircraft.aircraft_id} dispatched from {vertiport.vertiport_id} to {destination.vertiport_id} with {passengers_to_board} passengers.")
            aircraft.flight_ready=False # need to reserve this aircraft since dispatching at the same timestep will cause an error
            self.env.process(aircraft.fly(destination, self.run_mode))

        else:
            print(f"{self.env.now}: No aircraft available at {vertiport.vertiport_id} to {destination.vertiport_id}")

    def compute_expected_waiting_time(self, vertiport, destination):
        """
        :param destination:
        :param vertiport:
        :return: expected waiting time for aircraft to fly from vertiport to destination
        """
        remaining_time = []
        flying_route = self.network.airspaces[vertiport.vertiport_id, destination.vertiport_id]
        airspaces = [asp for vid, asp in self.network.airspaces.items() if vid[1] == vertiport.vertiport_id]

        for airspace in airspaces:
            for ac in airspace.current_aircrafts:
                remaining_flight_time, soc_expectation = ac.get_expected_arrival_time()

                flight_plan = flying_route.mission_profile[ac.vehicle]
                total_energy = flight_plan["energy_budget"].sum() * 1.3 + (ac.min_soc * ac.battery.capacity / 100)
                soc_requirement = total_energy / ac.battery.capacity

                charge_time = vertiport.charger.query_charging_time(initial_soc=soc_expectation, target_soc=soc_requirement)

                remaining_time.append(remaining_flight_time + charge_time)

        return remaining_time


    def connection_mechanism(self):
        """
        handles scenario like NASA - DAVIS
        logic: - first travel transfer station,
        and then, reappear in the transit station with maximum priority.
        :return:
        """
        return 0