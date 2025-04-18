import simpy
import pandas as pd
from models.network import UAMNetwork
from models.charger import ChargerModel
from airsim import UAMSimulation
from utils.live_visualization import LiveVisualizer
from planning.mission_profile import create_mission_profile
import os

"""
Initialize simulation input
"""
network_path = os.path.join(os.curdir, 'input/network')
demand_path = os.path.join(os.curdir, 'input/demand')
model_specification_path = os.path.join(os.curdir, 'input/specifications')

nodes_df = pd.read_csv(os.path.join(network_path,"nodes.csv"))
edges_df = pd.read_csv(os.path.join(network_path,"edges.csv"))
passenger_df = pd.read_csv(os.path.join(demand_path,"passenger_schedule.csv"))

# passenger_df = passenger_df.sort_values(by=['arrival_time'])
# Vehicle Input
os.path.join(model_specification_path, 'evtol_spec.csv')

# Create mission profile
mission_profile = create_mission_profile(nodes_df, edges_df, save_result=False)

# Create tabular model for charging
charger = ChargerModel(400, 0.9, 160)

"""
Initialize network and simulation environment
"""
# Initialize SimPy environment
env = simpy.Environment()
network = UAMNetwork(env, nodes_df, edges_df, charger, mission_profile)

print("network ready")

UAMSimulation = UAMSimulation(env, network, passenger_df, mission_profile, update_interval=120, run_mode="fast")

aircraft_list = list(network.aircrafts.values())


import threading
import matplotlib.pyplot as plt
visualizer = LiveVisualizer(env, network, aircraft_list)
# Start visualization in a separate thread
# visualizer_thread = threading.Thread(target=visualizer.show)
# visualizer_thread.start()

# print("Starting UAM Simulation...")
# env.run()
# print("Simulation completed.")


# Run simulation while keeping visualization active
while True:
    try:
        env.step()  # Run one simulation step at a time
        plt.pause(0.1)  # Allow Matplotlib to update
    except simpy.core.EmptySchedule:  # End of simulation
        break

print("Simulation completed.")

plt.show()  # Ensure final visualization stays open

# visualizer.show()


# access elements
# for vertiport in network.vertiports.values():
#     print(vertiport.get_available_aircraft())
#     print(vertiport.get_available_aircraft()[0].speed_horizontal) # accessing aircrafts
#     print(vertiport.get_available_aircraft()[0].origin_vertiport) # recursion back to the origin vertiport
#     print(vertiport.get_available_aircraft()[0].aircraft_id)
#     print(network.aircrafts['AC_16'])
#     print(network.aircrafts[vertiport.get_available_aircraft()[0].aircraft_id])