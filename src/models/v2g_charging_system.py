import numpy as np


class V2GChargingSystem:
    def __init__(self, building, ev, grid, desired_soc, target_time, arrival_time, min_soc=0.2):
        self.building = building
        self.ev = ev
        self.grid = grid
        self.desired_soc = desired_soc  # Desired State of Charge (SoC)
        self.target_time = target_time  # Time by which the desired SoC is required
        self.arrival_time = arrival_time  # Time when the vehicle arrives
        self.min_soc = min_soc  # Minimum SoC to prevent deep discharge

    def simple_charge(self, hour):
        """Simple algorithm: Charge as soon as possible after arrival until battery is full, no V2G."""
        if hour < self.arrival_time or self.ev.soc >= self.desired_soc:
            return False, 0  # Do not charge before arrival or if SoC is reached
        energy = self.ev.charge(self.ev.max_charge_rate)
        cost = energy * self.grid.get_price(hour)  # Use price for the given hour
        print(f"Charged {energy:.2f} kWh at hour {hour}, Cost: {cost:.2f} €")
        return True, cost

    def max_reward_with_choices(self, pos, neg, n, M, T, U, prices):
        """Dynamic programming to maximize reward with hourly prices and choices."""
        # Compute sum bounds
        min_sum = sum(min(neg[i], pos[i]) for i in range(n))
        max_sum = sum(max(neg[i], pos[i]) for i in range(n))
        if M > max_sum or U < min_sum or U < M:
            return "Impossible", []

        OFFSET = -min_sum + 1
        RANGE = max_sum - min_sum + 2
        INF = float('-inf')

        # Initialize DP and choice arrays
        dp = [[INF] * RANGE for _ in range(n + 1)]
        choice = [[None] * RANGE for _ in range(n + 1)]
        dp[0][OFFSET] = 0.0

        # Fill DP table
        for k in range(1, n + 1):
            for s in range(RANGE):
                if dp[k - 1][s] != INF:
                    actual_sum = s - OFFSET

                    # Choose positive (charge)
                    new_sum_pos = actual_sum + pos[k - 1]
                    new_s_pos = int(new_sum_pos + OFFSET)
                    if 0 <= new_s_pos < RANGE and M <= new_sum_pos <= U:
                        new_reward = dp[k - 1][s] - pos[k - 1] * prices[k - 1]  # Cost of grid energy
                        if new_reward > dp[k][new_s_pos]:
                            dp[k][new_s_pos] = new_reward
                            choice[k][new_s_pos] = ("P", s)

                    # Choose negative (discharge)
                    new_sum_neg = actual_sum + neg[k - 1]
                    new_s_neg = int(new_sum_neg + OFFSET)
                    reward_add = -neg[k - 1] * prices[k - 1]  # Revenue from discharged energy
                    if 0 <= new_s_neg < RANGE and M <= new_sum_neg <= U:
                        new_reward = dp[k - 1][s] + reward_add
                        if new_reward > dp[k][new_s_neg]:
                            dp[k][new_s_neg] = new_reward
                            choice[k][new_s_neg] = ("N", s)

        # Find maximum reward
        max_rew = INF
        final_s = -1
        for s in range(RANGE):
            if dp[n][s] != INF and T <= s - OFFSET <= U:
                if dp[n][s] > max_rew:
                    max_rew = dp[n][s]
                    final_s = s

        if max_rew == INF:
            return "Impossible", []

        # Backtrack choices
        choices = []
        k = n
        s = final_s
        while k > 0:
            c, prev_s = choice[k][s]
            choices.append(c)
            s = prev_s
            k -= 1
        choices.reverse()

        return max_rew, choices

    def cost_optimized_charge(self, hour):
        """Cost minimization algorithm using max_reward_with_choices: Charge or discharge to maximize revenue."""
        if hour < self.arrival_time:
            return (False, 0)  # Do not charge/discharge before arrival or if SoC is reached

        energy_needed = (self.desired_soc - self.ev.soc) * self.ev.battery_capacity

        # Define available hours
        n = self.target_time - self.arrival_time
        available_hours = list(range(self.arrival_time, self.target_time))

        # Calculate pos (charge), neg (discharge), prices, and renewables for each hour
        pos = []
        neg = []
        prices = []
        renewables = []
        for h in available_hours:
            # Renewable energy available
            renewable_energy = max(0, -self.building.get_net_energy_demand(h))
            # Charging: energy from grid, accounting for renewables
            energy_to_charge = self.ev.max_charge_rate
            pos.append(energy_to_charge)  # Grid energy needed for charging
            renewables.append(renewable_energy)

            # Discharging: energy discharged (unaffected by renewables)
            energy_to_discharge = min(self.ev.max_discharge_rate, (self.ev.soc - 0.2) * self.ev.battery_capacity)
            neg.append(-energy_to_discharge)  # Negative contribution to SoC

            # Grid price
            prices.append(self.grid.get_price(h))

        # Set constraints
        M = (0.2 - self.ev.soc) * self.ev.battery_capacity  # Minimum energy (SoC >= 20%)
        T = self.desired_soc * self.ev.battery_capacity - self.ev.soc * self.ev.battery_capacity  # Target energy
        U = self.ev.battery_capacity - self.ev.soc * self.ev.battery_capacity  # Maximum energy (SoC <= 100%)

        # Run max_reward_with_choices
        max_rew, choices = self.max_reward_with_choices(pos, neg, n, M, T, U, prices)
        if max_rew == "Impossible":
            return (False, 0)  # No valid sequence found

        # Execute the action for the current hour
        hour_idx = hour - self.arrival_time
        if hour_idx >= len(choices):
            return (False, 0)

        action = choices[hour_idx]
        if action == 'P':  # Charge
            renewable_energy = renewables[hour_idx]
            energy_to_charge = pos[hour_idx] + renewable_energy  # Total energy charged (grid + renewables)
            energy_from_grid = pos[hour_idx]  # Grid energy only
            energy_charged = self.ev.charge(energy_to_charge)
            cost = energy_from_grid * self.grid.get_price(hour)
            print(
                f"Charged {energy_charged:.2f} kWh at hour {hour} (Grid: {energy_from_grid:.2f}, Renewables: {renewable_energy:.2f}), Cost: {cost:.2f} €")
            return (True, cost)
        elif action == 'N':  # Discharge
            energy_to_discharge = -neg[hour_idx]  # Positive energy value
            energy_discharged = self.ev.discharge(energy_to_discharge)
            revenue = energy_discharged * self.grid.get_price(hour)
            print(f"Discharged {energy_discharged:.2f} kWh at hour {hour}, Revenue: {revenue:.2f} €")
            return (True, -revenue)

        return (False, 0)

    def rl_charge(self, hour, episodes=1000, learning_rate=0.1, discount_factor=0.9):
        """Reinforcement Learning algorithm: Decide to charge or discharge in the given hour."""
        if hour < self.arrival_time:
            return False, 0

        # Initialize Q-table
        states = [(soc, h) for soc in np.arange(self.min_soc, 1.01, 0.1)
                  for h in range(self.arrival_time, self.target_time)]
        actions = ['charge', 'discharge', 'standby']
        Q = np.zeros((len(states), len(actions)))

        # Training loop using simulated SoC
        initial_soc = self.ev.soc
        for _ in range(episodes):
            current_soc = initial_soc
            for h in range(self.arrival_time, self.target_time):
                state_idx = min(range(len(states)),
                                key=lambda i: abs(states[i][0] - current_soc) + abs(states[i][1] - h))

                # Action selection
                if np.random.rand() < 0.1:
                    action = np.random.choice(actions)
                else:
                    action = actions[np.argmax(Q[state_idx])]

                # Simulate action
                reward = 0
                if action == 'charge':
                    available_energy = max(0, -self.building.get_net_energy_demand(h))
                    energy = min(self.ev.max_charge_rate, (1.0 - current_soc) * self.ev.battery_capacity)
                    energy_from_grid = max(0, energy - available_energy)
                    reward = -energy_from_grid * self.grid.get_price(h)
                    current_soc += energy / self.ev.battery_capacity
                elif action == 'discharge' and current_soc > self.min_soc:
                    energy = min(self.ev.max_charge_rate,
                                 (current_soc - self.min_soc) * self.ev.battery_capacity)
                    reward = energy * self.grid.get_sell_price(h)
                    current_soc -= energy / self.ev.battery_capacity
                else:  # standby
                    reward = 0

                # Penalty for not meeting desired SoC or going below min_soc
                if h == self.target_time - 1 and current_soc < self.desired_soc:
                    reward -= 10000000 * (self.desired_soc - current_soc)
                if current_soc < self.min_soc:
                    reward -= 50

                # Update Q-table
                next_state_idx = min(range(len(states)),
                                     key=lambda i: abs(states[i][0] - current_soc) + abs(
                                         states[i][1] - min(h + 1, self.target_time - 1)))
                Q[state_idx, actions.index(action)] += learning_rate * (
                        reward + discount_factor * np.max(Q[next_state_idx]) - Q[state_idx, actions.index(action)]
                )

        # Decide action for current hour
        state_idx = min(range(len(states)),
                        key=lambda i: abs(states[i][0] - self.ev.soc) + abs(states[i][1] - hour))
        action = actions[np.argmax(Q[state_idx])]

        if action == 'standby':
            return False, 0
        elif action == 'charge':
            available_energy = max(0, -self.building.get_net_energy_demand(hour))
            energy = self.ev.charge(self.ev.max_charge_rate)
            energy_from_grid = max(0, energy - available_energy)
            cost = energy_from_grid * self.grid.get_price(hour)
            print(f"Charged {energy:.2f} kWh at hour {hour}, Cost: {cost:.2f} €")
            return True, cost
        else:  # discharge
            if self.ev.soc <= self.min_soc:
                return False, 0
            energy = self.ev.discharge(self.ev.max_charge_rate)
            self.building.receive_v2g_energy(energy)  # Pass discharged energy to building
            benefit = energy * self.grid.get_sell_price(hour)
            print(f"Discharged {energy:.2f} kWh at hour {hour}, Benefit: {benefit:.2f} €")
            return True, -benefit
