import logging

logger = logging.getLogger(__name__)

class Scheduler:
    def __init__(self, env, network, mission_profile, passenger_threshold=4, max_wait_time=600, run_mode="visual"):
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
                        logger.debug(f"[{self.env.now}]: check the dispatch threshold at {vertiport.vertiport_id}. Pax count: {passenger_count}, max wait time: {max_wait_time}")
                    self.env.process(self.dispatch_aircraft(vertiport, destination, passengers))

        self.perform_vehicle_reposition()

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

                    elif ac.state == "idle" and ac.flight_ready == False:
                        # no aircraft available due to reserved aircraft
                        skip_flag = True

        if not skip_flag:
            if aircraft is None:
                logger.debug(f"[{self.env.now}]: {vertiport.vertiport_id} - no aircraft available, skip flag not triggered")
            for i in range(passengers_to_board):
                passenger = passengers[i]
                passenger.board_aircraft(aircraft)

            if not flying_route.can_accommodate(): # air traffic control
                logger.warning(f"[{self.env.now}]: Airspace {(vertiport.vertiport_id, destination.vertiport_id)} full. waiting...")
                wait_time = flying_route.compute_time_until_availability()
                yield self.env.timeout(wait_time)

            logger.info(f"[{self.env.now}]: Aircraft {aircraft.aircraft_id} dispatched from {vertiport.vertiport_id} to {destination.vertiport_id} with {passengers_to_board} passengers.")
            aircraft.reserve_aircraft() # need to reserve this aircraft since dispatching at the same timestep will cause an error
            self.env.process(aircraft.fly(destination, self.run_mode))

        else:
            logger.warning(f"[{self.env.now}]: No aircraft available at {vertiport.vertiport_id} to {destination.vertiport_id}")

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

    def perform_vehicle_reposition(self):
        distribution = self.network.simulation.get_aircraft_distribution_state()
        aircraft_at_node = distribution["aircraft_at_node"]
        aircraft_inbound_to_node = distribution["aircraft_inbound_to_node"]
        initial_alloc = self.network.initial_aircraft_allocation
        buffer = 0.4  # Tolerance: allows ±1 imbalance before rebalancing
        supply_buffer = 0.7 # if neighboring airport is above 70% support worst supply vertiport by repositioning

        reposition_targets = {}  # node_id → imbalance
        node_supply = {}  # node_id → total aircraft (at + inbound)

        for node_id in self.network.vertiports:
            current = aircraft_at_node.get(node_id, 0) + aircraft_inbound_to_node.get(node_id, 0)
            node_supply[node_id] = current
            target = initial_alloc.get(node_id, 0)

            # deficit case
            if current <= round(target*buffer):
                reposition_targets[node_id] = current - target

        # Step 2: Rank surplus nodes by (actual supply - target), descending
        surplus_candidates = {
            node_id: node_supply[node_id] - initial_alloc.get(node_id, 0)
            for node_id in self.network.vertiports
            if node_id not in reposition_targets and node_supply[node_id] > initial_alloc.get(node_id, 0)
        }

        surplus_nodes = sorted(surplus_candidates.items(), key=lambda x: x[1], reverse=True)  # most surplus first
        deficit_nodes = sorted(reposition_targets.items(), key=lambda x: x[1])  # most negative = worst deficit


        """TODO: 
        1) add a demand-based re-balance requirement
        2) rather than rebalancing from a deficit node, 
            rebalance based on forecasted demand,
            also rebalance based on energy cost repositioning on the edge 
        """

        for dst_id, _ in deficit_nodes:
            dst_vp = self.network.vertiports[dst_id]
            target_dst = initial_alloc.get(dst_id, 0)

            inbound_neighbors = [
                src_id for src_id in self.network.graph.predecessors(dst_id)
                if src_id in self.network.vertiports
            ]

            best_source = None
            best_score = -float("inf")

            for src_id in inbound_neighbors:
                src_vp = self.network.vertiports[src_id]
                src_supply = node_supply.get(src_id, 0)
                src_target = initial_alloc.get(src_id, 0)

                if src_supply <= round(supply_buffer*src_target):
                    continue

                else:
                    score = src_supply - src_target
                    available_ac = src_vp.get_available_aircraft()

                    if not available_ac:
                        continue

                    if score > best_score:
                        best_score = score
                        best_source = (src_id, src_vp, available_ac[0])

            if best_source:
                src_id, src_vp, aircraft = best_source
                aircraft.reserve_aircraft()
                self.env.process(aircraft.fly(dst_vp, self.run_mode))

                logger.info(f"[{self.env.now}] Rebalancing aircraft {aircraft.aircraft_id} from {src_id} → {dst_id} "
                            f"(src surplus: {node_supply[src_id] - initial_alloc[src_id]}, dst current: {node_supply[dst_id]})")