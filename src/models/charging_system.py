import numpy as np


class ChargingSystem:
    def __init__(self, building, ev, grid, desired_soc, target_time, arrival_time):
        self.building = building
        self.ev = ev
        self.grid = grid
        self.desired_soc = desired_soc  # Desired State of Charge (SoC)
        self.target_time = target_time  # Time by which the desired SoC is required
        self.arrival_time = arrival_time  # Time when the vehicle arrives

    def simple_charge(self, hour):
        """Simple algorithm: Charge as soon as possible after arrival until battery is full."""
        if hour < self.arrival_time or self.ev.soc >= self.desired_soc:
            return False, 0  # Do not charge before arrival or if SoC is reached
        energy = self.ev.charge(self.ev.max_charge_rate)
        cost = energy * self.grid.get_price(hour)  # Use price for the given hour
        print(f"Charged {energy:.2f} kWh at hour {hour}, Cost: {cost:.2f} €")
        return True, cost

    def cost_optimized_charge(self, hour):
        """Cost minimization algorithm: Charge during cheapest hours after arrival."""
        if hour < self.arrival_time or self.ev.soc >= self.desired_soc:
            return False, 0  # Do not charge before arrival or if SoC is reached

        energy_needed = (self.desired_soc - self.ev.soc) * self.ev.battery_capacity
        if energy_needed <= 0:
            return (False, 0)

        # Sort available hours (from arrival_time to target_time) by electricity price
        available_hours = list(range(self.arrival_time, self.target_time))
        hours_sorted = sorted(available_hours, key=lambda h: self.grid.get_price(h))

        # Check if current hour is among the cheapest hours needed to meet energy demand
        hours_needed = []
        total_energy = 0
        for h in hours_sorted:
            if total_energy >= energy_needed:
                break
            total_energy += min(self.ev.max_charge_rate, energy_needed - total_energy)
            hours_needed.append(h)

        if hour not in hours_needed:
            return (False, 0)  # Do not charge in this hour

        # Charge in this hour
        available_energy = max(0, -self.building.get_net_energy_demand(hour))  # Energy from renewables
        energy_to_charge = min(self.ev.max_charge_rate, energy_needed)
        energy_from_grid = max(0, energy_to_charge - available_energy)
        energy_charged = self.ev.charge(energy_to_charge)
        cost = energy_from_grid * self.grid.get_price(hour)  # Cost only for grid energy
        print(f"Charged {energy_charged:.2f} kWh at hour {hour}, Cost: {cost:.2f} €")
        return (True, cost)

    def rl_charge(self, hour, episodes=1000, learning_rate=0.1, discount_factor=0.9):
        """Reinforcement Learning algorithm: Decide to charge in the given hour."""
        if hour < self.arrival_time or self.ev.soc >= self.desired_soc:
            return (False, 0)  # Do not charge before arrival or if SoC is reached

        # Initialize Q-table
        states = [(soc, h) for soc in np.arange(0, 1.01, 0.1) for h in range(self.arrival_time, self.target_time)]
        actions = ['charge', 'standby']  # Only charge and standby actions
        Q = np.zeros((len(states), len(actions)))  # Q-table

        # Training loop using a simulated SoC
        initial_soc = self.ev.soc  # Store initial SoC
        for _ in range(episodes):
            current_soc = initial_soc  # Reset to initial SoC for each episode
            for h in range(self.arrival_time, self.target_time):
                state_idx = min(range(len(states)),
                                key=lambda i: abs(states[i][0] - current_soc) + abs(states[i][1] - h))

                # Action selection with exploration
                if np.random.rand() < 0.1:  # Exploration
                    action = np.random.choice(actions)
                else:  # Exploitation
                    action = actions[np.argmax(Q[state_idx])]

                # Simulate action without modifying actual EV
                reward = 0
                if action == 'charge':
                    available_energy = max(0, -self.building.get_net_energy_demand(h))  # Energy from renewables
                    # Simulate charging: calculate energy charged without calling self.ev.charge()
                    energy = min(self.ev.max_charge_rate, (1.0 - current_soc) * self.ev.battery_capacity)
                    energy_from_grid = max(0, energy - available_energy)
                    reward = -energy_from_grid * self.grid.get_price(h) + energy
                    current_soc += energy / self.ev.battery_capacity  # Update simulated SoC
                else:  # standby
                    reward = 0

                # Penalty if desired SoC is not achieved by target time
                if h == self.target_time - 1 and current_soc < self.desired_soc:
                    reward -= 100

                # Update Q-table
                next_state_idx = min(range(len(states)),
                                     key=lambda i: abs(states[i][0] - current_soc) + abs(
                                         states[i][1] - min(h + 1, self.target_time - 1)))
                Q[state_idx, actions.index(action)] += learning_rate * (
                        reward + discount_factor * np.max(Q[next_state_idx]) - Q[state_idx, actions.index(action)]
                )

        # Decide action for the current hour using actual EV state
        state_idx = min(range(len(states)),
                        key=lambda i: abs(states[i][0] - self.ev.soc) + abs(states[i][1] - hour))
        action = actions[np.argmax(Q[state_idx])]

        if action != 'charge':
            return (False, 0)

        # Execute charging on the actual EV
        available_energy = max(0, -self.building.get_net_energy_demand(hour))  # Energy from renewables
        energy = self.ev.charge(self.ev.max_charge_rate)
        energy_from_grid = max(0, energy - available_energy)
        cost = energy_from_grid * self.grid.get_price(hour)
        print(f"Charged {energy:.2f} kWh at hour {hour}, Cost: {cost:.2f} €")
        return (True, cost)