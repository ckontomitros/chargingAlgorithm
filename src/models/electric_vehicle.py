import numpy as np
from math import sin, pi


class ElectricVehicle:
    def __init__(self, battery_capacity, initial_soc, energy_per_km, max_charge_rate, max_discharge_rate, usage_stats,
                 dod, duration, battery_efficiency=0.9):
        self.battery_efficiency = battery_efficiency
        self.battery_capacity = battery_capacity  # kWh
        self.soc = initial_soc  # State of Charge (0-1)
        self.energy_per_km = energy_per_km  # kWh/km
        self.max_charge_rate = max_charge_rate  # kW
        self.max_discharge_rate = max_discharge_rate  # kW (for V2G)
        self.usage_stats = usage_stats  # e.g., {'departure': 8, 'arrival': 18, 'daily_km': 50}
        self.dod = dod  # Depth of Discharge (0-1, e.g., 0.8 means max 80% discharge)
        self.duration = duration  # Duration for P_max calculation (hours)
        self.p_max = self.battery_capacity / self.duration  # Maximum power (kW)
        self.soc_min = self.battery_capacity * (1 - self.dod)  # Minimum SoC (kWh)

    def charge(self, excess_energy):
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

    def discharge(self, missing_energy):
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

    def get_required_energy(self):
        """Calculate energy required for daily usage."""
        return self.usage_stats['daily_km'] * self.energy_per_km
