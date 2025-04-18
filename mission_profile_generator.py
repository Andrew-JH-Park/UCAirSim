import pandas as pd
import os
from planning.mission_profile import create_mission_profile

network_path = os.path.join(os.curdir, 'input/network')
waypoint_path = os.path.join(os.curdir, 'input/waypoints')

nodes_df = pd.read_csv(os.path.join(network_path,"nodes.csv"))
edges_df = pd.read_csv(os.path.join(network_path,"edges.csv"))

create_mission_profile(nodes_df, edges_df)
