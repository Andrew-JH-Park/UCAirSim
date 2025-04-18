import matplotlib.pyplot as plt
import networkx as nx
import matplotlib.animation as animation
import numpy as np


import contextily as ctx  # For map overlay
import geopandas as gpd  # For coordinate conversion

class LiveVisualizer1:
    def __init__(self, env, network, aircraft_list, update_interval=1000):
        """
        Initializes the live visualization for the UAM network.

        :param env: SimPy environment
        :param network: UAMNetwork instance containing the vertiport network
        :param aircraft_list: List of Aircraft objects
        :param update_interval: Update interval in milliseconds (default: 1000ms = 1 second)
        """
        self.env = env
        self.network = network
        self.aircraft_list = aircraft_list
        self.update_interval = update_interval

        # Initialize Matplotlib figure
        self.fig, self.ax = plt.subplots()
        self.G = self.network.graph  # NetworkX graph of vertiports
        self.pos = nx.get_node_attributes(self.G, 'pos')  # Extract vertiport positions

        # Draw initial network graph
        nx.draw(self.G, self.pos, ax=self.ax, with_labels=True, node_color='blue', edge_color='gray')

        # Initialize aircrafts scatter plot
        self.aircraft_scat = self.ax.scatter([], [], color='red', s=50, label="Aircraft")

        # Animation function
        # self.ani = animation.FuncAnimation(self.fig, self.update, interval=self.update_interval)
        # self.ani = animation.FuncAnimation(self.fig, self.update, interval=self.update_interval)

        self.ani = animation.FuncAnimation(self.fig, self.update, interval=self.update_interval,frames=range(28800, 86400, 10))


    def update(self, frame):

        """Update function for live aircrafts positions."""
        aircraft_positions = [aircraft.position for aircraft in self.aircraft_list if aircraft.state == "flying"]

        if aircraft_positions:
            x_vals, y_vals = zip(*aircraft_positions)
        else:
            x_vals, y_vals = [], []  # No aircrafts in flight

        self.aircraft_scat.set_offsets(np.c_[x_vals, y_vals])
        return self.aircraft_scat,

    def show(self):
        """Run visualization."""
        plt.legend()
        plt.show()


import matplotlib.pyplot as plt
import networkx as nx
import matplotlib.animation as animation
import contextily as ctx  # For map overlay
import numpy as np
import geopandas as gpd  # For coordinate conversion


class LiveVisualizer:
    def __init__(self, env, network, aircraft_list, update_interval=1000):
        """
        Initializes the live visualization with a real-world map overlay.

        :param env: SimPy environment
        :param network: UAMNetwork instance containing the vertiport network
        :param aircraft_list: List of Aircraft objects
        :param update_interval: Update interval in milliseconds (default: 1000ms = 1 second)
        """
        self.env = env
        self.network = network
        self.aircraft_list = aircraft_list
        self.update_interval = update_interval

        # Initialize Matplotlib figure
        self.fig, self.ax = plt.subplots()
        self.G = self.network.graph  # NetworkX graph of vertiports
        self.pos = nx.get_node_attributes(self.G, 'pos')  # Extract vertiport positions

        # Convert positions to a GeoDataFrame (for map projection)
        self.gdf = gpd.GeoDataFrame(geometry=gpd.points_from_xy(
            [p[1] for p in self.pos.values()],  # Longitude
            [p[0] for p in self.pos.values()]  # Latitude
        ), crs="EPSG:4326")  # Define as WGS84 Lat/Lon

        # Convert to Web Mercator (for compatibility with map tiles)
        self.gdf = self.gdf.to_crs(epsg=3857)
        self.pos_mercator = {key: (geom.x, geom.y) for key, geom in zip(self.pos.keys(), self.gdf.geometry)}

        # Adjust zoom level manually (Set bounding box)
        self.ax.set_xlim(self.gdf.total_bounds[0] - 5000, self.gdf.total_bounds[2] + 5000)
        self.ax.set_ylim(self.gdf.total_bounds[1] - 5000, self.gdf.total_bounds[3] + 5000)

        # Add OpenStreetMap tiles as background
        ctx.add_basemap(self.ax, crs=self.gdf.crs, zoom=10, source=ctx.providers.OpenStreetMap.Mapnik)

        # Draw the UAM network over the map
        nx.draw(self.G, self.pos_mercator, ax=self.ax, with_labels=True, node_color='blue', edge_color='gray')

        # Initialize aircrafts scatter plot
        self.aircraft_scat = self.ax.scatter([], [], color='red', s=50, label="Aircraft")

        # Animation function
        self.ani = animation.FuncAnimation(self.fig, self.update, interval=self.update_interval, cache_frame_data=False)

    def update(self, frame):
        """Update function for live aircrafts positions."""
        aircraft_positions = [
            (aircraft.position[1], aircraft.position[0])  # Convert lat/lon to lon/lat for GeoDataFrame
            for aircraft in self.aircraft_list if aircraft.state == "flying"
        ]

        if aircraft_positions:
            gdf_aircraft = gpd.GeoDataFrame(geometry=gpd.points_from_xy(
                [pos[0] for pos in aircraft_positions],  # Longitude
                [pos[1] for pos in aircraft_positions]  # Latitude
            ), crs="EPSG:4326").to_crs(epsg=3857)  # Convert to Web Mercator

            x_vals, y_vals = gdf_aircraft.geometry.x, gdf_aircraft.geometry.y
        else:
            x_vals, y_vals = [], []  # No aircrafts in flight

        self.aircraft_scat.set_offsets(np.c_[x_vals, y_vals])
        return self.aircraft_scat,

    def show(self):
        """Run visualization."""
        plt.legend()
        plt.show()
