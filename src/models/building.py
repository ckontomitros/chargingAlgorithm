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
        """Calculate net energy demand (consumption - production)."""
        return self.energy_consumption_profile[hour] - self.renewable_energy_profile[hour]

    def charge_battery(self, excess_energy):
        """Charge building battery using excess energy."""
        # Convert SOC from percentage to energy (kWh)
        soc_energy = self.soc * self.battery_capacity

        # Calculate maximum charge power
        p_ch_t = min(self.p_max, self.battery_capacity - soc_energy)

        # Calculate actual energy to charge (limited by available excess energy)
        energy_charged = min(p_ch_t, excess_energy)

        # Update SOC (convert energy back to percentage)
        self.soc = (soc_energy + energy_charged) / self.battery_capacity

        return energy_charged

    def discharge_battery(self, missing_energy):
        """Discharge building battery to cover missing energy, respecting DoD."""
        # Convert SOC from percentage to energy (kWh)
        soc_energy = self.soc * self.battery_capacity

        # Calculate maximum discharge power (respecting minimum SOC)
        available_energy = soc_energy - self.soc_min
        p_dis_t = min(self.p_max, available_energy * self.battery_efficiency)

        # Calculate actual energy to discharge (limited by missing energy)
        # Note: p_dis_t is power, so we need to consider it as energy for 1-hour timestep
        energy_discharged_after_losses = min(p_dis_t, missing_energy)

        # Calculate energy actually taken from battery (before efficiency losses)
        energy_from_battery = energy_discharged_after_losses / self.battery_efficiency

        # Update SOC
        self.soc = (soc_energy - energy_from_battery) / self.battery_capacity

        return energy_discharged_after_losses
