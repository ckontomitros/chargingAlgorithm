class Battery:
    """Base class for battery functionality with charging and discharging capabilities."""

    def __init__(self, battery_capacity, initial_soc, battery_efficiency, dod,
                 max_charge_rate=None, max_discharge_rate=None):
        """
        Initialize battery parameters.

        Args:
            battery_capacity: Battery capacity in kWh
            initial_soc: Initial State of Charge (0-1)
            battery_efficiency: Charging/discharging efficiency (0-1)
            dod: Depth of Discharge (0-1, e.g., 0.8 means max 80% discharge)
            max_charge_rate: Maximum charging power in kW (defaults to battery_capacity)
            max_discharge_rate: Maximum discharging power in kW (defaults to battery_capacity)
        """
        self.battery_capacity = battery_capacity  # kWh
        self.soc = initial_soc  # State of Charge (0-1)
        self.battery_efficiency = battery_efficiency  # 0-1
        self.dod = dod  # Depth of Discharge (0-1)
        
        # Max charge/discharge rates (default to full capacity per hour if not specified)
        self.max_charge_rate = max_charge_rate if max_charge_rate is not None else battery_capacity
        self.max_discharge_rate = max_discharge_rate if max_discharge_rate is not None else battery_capacity
        
        # Minimum SoC based on DoD
        self.soc_min = 1 - dod  # Minimum SoC as fraction (e.g., 0.1 for 90% DoD)

    def charge(self, energy):
        """
        Charge battery using available energy.

        Args:
            energy: Available energy for charging (kWh)

        Returns:
            Energy actually charged (kWh)
        """
        # Current energy in battery
        soc_energy = self.soc * self.battery_capacity

        # Maximum energy that can be charged (limited by charge rate and remaining capacity)
        max_charge = min(self.max_charge_rate, self.battery_capacity - soc_energy)

        # Actual energy charged (accounting for efficiency)
        energy_charged = min(max_charge, energy * self.battery_efficiency)

        # Update SoC
        self.soc = (soc_energy + energy_charged) / self.battery_capacity

        return energy_charged

    def discharge(self, energy):
        """
        Discharge battery to cover energy demand, respecting DoD.

        Args:
            energy: Energy needed (kWh)

        Returns:
            Energy actually discharged (kWh)
        """
        # Current energy in battery
        soc_energy = self.soc * self.battery_capacity

        # Minimum energy to keep (respecting DoD)
        min_energy = self.soc_min * self.battery_capacity

        # Available energy for discharge
        available = max(0, soc_energy - min_energy)

        # Maximum discharge (limited by rate and availability)
        max_discharge = min(self.max_discharge_rate, available)

        # Actual energy discharged
        energy_discharged = min(max_discharge, energy)

        # Update SoC
        self.soc = (soc_energy - energy_discharged) / self.battery_capacity

        return energy_discharged * self.battery_efficiency  # Account for efficiency losses
