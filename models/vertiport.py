from collections import defaultdict

class Vertiport:
    def __init__(self, env, vertiport_id, name, location, network, charger, geometry=None):

        self.env = env
        self.vertiport_id = vertiport_id
        self.name = name
        self.location = location  # (latitude, longitude, altitude)
        self.geometry = geometry  # Placeholder for future use
        self.network = network  # Reference to the UAMNetwork
        self.charger = charger
        self.aircrafts = []  # List of aircraft currently at this vertiport
        self.passengers = [] # List of passengers waiting in the vertiport

        # self.node = # pointer to the network node
        # self.chargers = []  # List of chargers at this vertiport

    def add_passenger(self, passenger):
        """Add a passenger to the vertiport."""
        self.passengers.append(passenger)

    def remove_passenger(self, passenger):
        """Remove a passenger from the vertiport."""
        if passenger in self.passengers:
            self.passengers.remove(passenger)

    def get_available_aircraft(self):
        """Return list of aircraft currently available at this vertiport."""
        return [ac for ac in self.aircrafts if ac.flight_ready]

    def park_aircraft(self, aircraft):
        """Park an aircraft at this vertiport."""
        self.aircrafts.append(aircraft)

    def remove_aircraft(self, aircraft):
        """Dispatch an aircraft from this vertiport."""
        if aircraft in self.aircrafts:
            self.aircrafts.remove(aircraft)

    # def add_charger(self, charger):
    #     """Adds a charger to this vertiport."""
    #     self.chargers.append(charger)

    def check_demand(self):
        """Check if aircrafts should be dispatched based on static policy."""
        demand_summary = {}

        if not self.passengers:
            return demand_summary

        destination_groups = defaultdict(list)

        for passenger in self.passengers:
            destination_groups[passenger.destination].append(passenger)

        for destination, group in destination_groups.items():
            max_wait_time = max(p.wait_time for p in group)  # Find the longest wait time
            demand_summary[destination] = {
                "count": len(group),
                "max_wait_time": max_wait_time,
                "passengers": group  # Directly store the passenger list
            }

        return demand_summary

    def update_passengers(self):
        for passenger in self.passengers:
            passenger.update_wait_time(self.env)

    def update_aircraft_soc(self):
        for aircraft in self.aircrafts:
            if aircraft.state == "charge":
                aircraft.update_soc()

            elif aircraft.battery.soc < 0.99 and aircraft.state == "idle":
                raise Warning(f"{self.env.now}: aircraft {aircraft.aircraft_id} - soc: {aircraft.battery.soc} but state is idle not charge - check charge logic")
