from .battery import Battery


class ElectricVehicle(Battery):
    def __init__(self, battery_capacity, initial_soc, energy_per_km, max_charge_rate, max_discharge_rate, usage_stats,
                 dod, duration, battery_efficiency=0.9):
        # Initialize Battery base class
        super().__init__(battery_capacity, initial_soc, battery_efficiency, dod, duration)

        # EV-specific attributes
        self.energy_per_km = energy_per_km  # kWh/km
        self.max_charge_rate = max_charge_rate  # kW
        self.max_discharge_rate = max_discharge_rate  # kW (for V2G)
        self.usage_stats = usage_stats  # e.g., {'departure': 8, 'arrival': 18, 'daily_km': 50}

    def get_required_energy(self):
        """Calculate energy required for daily usage."""
        return self.usage_stats['daily_km'] * self.energy_per_km