import os.path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from utils.environment_utils import air_density

# file_path = './input/specifications/evtol_spec.csv'
# df = pd.read_csv(file_path)
spec_path = Path(__file__).parents[0]
df = pd.read_csv(os.path.join(spec_path, 'input/specifications/evtol_spec.csv'), index_col=0)

aircraft_params = df['joby_s4_2'].to_dict()

mtom = aircraft_params['mtom'] # MTOM kg (max takeoff weight)
g = 9.81
w = mtom*g
f = aircraft_params['f'] # correction factor for interference from the fuselage, f
dl = aircraft_params['disk_load'] # disk load kg/m2 == mtom/(disk area A)
s = aircraft_params['wing_area'] # wing area 13 m2
b = aircraft_params['wingspan'] # wingspan in m
A = mtom/dl # total disk area m2
fom = aircraft_params['FoM'] # figure of merit
Cd0 = aircraft_params['cd_0'] # zero lift drag coefficient
w_pax = aircraft_params['pax_mass'] # passenger weight kg
Cl_max = aircraft_params['cl_max'] # max lift coefficient
LD_max = aircraft_params['ld_max'] # max lift to drag ratio 15.3~18
LD_min = LD_max*0.866 # LD_max * 0.866
battery_capacity = aircraft_params['battery_capacity'] # battery capacity in kWh
eta_hover = aircraft_params['eta_hover']
eta_climb = aircraft_params['eta_climb']
eta_descent = aircraft_params['eta_descend']
eta_cruise = aircraft_params['eta_cruise']

e_osw = aircraft_params['oswald_efficiency']
aspect_ratio = b**2/s

# Compute induced drag coefficient K
K = 1 / (4 * Cd0 * (LD_max) ** 2)

"""
Cruise performance
Plotting altitude at 500m
"""
alts = [500,1500,2500,4000,5500]
V_air_spd = np.linspace(20, 120, 100) # airspeed range for level-flight performance

colors = plt.cm.viridis(np.linspace(0.3, 0.8, len(alts)))

def compute_V_min_power(alt):
    rho = air_density(alt)

    Cl = w/(.5*rho*V_air_spd**2*s)

    q_air = .5*rho*V_air_spd**2
    Cd_induced = Cl**2/(np.pi*e_osw*aspect_ratio)
    Cd = Cd0 + Cd_induced
    l_d = Cl/Cd

    P_req = (w/l_d)*V_air_spd
    np.max(l_d)

    V_max_ld = V_air_spd[np.argmax(l_d)]  # Velocity at max L/D (min thrust required)
    V_min_power = V_air_spd[np.argmin(P_req)]  # Velocity at min power required

    return V_max_ld, V_min_power, P_req

fig, ax = plt.subplots(figsize=(8, 6))

for idx, (alt, color) in enumerate(zip(alts, colors)):
    V_max_ld, V_min_power, P_req = compute_V_min_power(alt)
    print(f'Speed at LDmax: {V_max_ld:.2f} m/s \nSpeed at Min Power: {V_min_power:.2f} m/s')

    # ax.plot(V_air_spd, P_req*1e-3, color='g', label='Power requirement')
    # ax.axvline(V_max_ld, color='r', linestyle='--', label = 'max L/D air speed')
    # ax.axvline(V_min_power, color='b', linestyle='--', label= 'min Power air speed')

    ax.plot(V_air_spd, P_req * 1e-3, color=color, label=f'Power Req (alt={alt}m)')
    # ax.axvline(V_max_ld, color=color, linestyle='--', label='Max L/D Speed' if idx == 0 else "")
    ax.axvline(V_min_power, color=color, linestyle='--')

    # plt.plot(V_air_spd, Cl, color='k')
    # plt.plot(V_air_spd, Cd, color='b')
    # plt.plot(V_air_spd, l_d, color='r')

ax.set_xlabel('Air Speed (m/s)')
ax.set_ylabel('Power Requirement (kW)')
ax.legend(loc='upper right', fontsize=10, frameon=True)
ax.grid(True, linestyle='--', alpha=0.7)
ax.legend()
fig.show()



rho = air_density(500)

Cl = w / (.5 * rho * V_air_spd ** 2 * s)

