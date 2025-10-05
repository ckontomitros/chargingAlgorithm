"""
Test suite for Multi-EV V2G Charging System
Tests all algorithms and functionality using actual project models
"""
import unittest
import sys
import os
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.building import Building
from src.models.electric_vehicle import ElectricVehicle
from src.models.grid import Grid
from src.models.multi_ev_v2g_charging_system import MultiEVV2GChargingSystem


class TestMultiEVV2GSystem(unittest.TestCase):
    """Test suite for Multi-EV V2G Charging System"""

    def setup(self):
        """Setup common test environment with actual models"""

        # Create building with PV and battery
        energy_consumption = [15, 12, 10, 10, 12, 15, 20, 25, 22, 20,
                              18, 18, 20, 22, 24, 26, 28, 30, 28, 25,
                              22, 20, 18, 16]  # 24-hour consumption profile (kWh)

        building = Building(
            energy_consumption_profile=energy_consumption,
            panel_area=100,  # m²
            panel_efficiency=0.18,  # 18% efficiency
            peak_solar_irradiance=1000,  # W/m²
            battery_capacity=50,  # kWh
            battery_efficiency=0.95,
            initial_soc=0.5,  # 50% charged
            dod=0.8,  # 80% depth of discharge
            duration=2  # hours
        )

        # Create EVs with different characteristics
        ev1 = ElectricVehicle(
            battery_capacity=60.0,  # kWh
            initial_soc=0.3,  # 30% charged
            energy_per_km=0.2,  # kWh/km
            max_charge_rate=7.0,  # kW
            max_discharge_rate=7.0,  # kW
            usage_stats={'departure': 8, 'arrival': 18, 'daily_km': 50},
            dod=0.8,
            duration=2
        )

        ev2 = ElectricVehicle(
            battery_capacity=40.0,
            initial_soc=0.4,
            energy_per_km=0.18,
            max_charge_rate=5.0,
            max_discharge_rate=5.0,
            usage_stats={'departure': 9, 'arrival': 20, 'daily_km': 40},
            dod=0.8,
            duration=2
        )

        ev3 = ElectricVehicle(
            battery_capacity=50.0,
            initial_soc=0.2,
            energy_per_km=0.19,
            max_charge_rate=6.0,
            max_discharge_rate=6.0,
            usage_stats={'departure': 10, 'arrival': 17, 'daily_km': 45},
            dod=0.8,
            duration=2
        )

        # Create EV configurations
        evs = [
            {
                'ev': ev1,
                'desired_soc': 0.8,
                'target_time': 18,
                'arrival_time': 8
            },
            {
                'ev': ev2,
                'desired_soc': 0.9,
                'target_time': 20,
                'arrival_time': 9
            },
            {
                'ev': ev3,
                'desired_soc': 0.85,
                'target_time': 17,
                'arrival_time': 10
            }
        ]

        # Create grid with time-of-use pricing
        price_profile = []
        sell_price_profile = []
        for h in range(24):
            if 0 <= h < 6:  # Off-peak
                price_profile.append(0.10)
                sell_price_profile.append(0.05)
            elif 6 <= h < 9 or 17 <= h < 21:  # Peak
                price_profile.append(0.25)
                sell_price_profile.append(0.12)
            else:  # Mid-peak
                price_profile.append(0.15)
                sell_price_profile.append(0.08)

        grid = Grid(price_profile=price_profile, sell_price_profile=sell_price_profile)

        # Grid capacity constraint (20 kW per hour)
        grid_capacity = {h: 20.0 for h in range(24)}

        return evs, building, grid, grid_capacity

    def assert_true(self, condition, test_name, message=""):
        """Assert that condition is true"""
        if condition:
            self.passed += 1
            self.test_results.append(f"✓ PASS: {test_name}")
            print(f"✓ PASS: {test_name}")
        else:
            self.failed += 1
            self.test_results.append(f"✗ FAIL: {test_name} - {message}")
            print(f"✗ FAIL: {test_name} - {message}")

    def assert_equal(self, actual, expected, test_name, tolerance=0.01):
        """Assert that actual equals expected (with tolerance for floats)"""
        if isinstance(actual, float) and isinstance(expected, float):
            condition = abs(actual - expected) < tolerance
            message = f"Expected {expected}, got {actual}"
        else:
            condition = actual == expected
            message = f"Expected {expected}, got {actual}"

        self.assert_true(condition, test_name, message)

    def test_initialization(self):
        """Test system initialization"""
        print("\n=== Testing Initialization ===")

        evs, building, grid, grid_capacity = self.setup()
        system = MultiEVV2GChargingSystem(building, evs, grid, grid_capacity)

        self.assert_equal(len(system.evs), 3, "Number of EVs")
        self.assert_true(system.building is not None, "Building initialized")
        self.assert_true(system.grid is not None, "Grid initialized")
        self.assert_equal(len(system.grid_usage), 0, "Grid usage tracking initialized")

    def test_simple_charge(self):
        """Test simple charging algorithm"""
        print("\n=== Testing Simple Charge Algorithm ===")

        evs, building, grid, grid_capacity = self.setup()
        system = MultiEVV2GChargingSystem(building, evs, grid, grid_capacity)

        # Store initial SOCs
        initial_socs = [ev_cfg['ev'].soc for ev_cfg in evs]

        # Run charging at hour 10
        action_taken, cost = system.simple_charge_multi(10)

        self.assert_true(action_taken, "Simple charge action taken")
        self.assert_true(cost >= 0, "Simple charge cost is non-negative", f"Cost: {cost}")

        # Check that at least one EV was charged
        final_socs = [ev_cfg['ev'].soc for ev_cfg in evs]
        soc_increased = any(final_socs[i] > initial_socs[i] for i in range(len(evs)))
        self.assert_true(soc_increased, "At least one EV SOC increased")

    def test_rl_charge(self):
        """Test reinforcement learning algorithm"""
        print("\n=== Testing RL Charge Algorithm ===")

        evs, building, grid, grid_capacity = self.setup()
        system = MultiEVV2GChargingSystem(building, evs, grid, grid_capacity)

        # Store initial SOCs
        initial_socs = [ev_cfg['ev'].soc for ev_cfg in evs]

        # Run RL charging at hour 10 (reduced episodes for testing)
        print("Training RL agent (500 episodes)...")
        action_taken, benefit = system.rl_charge_multi(10, episodes=500)

        self.assert_true(isinstance(action_taken, bool), "RL returns boolean")
        self.assert_true(isinstance(benefit, (int, float)), "RL returns numeric benefit")

        print(f"RL Result: Action={action_taken}, Benefit={benefit:.2f}€")

    def test_milp_charge(self):
        """Test MILP optimization algorithm"""
        print("\n=== Testing MILP Algorithm ===")

        try:
            import pulp

            evs, building, grid, grid_capacity = self.setup()
            system = MultiEVV2GChargingSystem(building, evs, grid, grid_capacity)

            # Run MILP at hour 10
            action_taken, benefit = system.milp_charge(10)

            self.assert_true(isinstance(action_taken, bool), "MILP returns boolean")
            self.assert_true(isinstance(benefit, (int, float)), "MILP returns numeric benefit")

            print(f"MILP Result: Action={action_taken}, Benefit={benefit:.2f}€")

        except ImportError:
            print("⚠ SKIP: MILP test (PuLP not installed)")

    def test_mpc_charge(self):
        """Test Model Predictive Control algorithm"""
        print("\n=== Testing MPC Algorithm ===")

        evs, building, grid, grid_capacity = self.setup()
        system = MultiEVV2GChargingSystem(building, evs, grid, grid_capacity)

        # Store initial SOCs
        initial_socs = [ev_cfg['ev'].soc for ev_cfg in evs]

        # Run MPC at hour 10
        print("Running MPC optimization...")
        action_taken, benefit = system.mpc_charge(10, horizon=4, iterations=30)

        self.assert_true(isinstance(action_taken, bool), "MPC returns boolean")
        self.assert_true(isinstance(benefit, (int, float)), "MPC returns numeric benefit")

        print(f"MPC Result: Action={action_taken}, Benefit={benefit:.2f}€")

    def test_dqn_charge(self):
        """Test Deep Q-Network algorithm"""
        print("\n=== Testing DQN Algorithm ===")

        try:
            import tensorflow

            evs, building, grid, grid_capacity = self.setup()
            system = MultiEVV2GChargingSystem(building, evs, grid, grid_capacity)

            # Run DQN at hour 10 (reduced episodes for testing)
            print("Training DQN agent (200 episodes)...")
            action_taken, benefit = system.dqn_charge(10, episodes=200, batch_size=16)

            self.assert_true(isinstance(action_taken, bool), "DQN returns boolean")
            self.assert_true(isinstance(benefit, (int, float)), "DQN returns numeric benefit")

            print(f"DQN Result: Action={action_taken}, Benefit={benefit:.2f}€")

        except ImportError:
            print("⚠ SKIP: DQN test (TensorFlow not installed)")

    def test_pso_charge(self):
        """Test Particle Swarm Optimization algorithm"""
        print("\n=== Testing PSO Algorithm ===")

        evs, building, grid, grid_capacity = self.setup()
        system = MultiEVV2GChargingSystem(building, evs, grid, grid_capacity)

        # Store initial SOCs
        initial_socs = [ev_cfg['ev'].soc for ev_cfg in evs]

        # Run PSO at hour 10
        print("Running PSO optimization...")
        action_taken, benefit = system.pso_charge(10, n_particles=20, n_iterations=30)

        self.assert_true(isinstance(action_taken, bool), "PSO returns boolean")
        self.assert_true(isinstance(benefit, (int, float)), "PSO returns numeric benefit")

        print(f"PSO Result: Action={action_taken}, Benefit={benefit:.2f}€")

    def test_grid_capacity_constraint(self):
        """Test that grid capacity constraints are respected"""
        print("\n=== Testing Grid Capacity Constraints ===")

        evs, building, grid, grid_capacity = self.setup()
        # Set very low grid capacity
        grid_capacity = {h: 5.0 for h in range(24)}  # Only 5 kW available
        system = MultiEVV2GChargingSystem(building, evs, grid, grid_capacity)

        # Run charging
        system.simple_charge_multi(10)

        # Check that grid usage doesn't exceed capacity
        for hour, usage in system.grid_usage.items():
            self.assert_true(
                usage <= grid_capacity[hour] + 0.1,  # Small tolerance
                f"Grid capacity respected at hour {hour}",
                f"Usage {usage:.2f} exceeds capacity {grid_capacity[hour]:.2f}"
            )

    def test_soc_constraints(self):
        """Test that SOC stays within valid bounds"""
        print("\n=== Testing SOC Constraints ===")

        evs, building, grid, grid_capacity = self.setup()
        system = MultiEVV2GChargingSystem(building, evs, grid, grid_capacity)

        # Run multiple hours
        for hour in range(8, 15):
            system.simple_charge_multi(hour)

        # Check all EVs have valid SOC
        for i, ev_cfg in enumerate(evs):
            ev = ev_cfg['ev']
            self.assert_true(
                0 <= ev.soc <= 1.0,
                f"EV {i} SOC within bounds",
                f"SOC = {ev.soc}"
            )
            self.assert_true(
                ev.soc >= system.min_soc,
                f"EV {i} SOC above minimum",
                f"SOC = {ev.soc}, min = {system.min_soc}"
            )

    def test_arrival_departure_times(self):
        """Test that EVs only charge/discharge during available times"""
        print("\n=== Testing Arrival/Departure Times ===")

        evs, building, grid, grid_capacity = self.setup()
        system = MultiEVV2GChargingSystem(building, evs, grid, grid_capacity)

        # Try charging before any EV arrives (hour 7)
        initial_socs = [ev_cfg['ev'].soc for ev_cfg in evs]
        action_taken, _ = system.simple_charge_multi(7)
        final_socs = [ev_cfg['ev'].soc for ev_cfg in evs]

        # No EV should have charged
        self.assert_true(
            all(final_socs[i] == initial_socs[i] for i in range(len(evs))),
            "No charging before arrival",
            "Some EV charged before arrival"
        )

        # Try charging after all EVs departed (hour 21)
        initial_socs = [ev_cfg['ev'].soc for ev_cfg in evs]
        action_taken, _ = system.simple_charge_multi(21)
        final_socs = [ev_cfg['ev'].soc for ev_cfg in evs]

        self.assert_true(
            all(final_socs[i] == initial_socs[i] for i in range(len(evs))),
            "No charging after departure",
            "Some EV charged after departure"
        )

    def test_building_integration(self):
        """Test integration with building energy management"""
        print("\n=== Testing Building Integration ===")

        evs, building, grid, grid_capacity = self.setup()
        system = MultiEVV2GChargingSystem(building, evs, grid, grid_capacity)

        # Check building energy at different hours
        morning_demand = building.get_net_energy_demand(8)
        noon_demand = building.get_net_energy_demand(12)  # Should have solar

        self.assert_true(
            noon_demand < morning_demand,
            "Solar reduces building demand",
            f"Morning: {morning_demand:.2f}, Noon: {noon_demand:.2f}"
        )

    def test_full_simulation(self):
        """Test full day simulation with all EVs"""
        print("\n=== Testing Full Day Simulation ===")

        evs, building, grid, grid_capacity = self.setup()
        system = MultiEVV2GChargingSystem(building, evs, grid, grid_capacity)

        total_cost = 0

        # Run simulation from 8:00 to 20:00
        for hour in range(8, 21):
            action_taken, cost = system.simple_charge_multi(hour)
            total_cost += cost
            if action_taken:
                print(f"Hour {hour}: Cost = {cost:.2f}€")

        # Check that all EVs reached their target SOC
        for i, ev_cfg in enumerate(evs):
            ev = ev_cfg['ev']
            target_soc = ev_cfg['desired_soc']
            # Allow small tolerance due to charging constraints
            self.assert_true(
                ev.soc >= target_soc - 0.1,
                f"EV {i} reached target SOC",
                f"Target: {target_soc:.2f}, Actual: {ev.soc:.2f}"
            )

        print(f"\nTotal simulation cost: {total_cost:.2f}€")

    def test_algorithm_comparison(self):
        """Compare all algorithms on the same scenario"""
        print("\n=== Algorithm Comparison ===")

        algorithms = [
            ("Simple", lambda sys: sys.simple_charge_multi(10)),
            ("RL", lambda sys: sys.rl_charge_multi(10, episodes=300)),
            ("MPC", lambda sys: sys.mpc_charge(10, horizon=4, iterations=20)),
            ("PSO", lambda sys: sys.pso_charge(10, n_particles=15, n_iterations=20)),
        ]

        results = {}

        for name, algo_func in algorithms:
            # Create fresh environment for each algorithm
            evs, building, grid, grid_capacity = self.setup()
            system = MultiEVV2GChargingSystem(building, evs, grid, grid_capacity)

            try:
                print(f"\nRunning {name}...")
                action_taken, benefit = algo_func(system)
                results[name] = benefit
                print(f"{name}: Action={action_taken}, Benefit={benefit:.2f}€")
            except Exception as e:
                print(f"{name}: Error - {str(e)}")
                results[name] = None

        # Print comparison
        print("\n--- Algorithm Comparison Summary ---")
        for name, benefit in results.items():
            if benefit is not None:
                print(f"{name:15s}: {benefit:>10.2f}€")

    def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("Multi-EV V2G Charging System - Test Suite")
        print("=" * 60)

        # Run tests
        self.test_initialization()
        self.test_simple_charge()
        self.test_rl_charge()
        self.test_milp_charge()
        self.test_mpc_charge()
        self.test_dqn_charge()
        self.test_pso_charge()
        self.test_grid_capacity_constraint()
        self.test_soc_constraints()
        self.test_arrival_departure_times()
        self.test_building_integration()
        self.test_full_simulation()
        self.test_algorithm_comparison()

        # Print summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success Rate: {100 * self.passed / (self.passed + self.failed):.1f}%")
        print("=" * 60)

        return self.failed == 0


if __name__ == "__main__":
    # Run tests
    test_suite = TestMultiEVV2GSystem()
    success = test_suite.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if success else 1)
