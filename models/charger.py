import numpy as np
import pandas as pd
from sympy import Piecewise, var, integrate, symbols, lambdify, re
from scipy.interpolate import interp1d

class ChargerModel:
    def __init__(self, charger_max_charge_rate, charger_efficiency, battery_capacity, elbow_soc=0.3, max_target_soc=0.99, soc_resolution=0.05):
        """
        Charger Model with SoC-dependent charge rate and cumulative charging time trajectory.

        :param charger_max_charge_rate: Max charge rate in kW
        :param charger_efficiency: Efficiency (0-1)
        :param battery_capacity: Battery capacity in kWh
        :param elbow_soc: SoC threshold where linear decrease starts (0-1)
        :param max_target_soc: Maximum SoC limit (practical cap <1)
        :param soc_resolution: Resolution of SoC discretization
        """
        self.charger_max_charge_rate = charger_max_charge_rate
        self.charger_efficiency = charger_efficiency
        self.battery_capacity = battery_capacity
        self.elbow_soc = elbow_soc
        self.max_target_soc = max_target_soc
        self.soc_resolution = soc_resolution

        self.piecewise_soc = self.calc_piecewise_soc_charge_rate_func()
        self.soc_grid, self.time_grid = self.precompute_charging_trajectory()

    def slope_at_soc_charge_rate(self, max_charge_rate):
        return max_charge_rate / (1 - self.elbow_soc)

    def calc_piecewise_soc_charge_rate_func(self):
        var('x')
        max_charge_rate = self.charger_max_charge_rate * self.charger_efficiency
        slope = self.slope_at_soc_charge_rate(max_charge_rate)

        piecewise_soc = Piecewise(
            (max_charge_rate, x <= self.elbow_soc),
            (max_charge_rate - slope * (x - self.elbow_soc), x > self.elbow_soc)
        )
        return piecewise_soc

    def precompute_charging_trajectory(self):
        """
        Precomputes cumulative charging time as a function of SoC.
        """
        print("building charging model...")
        x = symbols('x')
        soc_grid = np.arange(0, self.max_target_soc + self.soc_resolution, self.soc_resolution)
        soc_grid[-1] = self.max_target_soc
        cumulative_time = []
        for target_soc in soc_grid:
            if target_soc == 0:
                cumulative_time.append(0.0)
            else:
                integral = integrate(1 / self.piecewise_soc, (x, 0, target_soc))
                integral_value = integral.evalf()
                integral_value = float(re(integral_value))
                time_sec = integral_value * target_soc * self.battery_capacity * 3600  # in seconds
                cumulative_time.append(time_sec)

        print("\t ... complete")

        return soc_grid, np.array(cumulative_time)

    def query_final_soc(self, initial_soc, charge_time_sec):
        """
        Given initial SoC and charge time, returns final SoC.
        """
        initial_time = np.interp(initial_soc, self.soc_grid, self.time_grid)
        target_time = initial_time + charge_time_sec

        # Find corresponding SoC
        final_soc = np.interp(target_time, self.time_grid, self.soc_grid)
        return float(np.clip(final_soc, 0, self.max_target_soc))

    def query_charging_time(self, initial_soc, target_soc):
        """
        Given initial and target SoC, returns charging time in seconds.
        """
        if target_soc <= initial_soc:
            return 0.0

        initial_time = np.interp(initial_soc, self.soc_grid, self.time_grid)
        target_time = np.interp(target_soc, self.soc_grid, self.time_grid)
        return float(target_time - initial_time)
