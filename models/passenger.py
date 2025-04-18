class Passenger:
    def __init__(self, passenger_id, origin, destination, arrival_time):
        self.passenger_id = passenger_id
        self.origin = origin
        self.destination = destination
        self.arrival_time = arrival_time  # Time the passenger arrives at the vertiport
        self.boarded_aircraft = None
        self.priority = 0  # Default priority, can be updated later
        self.wait_time = 0

    def update_priority(self, env):
        """Updates priority based on waiting time (longer wait = higher priority)."""
        self.priority = env.now - self.arrival_time

    def update_wait_time(self, env):
        self.wait_time = env.now - self.arrival_time

    def board_aircraft(self, aircraft):
        self.boarded_aircraft = aircraft
        self.boarded_aircraft.current_passengers.append(self)