q_air = .5 * rho * V_air_spd ** 2
Cd_induced = Cl ** 2 / (np.pi * e_osw * aspect_ratio)
Cd = Cd0 + Cd_induced
l_d = Cl / Cd

P_req = (w / l_d) * V_air_spd
np.max(l_d)

V_max_ld = V_air_spd[np.argmax(l_d)]  # Velocity at max L/D (min thrust required)
V_min_power = V_air_spd[np.argmin(P_req)]  # Velocity at min power required

P_min_power = np.min(P_req)
flight_time = battery_capacity*60*60*1000/P_min_power # second
range = V_min_power*flight_time/1000 *0.65 #km

P_max_ld = P_req[np.argmax(l_d)]
flight_time = battery_capacity*60*60*1000/P_max_ld # second
range = V_max_ld*flight_time/1000 *0.65 #km


estimated_range_min_power = V_min_power*117*60/1000*0.65


"""
Take off and landing power
"""

rho = air_density(500)

# Recalculate Power vs Climb Speed using the provided parameters

# Define climb speed range (V_climb in m/s)
V_climb_range = np.linspace(0, 15, 100)

# Compute power P_fixed-wing for each climb speed using the given equation
P_fixed_wing = ( ( (f * w) / fom ) * np.sqrt( (f * w / A) / (2 * rho) ) + (w * V_climb_range / 2) ) / eta_hover

# Plotting
plt.figure(figsize=(8, 5))
plt.plot(V_climb_range, P_fixed_wing, label=r'$P_{fixed-wing}$', color='b')
plt.xlabel(r'Climb Speed $V_{climb}$ (m/s)')
plt.ylabel(r'Power $P_{fixed-wing}$ (W)')
plt.title('Power vs Climb Speed for Vertical Takeoff (Updated Parameters)')
plt.legend()
plt.grid(True)
plt.show()


"""
Climb Power
input: vertical speed (rate of climb)
Assuming non-accelerating flight
"""
rho = air_density(500)
Vv_range = np.linspace(-10, 10, 16) # range of vertical speed in m/s
Vh_range = np.linspace(10, 100, 40) # range of horizontal speed

Vv, Vh = np.meshgrid(Vv_range, Vh_range)

V_air_spd = np.sqrt(Vv**2 + Vh**2)

P_weight = w*Vv/1000 # power needed to lift the weight with some speed

Cl = w*Vh/((0.5*rho*V_air_spd**3)*s)
Cd_induced = Cl**2/(np.pi*e_osw*aspect_ratio)
D_parasitic = 0.5*rho*(V_air_spd**2)*s*Cd0
D_induced = 0.5*rho*(V_air_spd**2)*s*Cd_induced
Drag = D_parasitic + D_induced
P_req = Drag*V_air_spd/1000

P_climb = P_weight + P_req

# Plot Contour
plt.figure(figsize=(8, 6))
contour = plt.contourf(Vh, Vv, P_climb, levels=50, cmap="viridis")
cbar = plt.colorbar(contour)
cbar.set_label("Climb Power Requirement (kW)")

plt.xlabel("Horizontal Speed Vh (m/s)")
plt.ylabel("Vertical Speed Vv (m/s)")
plt.title("Contour Plot of Climb Power Requirement")
plt.grid(True, linestyle="--", alpha=0.5)
plt.show()

"""
Visualize minimum power and best speed given two way points during climbing
"""
from utils.flight_utils import compute_2d_distance
current_position = (38.415014, -122.118111, 800.0) #(37.87598917647059, -122.24970423529412, 350.0)
next_position = (38.525032, -121.808567, 150.0) #(37.881278, -122.245911, 500)

lat1, lon1, alt1 = current_position
lat2, lon2, alt2 = next_position

dz = alt2 - alt1
d_xy = compute_2d_distance(current_position, next_position)
vh_feasible = np.linspace(10, 100, 200)
vv_feasible = dz * vh_feasible / d_xy  # vv = dz / (d_xy / vh)

vh_feasible = vh_feasible[(vv_feasible >= -10) & (vv_feasible <= 10)]
vv_feasible = vv_feasible[(vv_feasible >= -10) & (vv_feasible <= 10)]

