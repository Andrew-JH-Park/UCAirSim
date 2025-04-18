import simpy
import pandas as pd
from models.network import UAMNetwork
from models.charger import ChargerModel
from airsim import UAMSimulation
from planning.mission_profile import create_mission_profile

import os
import subprocess
import asyncio
from visualization.python_server.server import WebSocketServer
import webbrowser
import time

REALTIME_FACTOR = 0.1 # seconds per sim second (adjust for desired speed)
SIMULATION_START_TIME = 10#0.1*3600 # start simulation at 5am
RUN_MODE = "fast" # "fast" or "visual"
SIMULATION_UPDATE_INTERVAL = 120
"""
Initialize simulation input
"""
base_dir = os.curdir

network_path = os.path.join(base_dir, 'input/network')
demand_path = os.path.join(base_dir, 'input/demand')
model_specification_path = os.path.join(base_dir, 'input/specifications')

nodes_df = pd.read_csv(os.path.join(network_path,"nodes.csv"))
edges_df = pd.read_csv(os.path.join(network_path,"edges.csv"))
passenger_df = pd.read_csv(os.path.join(demand_path,"Fixed_Passenger_Schedule_BD.csv"))

# Vehicle Input
os.path.join(model_specification_path, 'evtol_spec.csv')

"""
Initialize visualization
"""
visualization_path = os.path.join(base_dir, 'visualization')
server_dir = os.path.join(visualization_path, 'python_server')
client_dir = os.path.join(visualization_path, 'web_client')


# Start WebSocket Server in background
async def run_simulation(simulation, env):
    """Run SimPy simulation asynchronously with artificial delay."""
    print('starting simulation...')
    await asyncio.sleep(2)

    # Advance simulation time to SIMULATION_START_TIME
    print(f"Fast-forwarding to t = {SIMULATION_START_TIME}")
    env.run(until=SIMULATION_START_TIME)

    while env.now <= simulation.end_time:
        # Step simulation by one event
        event = env.step()
        if event == False:
            break

        if RUN_MODE == "visual":
            print(f"Sim time: {env.now}")
            await asyncio.sleep(REALTIME_FACTOR)

async def main():
    # Your usual setup
    # Create mission profile
    mission_profile = create_mission_profile(nodes_df, edges_df, save_result=True)

    # Create tabular model for charging
    charger = ChargerModel(400, 0.9, 160)

    """
    Initialize network and simulation environment
    """
    # Initialize SimPy environment
    env = simpy.Environment()
    network = UAMNetwork(env, nodes_df, edges_df, charger, mission_profile)
    print("network ready")

    # === Start WebSocket server ===
    # === Initialize WebSocket server only for visual mode ===
    ws_server = None
    if RUN_MODE == "visual":
        ws_server = WebSocketServer(simulation=None)


    # === Initialize Simulation ===
    simulation = UAMSimulation(
        env, network, passenger_df, mission_profile,
        update_interval=SIMULATION_UPDATE_INTERVAL, run_mode=RUN_MODE, websocket_server=ws_server
    )
    print("simulation ready")

    if RUN_MODE == "visual":
        ws_server.simulation = simulation  # Link simulation to WebSocket server

        # === Start WebSocket server ===
        server_task = asyncio.create_task(ws_server.run())

        # === Start local HTTP server ===
        http_server = subprocess.Popen(["python", "-m", "http.server", "8080"], cwd=client_dir)
        print("HTTP server started at http://localhost:8080")

        # === Open browser ===
        time.sleep(10)  # small delay to ensure server is ready
        webbrowser.open("http://localhost:8080")

        # === Run simulation ===
        simulation_task = asyncio.create_task(run_simulation(simulation, env))

        await simulation_task

        # Simulation finished → cancel WebSocket server
        server_task.cancel()

        # === After simulation ends ===
        print("Simulation finished. Shutting down... after 5 minutes")
        time.sleep(300)
        http_server.terminate()

    elif RUN_MODE == "fast":
        simulation_task = asyncio.create_task(run_simulation(simulation, env))

        await simulation_task

    else:
        raise ValueError("check RUN_MODE parameter")

if __name__ == "__main__":
    asyncio.run(main())