import networkx as nx
from models.vertiport import Vertiport
from models.airspace import Airspace
from models.aircraft import Aircraft
from models.charger import ChargerModel
from pathlib import Path
import pandas as pd
import json

INPUT_PATH = Path.cwd() / "input"
SPECIFICATION_PATH = INPUT_PATH / "specifications"
AIRSPACE_PATH = INPUT_PATH / "waypoints"

class UAMNetwork:
    def __init__(self, env, nodes_df, edges_df, charger, mission_profile):
        self.env = env
        self.graph = nx.DiGraph()
        self.vertiports = {}  # Stores Vertiport instances
        self.airspaces = {}  # Stores Airspace instances
        self.aircrafts = {}
        self.initial_aircraft_allocation = {}  # node_id → expected aircraft count
        self.mission_profile = mission_profile
        self.load_network(nodes_df, edges_df, charger)

    def load_network(self, nodes_df, edges_df, charger):
        """Loads the nodes and edges, initializing Vertiport, Aircraft, Airspace instances."""
        # Load aircrafts specification
        df_specification = pd.read_csv(Path.joinpath(SPECIFICATION_PATH, "evtol_spec.csv"), index_col=0)
        dict_specification = df_specification[df_specification.columns[0]].to_dict()

        # Load nodes and initialize Vertiports
        aircraft_num = 1
        for _, row in nodes_df.iterrows():
            vertiport = Vertiport(
                env=self.env,
                vertiport_id=row["id"],
                name=row["name"],
                location=(row["lat"], row["lon"], row["alt"]),
                network=self,
                charger=charger
            )
            self.graph.add_node(row["id"], pos=vertiport.location, vertiport=vertiport)
            self.vertiports[row["id"]] = vertiport

            # initialize aircrafts
            for ac_vehicle, num in json.loads(row["ac_composition"]).items():
                for _ in range(num):
                    aircraft_id = f"AC_{aircraft_num}"
                    specification = df_specification[ac_vehicle]
                    aircraft = Aircraft(env=self.env, vehicle=ac_vehicle, aircraft_id=aircraft_id, network=self, origin_vertiport=vertiport, specification=specification)
                    self.aircrafts[aircraft_id] = aircraft
                    aircraft_num += 1
                    vertiport.park_aircraft(aircraft)

                # save aircraft distribution (for aircraft repositioning)
                self.initial_aircraft_allocation[row["id"]] = num

        # Load edges and initialize Airspaces
        for _, row in edges_df.iterrows():
            attributes = row.drop(["origin", "destination"]).to_dict()
            wp_name = row["waypoints"]
            waypoint_input_file = Path.joinpath(AIRSPACE_PATH, wp_name + ".csv")

            flight_time = list(self.mission_profile[wp_name]['joby_s4_2']['accumulated time'])[-1]

            try:
                waypoints = pd.read_csv(waypoint_input_file)
            except:
                raise Exception(f"waypoint file not found for {row}. Check file exists: {waypoint_input_file}")

            airspace = Airspace(
                origin=row["origin"],
                destination=row["destination"],
                capacity=attributes.get("capacity", 5),  # Default capacity = 5 if not provided
                waypoints=waypoints,
                mission_profile=self.mission_profile[row["waypoints"]]
            )
            self.graph.add_edge(row["origin"], row["destination"], airspace=airspace, flight_time=flight_time,**attributes)
            self.airspaces[(row["origin"], row["destination"])] = airspace

    def update_network(self):
        """Updates network state every 'update_interval' minutes."""
        # print(f"{self.env.now}: Performing network update.")
        for vertiport in self.vertiports.values():
            # vertiport.check_demand()
            vertiport.update_passengers()
            vertiport.update_aircraft_soc()

    def compute_itinerary(self, origin_node, destination_node):
        itinerary = nx.shortest_path(self.graph, source=origin_node, target=destination_node, weight='flight_time')
        return itinerary
