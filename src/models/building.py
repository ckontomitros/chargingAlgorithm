import numpy as np
from math import sin, pi


class Building:
    def __init__(self, energy_consumption_profile, panel_area, panel_efficiency, peak_solar_irradiance,
                 battery_capacity, battery_efficiency, initial_soc, dod, duration):
        self.energy_consumption_profile = energy_consumption_profile  # kWh/hour
        self.panel_area = panel_area  # m²
        self.panel_efficiency = panel_efficiency  # 0-1
        self.peak_solar_irradiance = peak_solar_irradiance  # W/m²
        self.battery_capacity = battery_capacity  # kWh
        self.battery_efficiency = battery_efficiency  # Charging/discharging efficiency (0-1)
        self.soc = initial_soc  # State of Charge (0-1)
        self.dod = dod  # Depth of Discharge (0-1, e.g., 0.8 means max 80% discharge)
        self.duration = duration  # Duration for P_max calculation (hours)
        self.renewable_energy_profile = self.generate_renewable_profile()  # Generate PV profile
        self.p_max = self.battery_capacity / self.duration  # Maximum power (kW)
        self.soc_min = self.battery_capacity * (1 - self.dod)  # Minimum SoC (kWh)
        self.v2g_energy = 0  # Track excess V2G energy not stored in battery (reset each hour)

    def generate_renewable_profile(self):
        """Generate renewable energy production profile from photovoltaics (kWh/hour)."""
        profile = [0] * 24  # Initialize 24-hour profile
        for hour in range(24):
            if 6 <= hour <= 18:
                normalized = sin(pi * (hour - 6) / 12)
                irradiance = self.peak_solar_irradiance * normalized  # W/m²
                power_kw = (self.panel_area * irradiance * self.panel_efficiency) / 1000  # kW
                profile[hour] = power_kw  # kWh for the hour
            else:
                profile[hour] = 0  # No production at night
        return profile

    def get_net_energy_demand(self, hour):
        """Calculate net energy demand (consumption - production - V2G energy)."""
        net_demand = (self.energy_consumption_profile[hour % len(self.energy_consumption_profile)] -
                      self.renewable_energy_profile[hour % len(self.renewable_energy_profile)] -
                      self.v2g_energy)
        self.v2g_energy = 0  # Reset V2G energy after use
        return net_demand

    def charge_battery(self, excess_energy):
        """Charge building battery using excess energy."""
        soc_energy = self.soc * self.battery_capacity
        p_ch_t = min(self.p_max, self.battery_capacity - soc_energy)
        energy_charged = min(p_ch_t, excess_energy)
        self.soc = (soc_energy + energy_charged) / self.battery_capacity
        return energy_charged

    def discharge_battery(self, missing_energy):
        """Discharge building battery to cover missing energy, respecting DoD."""
        soc_energy = self.soc * self.battery_capacity
        available_energy = soc_energy - self.soc_min
        p_dis_t = min(self.p_max, available_energy * self.battery_efficiency)
        energy_discharged_after_losses = min(p_dis_t, missing_energy)
        energy_from_battery = energy_discharged_after_losses / self.battery_efficiency
        self.soc = (soc_energy - energy_from_battery) / self.battery_capacity
        return energy_discharged_after_losses

    def receive_v2g_energy(self, energy):
        """Receive energy discharged from EV, store in battery or reduce grid demand."""
        # Try to store in building's battery
        soc_energy = self.soc * self.battery_capacity
        p_ch_t = min(self.p_max, self.battery_capacity - soc_energy)
        energy_to_battery = min(p_ch_t, energy * self.battery_efficiency)
        self.soc = (soc_energy + energy_to_battery) / self.battery_capacity
        # Remaining energy reduces grid demand
        self.v2g_energy = (energy - energy_to_battery / self.battery_efficiency)
        return energy