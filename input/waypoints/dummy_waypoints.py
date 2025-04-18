import pandas as pd
import os
from pathlib import Path

#network_path = os.path.join(os.getcwd(), "input/network")
workspace_dir = Path(__file__).resolve().parent.parent
network_path = os.path.join(workspace_dir, 'network')
waypoint_path = os.path.join(workspace_dir, 'waypoints')

edges_df = pd.read_csv(os.path.join(network_path, 'edges.csv'))
nodes_df = pd.read_csv(os.path.join(network_path, 'nodes.csv'))


# Adjusting node dictionary keys to match edge data
node_dict = {
    "A": (37.7749, -122.4194),  # Vertiport A
    "B": (37.8715, -122.2730),  # Vertiport B
    "C": (37.3382, -121.8863),  # Vertiport C
    "D": (37.7749, -121.4194)  # Vertiport D
}


# Re-run function with manually mapped node dictionary
def generate_waypoints_fixed(edge, node_df):
    waypoints_list = []

    origin, dest = edge["origin"], edge["destination"]

    # Get node coordinates
    lat1 = nodes_df[nodes_df["id"] == origin]["lat"].iloc[0]
    lon1 = nodes_df[nodes_df["id"] == origin]["lon"].iloc[0]
    lat2 = nodes_df[nodes_df["id"] == dest]["lat"].iloc[0]
    lon2 = nodes_df[nodes_df["id"] == dest]["lon"].iloc[0]

    # Calculate interpolated waypoints
    lat_wp1, lon_wp1 = lat1, lon1  # Start at origin
    lat_wp5, lon_wp5 = lat2, lon2  # End at destination

    lat_wp2 = lat1 + 0.3 * (lat2 - lat1)
    lon_wp2 = lon1 + 0.3 * (lon2 - lon1)

    lat_wp3 = lat1 + 0.7 * (lat2 - lat1)
    lon_wp3 = lon1 + 0.7 * (lon2 - lon1)

    lat_wp4, lon_wp4 = lat2, lon2  # Close to the destination

    # Define altitude levels
    altitude_wp1 = 60  # Hover climb
    altitude_wp2 = 450  # Cruise altitude (30% traverse)
    altitude_wp3 = 450  # Cruise altitude (70% traverse)
    altitude_wp4 = 60  # Hover descent
    altitude_wp5 = 0  # Landing

    # Store waypoints in list
    waypoints_list.append([origin, dest, lat_wp1, lon_wp1, altitude_wp1, "wp1"])
    waypoints_list.append([origin, dest, lat_wp2, lon_wp2, altitude_wp2, "wp2"])
    waypoints_list.append([origin, dest, lat_wp3, lon_wp3, altitude_wp3, "wp3"])
    waypoints_list.append([origin, dest, lat_wp4, lon_wp4, altitude_wp4, "wp4"])
    waypoints_list.append([origin, dest, lat_wp5, lon_wp5, altitude_wp5, "wp5"])

    # Create DataFrame
    columns = ["origin", "destination", "latitude", "longitude", "altitude", "waypoint_id"]
    waypoints_df = pd.DataFrame(waypoints_list, columns=columns)

    return waypoints_df


for _, edge in edges_df.iterrows():
    wp_df = generate_waypoints_fixed(edge, nodes_df)

    save_path = os.path.join(waypoint_path, edge['waypoints']+".csv")
    wp_df.to_csv(save_path, index=False)