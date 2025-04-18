class Airspace:
    def __init__(self, origin, destination, capacity, waypoints, mission_profile):
        self.origin = origin
        self.destination = destination
        self.capacity = capacity  # Max number of aircraft in airspace
        self.current_aircrafts = []  # Aircraft currently flying in this airspace
        self.waypoints = waypoints
        self.mission_profile = mission_profile

    def can_accommodate(self):
        """Returns True if airspace can take another aircraft."""
        return len(self.current_aircrafts) < self.capacity

    def enter_airspace(self, aircraft):
        """Add an aircraft to the airspace if capacity allows."""
        if self.can_accommodate():
            self.current_aircrafts.append(aircraft)
            return True
        return False

    def exit_airspace(self, aircraft):
        """Remove an aircraft from the airspace."""
        if aircraft in self.current_aircrafts:
            self.current_aircrafts.remove(aircraft)

    def compute_time_until_availability(self):
        remaining_time = []
        for ac in self.current_aircrafts:
            remaining_flight_time,_ = ac.get_expected_arrival_time()

            remaining_time.append(remaining_flight_time)

        return min(remaining_time)-20