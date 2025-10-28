import numpy as np
from collections import defaultdict

class MultiEVChargingSystem:
    def __init__(self, building, evs, grid, grid_capacity_per_hour, min_soc=0.2):
        """
        Initialize multi-EV charging system (charge-only, no V2G).

        Args:
            building: Building object
            evs: List of dictionaries, each containing:
                - 'ev': EV object
                - 'desired_soc': Target SoC
                - 'target_time': Time by which desired SoC is needed
                - 'arrival_time': Time when vehicle arrives
            grid: Grid object
            grid_capacity_per_hour: Dict mapping hour -> max grid power (kW)
            min_soc: Minimum SoC to prevent deep discharge
        """
        self.building = building
        self.evs = evs
        self.grid = grid
        self.grid_capacity_per_hour = grid_capacity_per_hour
        self.min_soc = min_soc

        # Track grid usage per hour
        self.grid_usage = defaultdict(float)

    def simple_charge_multi(self, hour):
        """Simple algorithm for multiple EVs: Charge available EVs respecting grid constraints."""
        total_cost = 0
        charged_evs = []
        available_grid_capacity = self.grid_capacity_per_hour.get(hour, float('inf')) - self.grid_usage[hour]

        for i, ev_config in enumerate(self.evs):
            ev = ev_config['ev']
            arrival_time = ev_config['arrival_time']
            target_time = ev_config['target_time']
            desired_soc = ev_config['desired_soc']

            # Skip if not arrived, already charged, or departed
            if hour < arrival_time or hour >= target_time or ev.soc >= desired_soc:
                continue

            # Calculate energy needed
            energy_needed = min(ev.max_charge_rate,
                                (desired_soc - ev.soc) * ev.battery_capacity)

            # Check grid capacity
            if energy_needed <= available_grid_capacity:
                energy = ev.charge(energy_needed)
                cost = energy * self.grid.get_price(hour)
                total_cost += cost
                self.grid_usage[hour] += energy
                available_grid_capacity -= energy
                charged_evs.append(i)
                print(f"EV {i}: Charged {energy:.2f} kWh at hour {hour}, Cost: {cost:.2f} €")

        return len(charged_evs) > 0, total_cost * -1  # Return negative cost as benefit

    def rl_charge_multi(self, hour, episodes=2000, learning_rate=0.1,
                        discount_factor=0.95, epsilon=0.15):
        """
        Multi-agent RL algorithm for multiple EVs with grid constraints (charge-only).
        Uses centralized learning with decentralized execution.
        """
        if not any(ev_cfg['arrival_time'] <= hour < ev_cfg['target_time']
                   for ev_cfg in self.evs):
            return False, 0

        # Discretize SoC states
        soc_bins = np.arange(self.min_soc, 1.01, 0.1)
        actions = ['charge', 'standby']  # Only charging and standby

        # Create state space: (ev_id, soc_bin, hour, grid_available)
        grid_bins = [0, 0.25, 0.5, 0.75, 1.0]  # Fraction of capacity available

        # Initialize Q-table as nested dictionary for sparse representation
        Q = defaultdict(lambda: np.zeros(len(actions)))

        # Training phase
        for episode in range(episodes):
            # Reset EVs to initial states
            ev_states = []
            for ev_config in self.evs:
                ev_states.append({
                    'soc': ev_config['ev'].soc,
                    'arrival': ev_config['arrival_time'],
                    'target': ev_config['target_time'],
                    'desired_soc': ev_config['desired_soc'],
                    'battery_cap': ev_config['ev'].battery_capacity,
                    'max_rate': ev_config['ev'].max_charge_rate
                })

            episode_grid_usage = defaultdict(float)

            # Simulate from earliest arrival to latest target
            min_hour = min(ev_cfg['arrival_time'] for ev_cfg in self.evs)
            max_hour = max(ev_cfg['target_time'] for ev_cfg in self.evs)

            for h in range(min_hour, max_hour):
                available_capacity = self.grid_capacity_per_hour.get(h, float('inf'))
                remaining_capacity = available_capacity - episode_grid_usage[h]

                # Process each EV
                for ev_id, ev_state in enumerate(ev_states):
                    if h < ev_state['arrival'] or h >= ev_state['target']:
                        continue

                    # Discretize state
                    soc_bin = min(len(soc_bins) - 1,
                                  max(0, int((ev_state['soc'] - self.min_soc) / 0.1)))
                    grid_bin = min(4, int(5 * remaining_capacity / available_capacity)) \
                        if available_capacity > 0 else 0

                    state = (ev_id, soc_bin, h, grid_bin)

                    # Epsilon-greedy action selection
                    if np.random.rand() < epsilon:
                        action_idx = np.random.randint(len(actions))
                    else:
                        action_idx = np.argmax(Q[state])

                    action = actions[action_idx]

                    # Simulate action
                    reward = 0

                    if action == 'charge' and remaining_capacity > 0:
                        # Calculate available building energy
                        building_energy = max(0, -self.building.get_net_energy_demand(h))

                        # Energy to charge
                        max_energy = min(
                            ev_state['max_rate'],
                            (1.0 - ev_state['soc']) * ev_state['battery_cap'],
                            remaining_capacity
                        )

                        if max_energy > 0:
                            energy_from_building = min(building_energy, max_energy)
                            energy_from_grid = max_energy - energy_from_building

                            # Cost for grid energy only
                            reward = -energy_from_grid * self.grid.get_price(h)

                            # Update state
                            ev_state['soc'] += max_energy / ev_state['battery_cap']
                            episode_grid_usage[h] += energy_from_grid
                            remaining_capacity -= energy_from_grid

                    # Penalties and bonuses
                    if ev_state['soc'] < self.min_soc:
                        reward -= 1000

                    if ev_state['soc'] > 1.0:
                        reward -= 500

                    # Strong penalty if target not met at deadline
                    if h == ev_state['target'] - 1:
                        if ev_state['soc'] < ev_state['desired_soc']:
                            shortfall = ev_state['desired_soc'] - ev_state['soc']
                            reward -= 10000 * shortfall
                        else:
                            reward += 50  # Bonus for meeting target

                    # Update Q-value
                    next_soc_bin = min(len(soc_bins) - 1,
                                       max(0, int((ev_state['soc'] - self.min_soc) / 0.1)))
                    next_grid_bin = min(4, int(5 * remaining_capacity / available_capacity)) \
                        if available_capacity > 0 else 0
                    next_state = (ev_id, next_soc_bin, min(h + 1, max_hour - 1), next_grid_bin)

                    best_next_q = np.max(Q[next_state])
                    Q[state][action_idx] += learning_rate * (
                            reward + discount_factor * best_next_q - Q[state][action_idx]
                    )

        # Execution phase: Make decisions for current hour
        total_benefit = 0
        actions_taken = []
        available_capacity = self.grid_capacity_per_hour.get(hour, float('inf'))
        remaining_capacity = available_capacity - self.grid_usage[hour]

        for ev_id, ev_config in enumerate(self.evs):
            ev = ev_config['ev']
            arrival_time = ev_config['arrival_time']
            target_time = ev_config['target_time']
            desired_soc = ev_config['desired_soc']

            if hour < arrival_time or hour >= target_time:
                continue

            # Get current state
            soc_bin = min(len(soc_bins) - 1,
                          max(0, int((ev.soc - self.min_soc) / 0.1)))
            grid_bin = min(4, int(5 * remaining_capacity / available_capacity)) \
                if available_capacity > 0 else 0
            state = (ev_id, soc_bin, hour, grid_bin)

            # Choose best action
            action_idx = np.argmax(Q[state])
            action = actions[action_idx]

            if action == 'standby':
                continue

            elif action == 'charge' and remaining_capacity > 0:
                building_energy = max(0, -self.building.get_net_energy_demand(hour))
                max_energy = min(
                    ev.max_charge_rate,
                    (1.0 - ev.soc) * ev.battery_capacity,
                    remaining_capacity
                )

                if max_energy > 0:
                    energy = ev.charge(max_energy)
                    energy_from_building = min(building_energy, energy)
                    energy_from_grid = energy - energy_from_building

                    cost = energy_from_grid * self.grid.get_price(hour)
                    total_benefit -= cost
                    self.grid_usage[hour] += energy_from_grid
                    remaining_capacity -= energy_from_grid

                    actions_taken.append(f"EV {ev_id}: Charged {energy:.2f} kWh "
                                         f"({energy_from_grid:.2f} from grid), Cost: {cost:.2f} €")

        # Print actions
        for action_msg in actions_taken:
            print(action_msg)

        return len(actions_taken) > 0, total_benefit

    def milp_charge(self, current_hour):
        """
        Mixed Integer Linear Programming approach for optimal charging schedule (charge-only).
        Requires pulp library: pip install pulp
        """
        try:
            from pulp import LpMinimize, LpProblem, LpVariable, lpSum, LpStatus, value
        except ImportError:
            print("PuLP library required. Install with: pip install pulp")
            return False, 0

        # Define time horizon
        min_hour = min(ev_cfg['arrival_time'] for ev_cfg in self.evs)
        max_hour = max(ev_cfg['target_time'] for ev_cfg in self.evs)
        hours = range(min_hour, max_hour)

        # Create optimization problem
        prob = LpProblem("Multi_EV_Charging_Optimization", LpMinimize)

        # Decision variables (only charging, no discharge)
        charge = {}  # charge[ev_id, h] = energy charged at hour h
        soc = {}  # soc[ev_id, h] = state of charge at hour h
        grid_energy = {}  # grid_energy[ev_id, h] = energy from grid

        for ev_id, ev_cfg in enumerate(self.evs):
            ev = ev_cfg['ev']
            for h in hours:
                charge[ev_id, h] = LpVariable(f"charge_{ev_id}_{h}", 0, ev.max_charge_rate)
                soc[ev_id, h] = LpVariable(f"soc_{ev_id}_{h}", self.min_soc, 1.0)
                grid_energy[ev_id, h] = LpVariable(f"grid_{ev_id}_{h}", 0, ev.max_charge_rate)

        # Objective: Minimize total cost (only grid purchases)
        total_cost = []
        for ev_id, ev_cfg in enumerate(self.evs):
            for h in hours:
                # Cost of grid energy
                total_cost.append(grid_energy[ev_id, h] * self.grid.get_price(h))

        prob += lpSum(total_cost)

        # Constraints
        for ev_id, ev_cfg in enumerate(self.evs):
            ev = ev_cfg['ev']
            arrival = ev_cfg['arrival_time']
            target = ev_cfg['target_time']
            desired_soc = ev_cfg['desired_soc']

            for h in hours:
                # No charging before arrival or after target
                if h < arrival or h >= target:
                    prob += charge[ev_id, h] == 0

                # SoC dynamics
                if h == arrival:
                    # Initial SoC
                    prob += soc[ev_id, h] == ev.soc + charge[ev_id, h] / ev.battery_capacity
                elif h > arrival and h < target:
                    # SoC evolution
                    prob += soc[ev_id, h] == soc[ev_id, h - 1] + charge[ev_id, h] / ev.battery_capacity

                # Grid energy constraint (charge from building first)
                building_energy = max(0, -self.building.get_net_energy_demand(h))
                prob += grid_energy[ev_id, h] >= charge[ev_id, h] - building_energy
                prob += grid_energy[ev_id, h] <= charge[ev_id, h]

            # Final SoC constraint
            if target - 1 >= arrival:
                prob += soc[ev_id, target - 1] >= desired_soc

        # Grid capacity constraint (total grid energy per hour)
        for h in hours:
            total_grid = lpSum([grid_energy[ev_id, h] for ev_id in range(len(self.evs))])
            prob += total_grid <= self.grid_capacity_per_hour.get(h, float('inf'))

        # Solve
        prob.solve()

        if LpStatus[prob.status] != 'Optimal':
            print(f"MILP: No optimal solution found. Status: {LpStatus[prob.status]}")
            return False, 0

        # Execute decisions for current hour
        total_benefit = 0
        actions_taken = []

        for ev_id, ev_cfg in enumerate(self.evs):
            ev = ev_cfg['ev']

            if current_hour < ev_cfg['arrival_time'] or current_hour >= ev_cfg['target_time']:
                continue

            charge_amount = value(charge[ev_id, current_hour])

            if charge_amount and charge_amount > 0.01:
                energy = ev.charge(charge_amount)
                building_energy = max(0, -self.building.get_net_energy_demand(current_hour))
                energy_from_grid = max(0, energy - building_energy)
                cost = energy_from_grid * self.grid.get_price(current_hour)
                total_benefit -= cost
                self.grid_usage[current_hour] += energy_from_grid
                actions_taken.append(f"EV {ev_id}: Charged {energy:.2f} kWh, Cost: {cost:.2f} €")

        for action in actions_taken:
            print(action)

        return len(actions_taken) > 0, total_benefit

    def mpc_charge(self, current_hour, horizon=6, iterations=50):
        """
        Model Predictive Control for multi-EV charging (charge-only).
        Optimizes over a receding horizon using gradient descent.
        """
        min_hour = min(ev_cfg['arrival_time'] for ev_cfg in self.evs)
        max_hour = max(ev_cfg['target_time'] for ev_cfg in self.evs)

        if current_hour >= max_hour:
            return False, 0

        # Define prediction horizon
        horizon_end = min(current_hour + horizon, max_hour)
        prediction_hours = range(current_hour, horizon_end)

        # Initialize control variables (only charge rates, no discharge)
        n_evs = len(self.evs)
        n_hours = len(prediction_hours)

        # Control vector: charge_rates for all EVs and hours
        controls = np.random.rand(n_evs * n_hours) * 0.5

        best_controls = controls.copy()
        best_cost = float('inf')

        # Gradient descent optimization
        for iteration in range(iterations):
            # Evaluate cost
            total_cost = 0
            penalty = 0

            # Simulate forward
            ev_socs = [ev_cfg['ev'].soc for ev_cfg in self.evs]
            hour_grid_usage = {h: self.grid_usage[h] for h in prediction_hours}

            for t_idx, h in enumerate(prediction_hours):
                available_capacity = self.grid_capacity_per_hour.get(h, float('inf')) - hour_grid_usage[h]
                hour_grid_used = 0

                for ev_id, ev_cfg in enumerate(self.evs):
                    if h < ev_cfg['arrival_time'] or h >= ev_cfg['target_time']:
                        continue

                    ev = ev_cfg['ev']
                    charge_idx = ev_id * n_hours + t_idx

                    charge_rate = np.clip(controls[charge_idx], 0, ev.max_charge_rate)

                    # Charging
                    if charge_rate > 0:
                        energy = min(charge_rate, (1.0 - ev_socs[ev_id]) * ev.battery_capacity)
                        building_energy = max(0, -self.building.get_net_energy_demand(h))
                        energy_from_grid = max(0, min(energy - building_energy, available_capacity - hour_grid_used))

                        total_cost += energy_from_grid * self.grid.get_price(h)
                        ev_socs[ev_id] += energy / ev.battery_capacity
                        hour_grid_used += energy_from_grid

                    # Penalties
                    if ev_socs[ev_id] < self.min_soc:
                        penalty += 1000 * (self.min_soc - ev_socs[ev_id])
                    if ev_socs[ev_id] > 1.0:
                        penalty += 500 * (ev_socs[ev_id] - 1.0)

            # Terminal penalty: not meeting desired SoC
            for ev_id, ev_cfg in enumerate(self.evs):
                if horizon_end >= ev_cfg['target_time'] - 1:
                    shortfall = max(0, ev_cfg['desired_soc'] - ev_socs[ev_id])
                    penalty += 5000 * shortfall

            objective = total_cost + penalty

            # Update best
            if objective < best_cost:
                best_cost = objective
                best_controls = controls.copy()

            # Simple random perturbation for optimization
            perturbation = np.random.randn(len(controls)) * 0.1
            controls = best_controls + perturbation
            controls = np.clip(controls, 0, 10)

        # Execute first step of best control
        controls = best_controls
        total_benefit = 0
        actions_taken = []

        for ev_id, ev_cfg in enumerate(self.evs):
            ev = ev_cfg['ev']

            if current_hour < ev_cfg['arrival_time'] or current_hour >= ev_cfg['target_time']:
                continue

            charge_idx = ev_id * n_hours

            charge_rate = np.clip(controls[charge_idx], 0, ev.max_charge_rate)

            if charge_rate > 0.1:
                energy = ev.charge(charge_rate)
                building_energy = max(0, -self.building.get_net_energy_demand(current_hour))
                energy_from_grid = max(0, energy - building_energy)
                cost = energy_from_grid * self.grid.get_price(current_hour)
                total_benefit -= cost
                self.grid_usage[current_hour] += energy_from_grid
                actions_taken.append(f"EV {ev_id}: Charged {energy:.2f} kWh, Cost: {cost:.2f} €")

        for action in actions_taken:
            print(action)

        return len(actions_taken) > 0, total_benefit

    def pso_charge(self, current_hour, n_particles=30, n_iterations=50, w=0.7, c1=1.5, c2=1.5):
        """
        Particle Swarm Optimization for multi-EV charging schedule (charge-only).
        Optimizes charging decisions over future horizon.
        """
        min_hour = min(ev_cfg['arrival_time'] for ev_cfg in self.evs)
        max_hour = max(ev_cfg['target_time'] for ev_cfg in self.evs)

        if current_hour >= max_hour:
            return False, 0

        # Define optimization horizon
        horizon = min(8, max_hour - current_hour)
        n_evs = len(self.evs)

        # Particle dimension: action for each EV at each hour in horizon
        # Action: continuous value [0, 1] for charge rate (0=no charge, 1=max charge)
        dim = n_evs * horizon

        # Initialize particles (only positive values for charging)
        particles = np.random.uniform(0, 1, (n_particles, dim))
        velocities = np.random.uniform(-0.3, 0.3, (n_particles, dim))

        # Personal and global bests
        p_best = particles.copy()
        p_best_scores = np.full(n_particles, float('inf'))
        g_best = particles[0].copy()
        g_best_score = float('inf')

        def evaluate_particle(particle):
            """Evaluate cost of a particle's schedule."""
            total_cost = 0
            penalty = 0

            # Simulate schedule
            ev_socs = [ev_cfg['ev'].soc for ev_cfg in self.evs]
            hour_grid_usage = {h: self.grid_usage[h] for h in range(current_hour, current_hour + horizon)}

            for t in range(horizon):
                h = current_hour + t
                if h >= max_hour:
                    break

                available_capacity = self.grid_capacity_per_hour.get(h, float('inf')) - hour_grid_usage[h]
                hour_grid_used = 0

                for ev_id, ev_cfg in enumerate(self.evs):
                    if h < ev_cfg['arrival_time'] or h >= ev_cfg['target_time']:
                        continue

                    ev = ev_cfg['ev']
                    action_val = particle[ev_id * horizon + t]

                    # Charge (action_val is between 0 and 1)
                    charge_rate = action_val * ev.max_charge_rate
                    energy = min(charge_rate, (1.0 - ev_socs[ev_id]) * ev.battery_capacity,
                                 available_capacity - hour_grid_used)

                    if energy > 0:
                        building_energy = max(0, -self.building.get_net_energy_demand(h))
                        energy_from_grid = max(0, energy - building_energy)
                        total_cost += energy_from_grid * self.grid.get_price(h)
                        ev_socs[ev_id] += energy / ev.battery_capacity
                        hour_grid_used += energy_from_grid

                    # Constraint penalties
                    if ev_socs[ev_id] < self.min_soc:
                        penalty += 2000 * (self.min_soc - ev_socs[ev_id])
                    if ev_socs[ev_id] > 1.0:
                        penalty += 1000 * (ev_socs[ev_id] - 1.0)

            # Terminal penalties
            for ev_id, ev_cfg in enumerate(self.evs):
                if current_hour + horizon >= ev_cfg['target_time']:
                    shortfall = max(0, ev_cfg['desired_soc'] - ev_socs[ev_id])
                    penalty += 8000 * shortfall

            return total_cost + penalty

        # PSO iterations
        for iteration in range(n_iterations):
            # Evaluate all particles
            for i in range(n_particles):
                score = evaluate_particle(particles[i])

                # Update personal best
                if score < p_best_scores[i]:
                    p_best_scores[i] = score
                    p_best[i] = particles[i].copy()

                # Update global best
                if score < g_best_score:
                    g_best_score = score
                    g_best = particles[i].copy()

            # Update velocities and positions
            r1 = np.random.rand(n_particles, dim)
            r2 = np.random.rand(n_particles, dim)

            velocities = (w * velocities +
                          c1 * r1 * (p_best - particles) +
                          c2 * r2 * (g_best - particles))

            particles = particles + velocities
            particles = np.clip(particles, 0, 1)  # Only positive values for charging

        # Execute first step of best solution
        total_benefit = 0
        actions_taken = []

        for ev_id, ev_cfg in enumerate(self.evs):
            if current_hour < ev_cfg['arrival_time'] or current_hour >= ev_cfg['target_time']:
                continue

            ev = ev_cfg['ev']
            action_val = g_best[ev_id * horizon]  # First time step

            if action_val > 0.1:  # Charge
                charge_rate = action_val * ev.max_charge_rate
                energy = ev.charge(charge_rate)
                building_energy = max(0, -self.building.get_net_energy_demand(current_hour))
                energy_from_grid = max(0, energy - building_energy)
                cost = energy_from_grid * self.grid.get_price(current_hour)
                total_benefit -= cost
                self.grid_usage[current_hour] += energy_from_grid
                actions_taken.append(f"EV {ev_id}: Charged {energy:.2f} kWh, Cost: {cost:.2f} €")

        for action in actions_taken:
            print(action)

        return len(actions_taken) > 0, total_benefit

    def dqn_charge(self, current_hour, episodes=1000, batch_size=32, gamma=0.95,
                   epsilon_start=1.0, epsilon_end=0.01, epsilon_decay=0.995):
        """
        Deep Q-Network for multi-EV charging using neural networks (charge-only).
        Requires tensorflow/keras.
        """
        try:
            import tensorflow as tf
            from tensorflow import keras
            from collections import deque
        except ImportError:
            print("TensorFlow required. Install with: pip install tensorflow")
            return False, 0

        # Suppress TF warnings
        tf.get_logger().setLevel('ERROR')

        # State: [ev1_soc, ev2_soc, ..., hour, grid_available, building_surplus]
        n_evs = len(self.evs)
        state_size = n_evs + 3  # n_evs SOCs + hour + grid_available + building_surplus
        n_actions = 2  # charge, standby (no discharge)

        # Create Q-networks for each EV
        def create_network():
            model = keras.Sequential([
                keras.layers.Dense(64, activation='relu', input_shape=(state_size,)),
                keras.layers.Dense(64, activation='relu'),
                keras.layers.Dense(32, activation='relu'),
                keras.layers.Dense(n_actions, activation='linear')
            ])
            model.compile(optimizer=keras.optimizers.Adam(learning_rate=0.001),
                          loss='mse')
            return model

        q_networks = [create_network() for _ in range(n_evs)]
        target_networks = [create_network() for _ in range(n_evs)]

        # Initialize target networks
        for i in range(n_evs):
            target_networks[i].set_weights(q_networks[i].get_weights())

        # Replay buffers for each EV
        replay_buffers = [deque(maxlen=2000) for _ in range(n_evs)]

        # Training
        epsilon = epsilon_start
        min_hour = min(ev_cfg['arrival_time'] for ev_cfg in self.evs)
        max_hour = max(ev_cfg['target_time'] for ev_cfg in self.evs)

        for episode in range(episodes):
            # Reset environment
            ev_socs = [ev_cfg['ev'].soc for ev_cfg in self.evs]
            episode_grid_usage = defaultdict(float)

            for h in range(min_hour, max_hour):
                available_capacity = self.grid_capacity_per_hour.get(h, float('inf'))
                remaining_capacity = available_capacity - episode_grid_usage[h]
                building_surplus = max(0, -self.building.get_net_energy_demand(h))

                # Construct state
                state = np.array(ev_socs + [h / 24.0, remaining_capacity / 100.0,
                                            building_surplus / 50.0])

                # Each EV takes action
                for ev_id, ev_cfg in enumerate(self.evs):
                    if h < ev_cfg['arrival_time'] or h >= ev_cfg['target_time']:
                        continue

                    # Epsilon-greedy
                    if np.random.rand() < epsilon:
                        action = np.random.randint(n_actions)
                    else:
                        q_values = q_networks[ev_id].predict(state.reshape(1, -1), verbose=0)
                        action = np.argmax(q_values[0])

                    # Execute action
                    reward = 0
                    ev = ev_cfg['ev']

                    if action == 0:  # Charge
                        max_energy = min(ev.max_charge_rate,
                                         (1.0 - ev_socs[ev_id]) * ev.battery_capacity,
                                         remaining_capacity)
                        if max_energy > 0:
                            energy_from_building = min(building_surplus, max_energy)
                            energy_from_grid = max_energy - energy_from_building
                            reward = -energy_from_grid * self.grid.get_price(h)
                            ev_socs[ev_id] += max_energy / ev.battery_capacity
                            episode_grid_usage[h] += energy_from_grid
                            remaining_capacity -= energy_from_grid

                    # Penalties
                    if ev_socs[ev_id] < self.min_soc:
                        reward -= 1000
                    if h == ev_cfg['target_time'] - 1 and ev_socs[ev_id] < ev_cfg['desired_soc']:
                        reward -= 10000 * (ev_cfg['desired_soc'] - ev_socs[ev_id])

                    # Next state
                    next_state = np.array(ev_socs + [min(h + 1, max_hour - 1) / 24.0,
                                                     remaining_capacity / 100.0,
                                                     building_surplus / 50.0])

                    # Store transition
                    replay_buffers[ev_id].append((state, action, reward, next_state,
                                                  h >= ev_cfg['target_time'] - 1))

                    # Train if enough samples
                    if len(replay_buffers[ev_id]) >= batch_size:
                        minibatch = np.random.choice(len(replay_buffers[ev_id]),
                                                     batch_size, replace=False)

                        states = np.array([replay_buffers[ev_id][i][0] for i in minibatch])
                        actions = np.array([replay_buffers[ev_id][i][1] for i in minibatch])
                        rewards = np.array([replay_buffers[ev_id][i][2] for i in minibatch])
                        next_states = np.array([replay_buffers[ev_id][i][3] for i in minibatch])
                        dones = np.array([replay_buffers[ev_id][i][4] for i in minibatch])

                        # Compute targets
                        current_q = q_networks[ev_id].predict(states, verbose=0)
                        next_q = target_networks[ev_id].predict(next_states, verbose=0)

                        targets = current_q.copy()
                        for idx in range(batch_size):
                            if dones[idx]:
                                targets[idx][actions[idx]] = rewards[idx]
                            else:
                                targets[idx][actions[idx]] = rewards[idx] + gamma * np.max(next_q[idx])

                        q_networks[ev_id].fit(states, targets, epochs=1, verbose=0)

            # Decay epsilon
            epsilon = max(epsilon_end, epsilon * epsilon_decay)

            # Update target networks periodically
            if episode % 10 == 0:
                for i in range(n_evs):
                    target_networks[i].set_weights(q_networks[i].get_weights())

        # Execute for current hour
        ev_socs = [ev_cfg['ev'].soc for ev_cfg in self.evs]
        available_capacity = self.grid_capacity_per_hour.get(current_hour, float('inf'))
        remaining_capacity = available_capacity - self.grid_usage[current_hour]
        building_surplus = max(0, -self.building.get_net_energy_demand(current_hour))

        state = np.array(ev_socs + [current_hour / 24.0, remaining_capacity / 100.0,
                                    building_surplus / 50.0])

        total_benefit = 0
        actions_taken = []

        for ev_id, ev_cfg in enumerate(self.evs):
            if current_hour < ev_cfg['arrival_time'] or current_hour >= ev_cfg['target_time']:
                continue

            q_values = q_networks[ev_id].predict(state.reshape(1, -1), verbose=0)
            action = np.argmax(q_values[0])

            ev = ev_cfg['ev']

            if action == 0 and remaining_capacity > 0:  # Charge
                max_energy = min(ev.max_charge_rate, (1.0 - ev.soc) * ev.battery_capacity,
                                 remaining_capacity)
                if max_energy > 0:
                    energy = ev.charge(max_energy)
                    energy_from_building = min(building_surplus, energy)
                    energy_from_grid = energy - energy_from_building
                    cost = energy_from_grid * self.grid.get_price(current_hour)
                    total_benefit -= cost
                    self.grid_usage[current_hour] += energy_from_grid
                    remaining_capacity -= energy_from_grid
                    actions_taken.append(f"EV {ev_id}: Charged {energy:.2f} kWh, Cost: {cost:.2f} €")

        for action in actions_taken:
            print(action)

        return len(actions_taken) > 0, total_benefit

    def reset_grid_usage(self):
        """Reset grid usage tracking (call at start of new simulation)."""
        self.grid_usage.clear()
