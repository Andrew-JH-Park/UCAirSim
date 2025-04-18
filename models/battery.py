import numpy as np
import pandas as pd

# charger_max_charge_rate = self.vertiports[self.vertiport_ids[0]].charger_max_charge_rate
# charger_efficiency = self.vertiports[self.vertiport_ids[0]].charger_efficiency
# charger_model = self.set_charger_model(charger_max_charge_rate=charger_max_charge_rate,
#                                        charger_efficiency=charger_efficiency)

class Battery:
    def __init__(self, battery_capacity):
        self.capacity=battery_capacity
        self.soc = 1.0

    def charge_process(self, charger_model):
        """
        Computes the charging process for a given battery size and charger model. Each aircrafts model has its own process
        :param battery_capacity:
        :return:
        """
        increments_size_in_soc = 0.5  # in %
        charge_rate_kw = charger_model.charger_max_charge_rate * charger_model.charger_efficiency
        prev_time = 0
        soc_initial = 0
        soc_final = 100
        total_charge = 0
        time = [prev_time]
        charge_rates = [charge_rate_kw]
        socs = [soc_initial]
        cumulative_energy_kwh = [0]

        for soc in np.arange(soc_initial, soc_final + 1, increments_size_in_soc):
            new_charge_rate_kw = charger_model.calc_charge_rate(charger_model.piecewise_soc, soc)
            average_kw = (charge_rate_kw + new_charge_rate_kw) / 2
            if average_kw == 0:
                break

            charge_increment_kwh = round(increments_size_in_soc / 100 * self.battery_capacity, 4)  # Charge in the interval
            time_increment = round(charge_increment_kwh / average_kw, 4)  # in hours
            current_time = prev_time + time_increment
            total_charge += charge_increment_kwh
            cumulative_energy_kwh.append(total_charge)
            time.append(current_time)
            charge_rates.append(average_kw)
            socs.append(soc)
            prev_time = current_time
            charge_rate_kw = average_kw

        charge_df = pd.DataFrame(data=list(zip(time, charge_rates, socs, cumulative_energy_kwh)),
                                 columns=['time_hr', 'charge_rate', 'soc', 'cumulative_energy_kwh'], dtype=float)
        charge_df['time_sec'] = charge_df['time_hr'] * 3600
        charge_df = charge_df[charge_df.soc <= 100]
        return charge_df

    def expected_charge_time(self, target_soc):
        """
        :param target_soc:
        :return: expected time to charge to target soc
        """
        current_soc = self.soc

    def get_discharge_rate(self):
        current_soc = self.soc
        return 2

    def update_soc_power(self, power_consumption, time):
        """
        soc update under steady state power consumption
        :param power_consumption: steady power consumption in kW
        :param time: operation time in second
        """

        total_energy_consumed = power_consumption*time/3600
        self.soc -= total_energy_consumed/self.capacity

    def update_soc_energy(self, energy_comsumed):
        """
        soc update under steady state power consumption
        :param energy_comsumed: energy consumption in Wh
        :param time: operation time in second
        """
        self.soc -= energy_comsumed/self.capacity