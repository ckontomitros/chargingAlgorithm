class Battery:
    """Base class for battery functionality with charging and discharging capabilities."""

    def __init__(self, battery_capacity, initial_soc, battery_efficiency, dod, duration):
        """
        Initialize battery parameters.

        Args:
            battery_capacity: Battery capacity in kWh
            initial_soc: Initial State of Charge (0-1)
            battery_efficiency: Charging/discharging efficiency (0-1)
            dod: Depth of Discharge (0-1, e.g., 0.8 means max 80% discharge)
            duration: Duration for P_max calculation (hours)
        """
        self.battery_capacity = battery_capacity  # kWh
        self.soc = initial_soc  # State of Charge (0-1)
        self.battery_efficiency = battery_efficiency  # 0-1
        self.dod = dod  # Depth of Discharge (0-1)
        self.duration = duration  # Duration for P_max calculation (hours)
        self.p_max = self.battery_capacity / self.duration  # Maximum power (kW)
        self.soc_min = self.battery_capacity * (1 - self.dod)  # Minimum SoC (kWh)

    def charge(self, excess_energy):
        """
        Charge battery using excess energy.

        Args:
            excess_energy: Available energy for charging (kWh)

        Returns:
            Energy actually charged (kWh)
        """
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
        """
        Discharge battery to cover missing energy, respecting DoD.

        Args:
            missing_energy: Energy needed (kWh)

        Returns:
            Energy actually discharged after efficiency losses (kWh)
        """
        # Convert SOC from percentage to energy (kWh)
        soc_energy = self.soc * self.battery_capacity

        # Calculate maximum discharge power (respecting minimum SOC)
        available_energy = soc_energy - self.soc_min
        p_dis_t = min(self.p_max, available_energy * self.battery_efficiency)

        # Calculate actual energy to discharge (limited by missing energy)
        energy_discharged_after_losses = min(p_dis_t, missing_energy)

        # Calculate energy actually taken from battery (before efficiency losses)
        energy_from_battery = energy_discharged_after_losses / self.battery_efficiency

        # Update SOC
        self.soc = (soc_energy - energy_from_battery) / self.battery_capacity

        return energy_discharged_after_losses
