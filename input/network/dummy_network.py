import networkx as nx
import pandas as pd
import os
from pathlib import Path

workspace_dir = Path(__file__).resolve().parent.parent
network_path = os.path.join(workspace_dir, 'network')
# network_path = os.path.join(os.curdir, 'input/network')

# Define vertiports with their attributes
vertiports = {
    "A": {"lat": 37.7749, "lon": -122.4194, "id": 1, "name": "Vertiport A"},
    "B": {"lat": 37.8715, "lon": -122.2730, "id": 2, "name": "Vertiport B"},
    "C": {"lat": 37.3382, "lon": -121.8863, "id": 3, "name": "Vertiport C"},
    "D": {"lat": 37.7749, "lon": -121.4194, "id": 4, "name": "Vertiport D"}
}

# Define edges with their attributes
edges = [
    ("A", "B", {"ground_distance": 10, "wind_speed": 5.2, "waypoints": "wp_AB"}),
    ("B", "A", {"ground_distance": 10, "wind_speed": 4.9, "waypoints": "wp_BA"}),
    ("B", "C", {"ground_distance": 15, "wind_speed": 4.8, "waypoints": "wp_BC"}),
    ("C", "B", {"ground_distance": 15, "wind_speed": 5.1, "waypoints": "wp_CB"}),
    ("C", "D", {"ground_distance": 20, "wind_speed": 6.0, "waypoints": "wp_CD"}),
    ("D", "C", {"ground_distance": 20, "wind_speed": 5.7, "waypoints": "wp_DC"}),
    ("D", "A", {"ground_distance": 25, "wind_speed": 5.5, "waypoints": "wp_DA"}),
    ("A", "D", {"ground_distance": 25, "wind_speed": 5.3, "waypoints": "wp_AD"})
]

# Create a directed graph
graph = nx.DiGraph()

# Add nodes
graph.add_nodes_from([(v, attr) for v, attr in vertiports.items()])

# Add edges with length attributes
for origin, destination, attr in edges:
    graph.add_edge(origin, destination, **attr)  # Adding edge with attributes

# Convert graph to DataFrame
# nodes_data = [{"id": v, **attr} for v, attr in graph.nodes(data=True)]
nodes_data = [{"id": v, **{k: val for k, val in attr.items() if k != "id"}} for v, attr in graph.nodes(data=True)]
edges_data = [{"origin": u, "destination": v, **attr} for u, v, attr in graph.edges(data=True)]

nodes_df = pd.DataFrame(nodes_data)
edges_df = pd.DataFrame(edges_data)

# Save network data to CSV
nodes_df.to_csv(os.path.join(network_path,"nodes.csv"), index=False)
edges_df.to_csv(os.path.join(network_path,"edges.csv"), index=False)