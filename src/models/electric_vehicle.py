from .battery import Battery


class ElectricVehicle(Battery):
    def __init__(self, battery_capacity, initial_soc, energy_per_km, max_charge_rate, max_discharge_rate, 
                 usage_stats, dod, duration, battery_efficiency=0.95):
        # Initialize Battery base class with charge/discharge rates
        super().__init__(
            battery_capacity=battery_capacity,
            initial_soc=initial_soc,
            battery_efficiency=battery_efficiency,
            dod=dod,
            max_charge_rate=max_charge_rate,
            max_discharge_rate=max_discharge_rate
        )

        # EV-specific attributes
        self.energy_per_km = energy_per_km  # kWh/km
        self.usage_stats = usage_stats  # e.g., {'departure': 8, 'arrival': 18, 'daily_km': 50}
        self.duration = duration  # Simulation duration

    def get_required_energy(self):
        """Calculate energy required for daily usage."""
        if self.usage_stats:
            return self.usage_stats['daily_km'] * self.energy_per_km
        return 0
