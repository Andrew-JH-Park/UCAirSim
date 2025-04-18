import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

def generate_passenger_demand(lambda_df: pd.DataFrame):
    """
    Generates passenger demand with precise timestamps within each time interval.

    Parameters:
    - lambda_df: DataFrame containing lambda values for each vertiport at different time intervals.

    Returns:
    - DataFrame of passengers with exact arrival timestamps, origins, destinations, and interarrival times.
    """
    passenger_data = []

    # Iterate over each time interval
    for _, row in lambda_df.iterrows():
        time_slot_str = row["time"]  # Get time in HH:MM format
        base_time = datetime.strptime(time_slot_str, "%H:%M")  # Convert to datetime

        for vertiport in lambda_df.columns[1:]:  # Skip 'time' column
            lambda_val = row[vertiport]

            # Generate number of arrivals using Poisson distribution
            num_arrivals = np.random.poisson(lambda_val)

            if num_arrivals > 0:
                interarrival_times = np.random.exponential(1 / lambda_val, num_arrivals)

                arrival_time = base_time
                for interarrival in interarrival_times:
                    arrival_time += timedelta(seconds=interarrival * 60)

                    passenger_data.append({
                        "arrival_time": arrival_time,
                        "origin": vertiport,
                        "destination": np.random.choice([v for v in lambda_df.columns[1:] if v != vertiport]),
                        "interarrival_time": interarrival
                    })

    # Convert to DataFrame and sort by arrival time
    passenger_df = pd.DataFrame(passenger_data)
    passenger_df.sort_values(by="arrival_time", inplace=True)
    passenger_df.reset_index(drop=True, inplace=True)

    # Assign passenger IDs in sorted order
    passenger_df["passenger_id"] = passenger_df.index

    # Format arrival time as string
    passenger_df["arrival_time"] = passenger_df["arrival_time"].dt.strftime("%H:%M:%S")

    return passenger_df
    #
    # passenger_data = []
    # passenger_id = 0
    #
    # # Iterate over each time interval
    # for _, row in lambda_df.iterrows():
    #     time_slot_str = row["time"]  # Get time in HH:MM format
    #     base_time = datetime.strptime(time_slot_str, "%H:%M")  # Convert to datetime
    #
    #     for vertiport in lambda_df.columns[1:]:  # Skip 'Time' column
    #         lambda_val = row[vertiport]  # Get lambda for this time and vertiport
    #
    #         # Generate number of arrivals using Poisson distribution
    #         num_arrivals = np.random.poisson(lambda_val)
    #
    #         if num_arrivals > 0:
    #             interarrival_times = np.random.exponential(1 / lambda_val, num_arrivals)  # Exponential interarrival
    #
    #             # Convert interarrival times to exact timestamps
    #             arrival_time = base_time  # Start at the base time for the interval
    #             for interarrival in interarrival_times:
    #                 arrival_time += timedelta(seconds=interarrival * 60)  # Convert minutes to seconds
    #
    #                 passenger_data.append({
    #                     "passenger_id": passenger_id,
    #                     "arrival_time": arrival_time.strftime("%H:%M:%S"),  # Exact timestamp
    #                     "origin": vertiport,
    #                     "destination": np.random.choice([v for v in lambda_df.columns[1:] if v != vertiport]),
    #                     "interarrival_time": interarrival
    #                 })
    #                 passenger_id += 1
    #
    # # Convert to DataFrame
    # passenger_df = pd.DataFrame(passenger_data)
    #
    # return passenger_df

def plot_passenger_arrivals(passenger_demand_df: pd.DataFrame, origin: str = None, destination: str = None):
    """
    Plots a histogram of passenger arrivals filtered by origin (departures), destination (arrivals), or both.

    Parameters:
    - passenger_demand_df: DataFrame containing passenger arrivals with timestamps.
    - origin: (Optional) The origin vertiport to filter by (counts departures).
    - destination: (Optional) The destination vertiport to filter by (counts arrivals).

    Returns:
    - A histogram of passenger departures/arrivals over time.
    """
    # Apply filtering based on user selection
    filtered_data = passenger_demand_df.copy()

    if origin and destination:
        filtered_data = filtered_data[(filtered_data["origin"] == origin) & (filtered_data["destination"] == destination)]
        title = f"Departures from {origin} to {destination} (15-min bins)"
    elif origin:
        filtered_data = filtered_data[filtered_data["origin"] == origin]
        title = f"Departures from {origin} to All Destinations (15-min bins)"
    elif destination:
        filtered_data = filtered_data[filtered_data["destination"] == destination]
        title = f"Arrivals at {destination} from All Origins (15-min bins)"
    else:
        title = "Passenger Movements for All O-D Pairs (15-min bins)"

    if filtered_data.empty:
        print("No passenger data found for the selected filters.")
        return

    # Convert arrival_time to datetime for proper plotting
    filtered_data["arrival_time"] = pd.to_datetime(filtered_data["arrival_time"], format="%H:%M:%S")

    # Define time bins for 15-minute intervals
    start_time = datetime.strptime("00:00:00", "%H:%M:%S")
    end_time = datetime.strptime("23:59:59", "%H:%M:%S")
    bin_edges = [start_time + timedelta(minutes=15 * i) for i in range(96)]  # 96 bins for 15-min intervals

    # Plot histogram
    plt.figure(figsize=(12, 6))
    plt.hist(filtered_data["arrival_time"], bins=bin_edges, alpha=0.7, edgecolor="black")

    plt.xlabel("Time of Day")
    plt.ylabel("Number of Passengers")
    plt.title(title)

    # Set x-axis ticks to only show hour marks
    hour_ticks = [start_time + timedelta(hours=h) for h in range(24)]  # Generate datetime hour marks
    hour_labels = [t.strftime("%H:%M") for t in hour_ticks]  # Convert to HH:MM format

    plt.xticks(hour_ticks, hour_labels, rotation=45)
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    plt.show()


lambda_df = pd.read_csv('lambda_matrix.csv')

# Generate passenger demand with exact timestamps
passenger_demand_df = generate_passenger_demand(lambda_df)

passenger_demand_df.to_csv('passenger_schedule.csv', index=False)



# Plot all passengers traveling from Vertiport A to any destination
plot_passenger_arrivals(passenger_demand_df, origin="UCB")

# Plot all passengers traveling to Vertiport B from any origin
plot_passenger_arrivals(passenger_demand_df, destination="UCD")

# Plot all passengers traveling from A to B specifically
plot_passenger_arrivals(passenger_demand_df, origin="UCB", destination="UCD")


# plot_passenger_arrivals(passenger_demand_df, origin="A", destination="B")