plt.figure(figsize=(10, 6))
contour = plt.contourf(Vh, Vv, P_climb, levels=50, cmap="viridis")
cbar = plt.colorbar(contour)
cbar.set_label("Climb/Descent Power Requirement (kW)")

# optimize over speeds
from scipy.interpolate import RegularGridInterpolator

interpolator = RegularGridInterpolator(
    (Vh_range, Vv_range), P_climb, bounds_error=False, fill_value=np.inf
)

# 4. Stack vh and vv into pairs and query the interpolator
query_points = np.column_stack((vh_feasible, vv_feasible))
power_values = interpolator(query_points)

# 5. Find index of minimum power along the feasible curve
min_idx = np.argmin(power_values)
vh_opt = vh_feasible[min_idx]
vv_opt = vv_feasible[min_idx]
min_power = power_values[min_idx]

# Overlay feasibility curve
plt.plot(vh_feasible, vv_feasible, color='orange', linewidth=2, linestyle="--",label="Feasible Speeds")
plt.plot(vh_opt, vv_opt, marker='*', color='red', markersize=15, label='Optimal Point')
plt.xlabel("Horizontal Speed Vh (m/s)")
plt.ylabel("Vertical Speed Vv (m/s)")
plt.title("Climb/Descent Power Heatmap with Feasible Speed Curve")
plt.legend()
plt.grid(True, linestyle="--", alpha=0.5)
plt.tight_layout()
plt.show()


"""
Vertical Flight
"""

# Compute forward velocity for minimum power consumption using the given equation
V_MinPower = np.sqrt((2 * w) / (rho * A) * np.sqrt(K / (3 * Cd0)))

# Define velocity range (V in m/s)
V_range = np.linspace(5, 100, 80)  # Horizontal speed in m/s
Vv_range = np.linspace(0.1, 15, 40)  # Vertical climb speed in m/s


V, Vv = np.meshgrid(V_range, Vv_range)

# Compute power P_climb using the equation
P_climb_3D = ((w * Vv) +
                   (0.5 * rho * (V**3) * A * Cd0) +
                   ((K * w**2) / (0.5 * rho * V * A))) / eta_climb

# Plot 3D surface
fig = plt.figure(figsize=(10, 7))
ax = fig.add_subplot(111, projection='3d')
ax.plot_surface(V, Vv, P_climb_3D, cmap='viridis', edgecolor='k', alpha=0.8)

# Labels and Title
ax.set_xlabel('Horizontal Speed $V$ (m/s)')
ax.set_ylabel('Climb Speed $V_v$ (m/s)')
ax.set_zlabel('Power $P_{fixed-wing}$ (W)')
ax.set_title('Power vs Horizontal Speed and Climb Speed')

plt.show()


# Create a contour plot of Power vs Horizontal Speed and Climb Speed
fig, ax = plt.subplots(figsize=(8, 6))
contour = ax.contourf(V, Vv, P_climb_3D, cmap='viridis', levels=50)
cbar = plt.colorbar(contour)
cbar.set_label('Power $P_{fixed-wing}$ (W)')

# Add a red dashed vertical line at V_MinPower
ax.axvline(V_MinPower, color='r', linestyle='-', linewidth=1, label=r'$V_{MinPower}$')

# Labels and Title
ax.set_xlabel('Horizontal Speed $V$ (m/s)')
ax.set_ylabel('Climb Speed $V_v$ (m/s)')
ax.set_title('Contour Plot of Power vs Horizontal Speed and Climb Speed')

# Add legend
ax.legend()

plt.show()


"""
Cruise performance
"""
Vv = 0
V_range = np.linspace(5, 100, 100)  # Horizontal speed in m/s
P_cruise = (w*Vv + (w*V_range)/(LD_max))/eta_cruise

# Plotting
plt.figure(figsize=(8, 5))
plt.plot(V_range, P_cruise, label=r'$P_{cruise}$', color='b')
plt.xlabel(r'Cruise Speed $V_{cruise}$ (m/s)')
plt.ylabel(r'Power $P_{cruise}$ (W)')
plt.title('Power vs Forward Speed')
plt.legend()
plt.grid(True)
plt.show()
