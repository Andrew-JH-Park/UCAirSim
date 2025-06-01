import simpy
import logging

logger = logging.getLogger(__name__)

class Passenger:
    def __init__(self, env, network, passenger_id, itinerary):
        self.env = env
        self.network = network
        self.passenger_id = passenger_id
        self.itinerary = itinerary
        self.origin = None
        self.destination = None
        self.initial_time = self.env.now # initial arrival time to the vertiport (used to compute the total travel time)
        self.arrival_time = -1  # Time the passenger arrives at the vertiport
        self.boarded_aircraft = None
        self.wait_time = 0
        self.destination_arrival_time_history = []
        self.wait_time_history = []
        self.current_leg_complete = None
        self.journey_process = None
        self.trip_result = None

    def update_wait_time(self, env):
        self.wait_time = env.now - self.arrival_time

    def board_aircraft(self, aircraft):
        self.boarded_aircraft = aircraft
        self.origin.remove_passenger(self) # Remove from vertiport
        self.boarded_aircraft.current_passengers.append(self)
        self.wait_time_history.append(self.wait_time)

    def unboard_aircraft(self):
        self.boarded_aircraft.current_passengers.remove(self)
        self.boarded_aircraft = None

    def journey(self):
        for i in range(1, len(self.itinerary)):
            current_origin = self.itinerary[i - 1]
            next_dest = self.itinerary[i]

            self.current_leg_complete = self.env.event()

            # Request to travel from current to next
            self.origin = self.network.vertiports[current_origin]
            self.destination = self.network.vertiports[next_dest]

            # arrive at vertiport
            self.origin.add_passenger(self)
            self.arrival_time = self.env.now
            self.wait_time = 0 # reset wait time -- increase this if priority is higher

            logger.info(f"[{self.env.now}] Passenger {self.passenger_id} traveling {current_origin} → {next_dest}")

            try:
                yield self.current_leg_complete  # Wait for this trip to complete
                self.destination_arrival_time_history.append(self.env.now)
                logger.info(f"[{self.env.now}] Passenger {self.passenger_id} intermediate point reached : {current_origin} out of {self.itinerary}")
            except simpy.Interrupt as interrupt:
                print(f"[{self.env.now}] Passenger {self.passenger_id} interrupted: {interrupt.cause}")
                break


        logger.info(f"[{self.env.now}] Passenger {self.passenger_id} final destination reached.")
        self.trip_result = self.compute_travel_result()


    def compute_travel_result(self):
        """Returns total wait and travel time for completed journey."""
        # final arrival is time at last destination (last leg index)

        total_travel_time = self.destination_arrival_time_history[-1] - self.initial_time
        total_wait_time = 0

        result_dict = {
            "passenger_id": self.passenger_id,
            "itinerary": self.itinerary,
            "origin": self.itinerary[0]
        }

        for i, (wt, dt) in enumerate(zip(self.wait_time_history, self.destination_arrival_time_history), start=1):
            result_dict[f"wait time at itinerary {i-1}"] = wt
            result_dict[f"itinerary {i}"] = self.itinerary[i]
            result_dict[f"travel time to itinerary {i}"] = dt - self.initial_time
            total_wait_time += wt

        result_dict["total wait time"]= total_wait_time
        result_dict["total travel time"] = total_travel_time

        return result_dict
