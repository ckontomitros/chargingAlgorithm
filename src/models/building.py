import numpy as np
from math import sin, pi
from .battery import Battery


class Building(Battery):
    def __init__(self, energy_consumption_profile, panel_area, panel_efficiency, peak_solar_irradiance,
                 battery_capacity, battery_efficiency, initial_soc, dod, 
                 max_charge_rate=None, max_discharge_rate=None, irradiance_profile=None):
        # Default charge/discharge rates to battery capacity if not specified
        if max_charge_rate is None:
            max_charge_rate = battery_capacity
        if max_discharge_rate is None:
            max_discharge_rate = battery_capacity
            
        # Initialize Battery base class
        super().__init__(
            battery_capacity=battery_capacity,
            initial_soc=initial_soc,
            battery_efficiency=battery_efficiency,
            dod=dod,
            max_charge_rate=max_charge_rate,
            max_discharge_rate=max_discharge_rate
        )

        # Building-specific attributes
        self.energy_consumption_profile = energy_consumption_profile  # kWh/hour
        self.panel_area = panel_area  # m²
        self.panel_efficiency = panel_efficiency  # 0-1
        self.peak_solar_irradiance = peak_solar_irradiance  # W/m² (used for synthetic profile)
        self.irradiance_profile = irradiance_profile  # Real irradiance data (W/m²) if provided
        self.renewable_energy_profile = self.generate_renewable_profile()  # Generate PV profile
        self.v2g_energy = 0  # Track excess V2G energy not stored in battery (reset each hour)

    def generate_renewable_profile(self):
        """
        Generate renewable energy production profile from photovoltaics (kWh/hour).
        
        If real irradiance data is provided (irradiance_profile), uses that.
        Otherwise, generates synthetic sinusoidal profile using peak_solar_irradiance.
        """
        profile = [0] * 24
        
        if self.irradiance_profile is not None:
            # Use real irradiance data from PVGIS or similar source
            for hour in range(24):
                irradiance = self.irradiance_profile[hour % len(self.irradiance_profile)]  # W/m²
                power_kw = (self.panel_area * irradiance * self.panel_efficiency) / 1000  # kW
                profile[hour] = power_kw  # kWh for the hour
        else:
            # Generate synthetic sinusoidal profile
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
        return self.charge(excess_energy)

    def discharge_battery(self, missing_energy):
        """Discharge building battery to cover missing energy, respecting DoD."""
        return self.discharge(missing_energy)

    def receive_v2g_energy(self, energy):
        """Receive energy discharged from EV, store in battery or reduce grid demand."""
        # Try to store in building's battery
        energy_to_battery = self.charge(energy)
        
        # Remaining energy reduces grid demand
        self.v2g_energy = energy - energy_to_battery
        
        return energy
