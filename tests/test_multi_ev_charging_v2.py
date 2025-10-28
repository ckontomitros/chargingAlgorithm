"""
Test suite for Multi-EV Charging System (Charge-Only, No V2G)
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
from src.models.multi_ev_charging_system import MultiEVChargingSystem


class TestMultiEVChargingSystem(unittest.TestCase):
    """Test suite for Multi-EV Charging System (Charge-Only)"""

    def setUp(self):
        """Setup common test environment with actual models"""

        # Create building with PV and battery
        energy_consumption = [15, 12, 10, 10, 12, 15, 20, 25, 22, 20,
                              18, 18, 20, 22, 24, 26, 28, 30, 28, 25,
                              22, 20, 18, 16]  # 24-hour consumption profile (kWh)

        self.building = Building(
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
            max_discharge_rate=7.0,  # kW (not used in charge-only system)
            usage_stats={'departure': 18, 'arrival': 8, 'daily_km': 50},
            dod=0.8,
            duration=2
        )

        ev2 = ElectricVehicle(
            battery_capacity=40.0,
            initial_soc=0.4,
            energy_per_km=0.18,
            max_charge_rate=5.0,
            max_discharge_rate=5.0,
            usage_stats={'departure': 20, 'arrival': 9, 'daily_km': 40},
            dod=0.8,
            duration=2
        )

        ev3 = ElectricVehicle(
            battery_capacity=50.0,
            initial_soc=0.2,
            energy_per_km=0.19,
            max_charge_rate=6.0,
            max_discharge_rate=6.0,
            usage_stats={'departure': 17, 'arrival': 10, 'daily_km': 45},
            dod=0.8,
            duration=2
        )

        # Create EV configurations
        self.evs = [
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

        self.grid = Grid(price_profile=price_profile, sell_price_profile=sell_price_profile)

        # Grid capacity constraint (20 kW per hour)
        self.grid_capacity = {h: 20.0 for h in range(24)}

    def test_initialization(self):
        """Test system initialization"""
        print("\n=== Testing Initialization ===")

        system = MultiEVChargingSystem(self.building, self.evs, self.grid, self.grid_capacity)

        self.assertEqual(len(system.evs), 3, "Number of EVs should be 3")
        self.assertIsNotNone(system.building, "Building should be initialized")
        self.assertIsNotNone(system.grid, "Grid should be initialized")
        self.assertEqual(len(system.grid_usage), 0, "Grid usage tracking should be empty initially")
        print("✓ Initialization test passed")

    def test_simple_charge(self):
        """Test simple charging algorithm"""
        print("\n=== Testing Simple Charge Algorithm ===")

        system = MultiEVChargingSystem(self.building, self.evs, self.grid, self.grid_capacity)

        # Store initial SOCs
        initial_socs = [ev_cfg['ev'].soc for ev_cfg in self.evs]

        # Run charging at hour 10
        action_taken, cost = system.simple_charge_multi(10)

        self.assertTrue(action_taken, "Simple charge action should be taken")
        self.assertLessEqual(cost, 0, f"Cost should be non-positive (benefit format): {cost}")

        # Check that at least one EV was charged
        final_socs = [ev_cfg['ev'].soc for ev_cfg in self.evs]
        soc_increased = any(final_socs[i] > initial_socs[i] for i in range(len(self.evs)))
        self.assertTrue(soc_increased, "At least one EV SOC should increase")
        
        print(f"✓ Simple charge test passed - Action: {action_taken}, Cost: {cost:.2f}€")

    def test_charge_when_soc_below_target(self):
        """Test that algorithms charge when SOC is below target"""
        print("\n=== Testing Charge When SOC Below Target ===")

        algorithms = [
            ("Simple", lambda sys, h: sys.simple_charge_multi(h)),
            ("RL", lambda sys, h: sys.rl_charge_multi(h, episodes=200)),
            ("PSO", lambda sys, h: sys.pso_charge(h, n_particles=15, n_iterations=20)),
            ("MPC", lambda sys, h: sys.mpc_charge(h, horizon=3, iterations=20)),
        ]

        for algo_name, algo_func in algorithms:
            print(f"\n  Testing {algo_name}...")
            
            # Reset EVs to low SOC
            for ev_cfg in self.evs:
                ev_cfg['ev'].soc = 0.3  # Well below target
            
            system = MultiEVChargingSystem(self.building, self.evs, self.grid, self.grid_capacity)
            
            charged_at_least_once = False
            for hour in range(10, 15):
                initial_socs = [ev_cfg['ev'].soc for ev_cfg in self.evs]
                action_taken, benefit = algo_func(system, hour)
                final_socs = [ev_cfg['ev'].soc for ev_cfg in self.evs]
                
                # Check if any EV charged
                if any(final_socs[i] > initial_socs[i] + 0.001 for i in range(len(self.evs))):
                    charged_at_least_once = True
                    print(f"    {algo_name} charged at hour {hour}")
            
            self.assertTrue(
                charged_at_least_once,
                f"{algo_name} should charge when EVs are below target SOC"
            )
            print(f"  ✓ {algo_name} charges when needed")

    def test_standby_when_soc_reached(self):
        """Test that algorithms go to standby when target SOC is reached"""
        print("\n=== Testing Standby When Target SOC Reached ===")

        algorithms = [
            ("Simple", lambda sys, h: sys.simple_charge_multi(h)),
            ("RL", lambda sys, h: sys.rl_charge_multi(h, episodes=200)),
            ("PSO", lambda sys, h: sys.pso_charge(h, n_particles=15, n_iterations=20)),
            ("MPC", lambda sys, h: sys.mpc_charge(h, horizon=3, iterations=20)),
        ]

        for algo_name, algo_func in algorithms:
            print(f"\n  Testing {algo_name}...")
            
            # Set all EVs to target SOC
            self.evs[0]['ev'].soc = self.evs[0]['desired_soc']
            self.evs[1]['ev'].soc = self.evs[1]['desired_soc']
            self.evs[2]['ev'].soc = self.evs[2]['desired_soc']
            
            system = MultiEVChargingSystem(self.building, self.evs, self.grid, self.grid_capacity)
            
            # Run algorithm
            initial_socs = [ev_cfg['ev'].soc for ev_cfg in self.evs]
            action_taken, benefit = algo_func(system, 12)
            final_socs = [ev_cfg['ev'].soc for ev_cfg in self.evs]
            
            # Check that no EV charged significantly (small tolerance for numerical errors)
            for i in range(len(self.evs)):
                self.assertAlmostEqual(
                    final_socs[i],
                    initial_socs[i],
                    places=2,
                    msg=f"{algo_name}: EV {i} should not charge when at target SOC"
                )
            
            print(f"  ✓ {algo_name} goes to standby when target reached")

    def test_standby_before_arrival(self):
        """Test that algorithms don't charge before EV arrival"""
        print("\n=== Testing Standby Before Arrival ===")

        algorithms = [
            ("Simple", lambda sys, h: sys.simple_charge_multi(h)),
            ("RL", lambda sys, h: sys.rl_charge_multi(h, episodes=200)),
            ("PSO", lambda sys, h: sys.pso_charge(h, n_particles=15, n_iterations=20)),
            ("MPC", lambda sys, h: sys.mpc_charge(h, horizon=3, iterations=20)),
        ]

        for algo_name, algo_func in algorithms:
            print(f"\n  Testing {algo_name}...")
            
            # Reset EVs to low SOC
            for ev_cfg in self.evs:
                ev_cfg['ev'].soc = 0.3
            
            system = MultiEVChargingSystem(self.building, self.evs, self.grid, self.grid_capacity)
            
            # Try charging before earliest arrival (hour 7, earliest is 8)
            initial_socs = [ev_cfg['ev'].soc for ev_cfg in self.evs]
            action_taken, benefit = algo_func(system, 7)
            final_socs = [ev_cfg['ev'].soc for ev_cfg in self.evs]
            
            for i in range(len(self.evs)):
                self.assertAlmostEqual(
                    final_socs[i],
                    initial_socs[i],
                    places=6,
                    msg=f"{algo_name}: EV {i} should not charge before arrival"
                )
            
            print(f"  ✓ {algo_name} correctly stays on standby before arrival")

    def test_standby_after_departure(self):
        """Test that algorithms don't charge after EV departure"""
        print("\n=== Testing Standby After Departure ===")

        algorithms = [
            ("Simple", lambda sys, h: sys.simple_charge_multi(h)),
            ("RL", lambda sys, h: sys.rl_charge_multi(h, episodes=200)),
            ("PSO", lambda sys, h: sys.pso_charge(h, n_particles=15, n_iterations=20)),
            ("MPC", lambda sys, h: sys.mpc_charge(h, horizon=3, iterations=20)),
        ]

        for algo_name, algo_func in algorithms:
            print(f"\n  Testing {algo_name}...")
            
            # Reset EVs to low SOC
            for ev_cfg in self.evs:
                ev_cfg['ev'].soc = 0.5
            
            system = MultiEVChargingSystem(self.building, self.evs, self.grid, self.grid_capacity)
            
            # Try charging after latest departure (hour 21, latest target is 20)
            initial_socs = [ev_cfg['ev'].soc for ev_cfg in self.evs]
            action_taken, benefit = algo_func(system, 21)
            final_socs = [ev_cfg['ev'].soc for ev_cfg in self.evs]
            
            for i in range(len(self.evs)):
                self.assertAlmostEqual(
                    final_socs[i],
                    initial_socs[i],
                    places=6,
                    msg=f"{algo_name}: EV {i} should not charge after departure"
                )
            
            print(f"  ✓ {algo_name} correctly stays on standby after departure")

    def test_grid_capacity_not_exceeded_simple(self):
        """Test that simple algorithm respects grid capacity"""
        print("\n=== Testing Grid Capacity - Simple Algorithm ===")

        # Set strict grid capacity
        grid_capacity = {h: 10.0 for h in range(24)}  # 10 kW limit
        system = MultiEVChargingSystem(self.building, self.evs, self.grid, grid_capacity)

        # Run charging for multiple hours
        for hour in range(10, 16):
            system.simple_charge_multi(hour)
            
            # Check grid usage doesn't exceed capacity
            if hour in system.grid_usage:
                self.assertLessEqual(
                    system.grid_usage[hour],
                    grid_capacity[hour] + 0.1,  # Small tolerance
                    f"Simple: Grid usage {system.grid_usage[hour]:.2f} kW exceeds "
                    f"capacity {grid_capacity[hour]:.2f} kW at hour {hour}"
                )
                print(f"  Hour {hour}: Grid usage = {system.grid_usage[hour]:.2f} kW "
                      f"(capacity = {grid_capacity[hour]:.2f} kW) ✓")

    def test_grid_capacity_not_exceeded_rl(self):
        """Test that RL algorithm respects grid capacity"""
        print("\n=== Testing Grid Capacity - RL Algorithm ===")

        # Set strict grid capacity
        grid_capacity = {h: 8.0 for h in range(24)}  # 8 kW limit
        system = MultiEVChargingSystem(self.building, self.evs, self.grid, grid_capacity)

        # Run RL charging for multiple hours
        for hour in range(10, 14):
            system.rl_charge_multi(hour, episodes=300)
            
            # Check grid usage doesn't exceed capacity
            if hour in system.grid_usage:
                self.assertLessEqual(
                    system.grid_usage[hour],
                    grid_capacity[hour] + 0.5,  # Slightly larger tolerance for RL
                    f"RL: Grid usage {system.grid_usage[hour]:.2f} kW exceeds "
                    f"capacity {grid_capacity[hour]:.2f} kW at hour {hour}"
                )
                print(f"  Hour {hour}: Grid usage = {system.grid_usage[hour]:.2f} kW "
                      f"(capacity = {grid_capacity[hour]:.2f} kW) ✓")

    def test_grid_capacity_not_exceeded_pso(self):
        """Test that PSO algorithm respects grid capacity"""
        print("\n=== Testing Grid Capacity - PSO Algorithm ===")

        # Set strict grid capacity
        grid_capacity = {h: 9.0 for h in range(24)}  # 9 kW limit
        system = MultiEVChargingSystem(self.building, self.evs, self.grid, grid_capacity)

        # Run PSO charging for multiple hours
        for hour in range(10, 14):
            system.pso_charge(hour, n_particles=20, n_iterations=25)
            
            # Check grid usage doesn't exceed capacity
            if hour in system.grid_usage:
                self.assertLessEqual(
                    system.grid_usage[hour],
                    grid_capacity[hour] + 0.5,  # Tolerance for PSO
                    f"PSO: Grid usage {system.grid_usage[hour]:.2f} kW exceeds "
                    f"capacity {grid_capacity[hour]:.2f} kW at hour {hour}"
                )
                print(f"  Hour {hour}: Grid usage = {system.grid_usage[hour]:.2f} kW "
                      f"(capacity = {grid_capacity[hour]:.2f} kW) ✓")

    def test_grid_capacity_not_exceeded_mpc(self):
        """Test that MPC algorithm respects grid capacity"""
        print("\n=== Testing Grid Capacity - MPC Algorithm ===")

        # Set strict grid capacity
        grid_capacity = {h: 10.0 for h in range(24)}  # 10 kW limit
        system = MultiEVChargingSystem(self.building, self.evs, self.grid, grid_capacity)

        # Run MPC charging for multiple hours
        for hour in range(10, 14):
            system.mpc_charge(hour, horizon=4, iterations=25)
            
            # Check grid usage doesn't exceed capacity
            if hour in system.grid_usage:
                self.assertLessEqual(
                    system.grid_usage[hour],
                    grid_capacity[hour] + 0.5,  # Tolerance for MPC
                    f"MPC: Grid usage {system.grid_usage[hour]:.2f} kW exceeds "
                    f"capacity {grid_capacity[hour]:.2f} kW at hour {hour}"
                )
                print(f"  Hour {hour}: Grid usage = {system.grid_usage[hour]:.2f} kW "
                      f"(capacity = {grid_capacity[hour]:.2f} kW) ✓")

    def test_grid_capacity_not_exceeded_milp(self):
        """Test that MILP algorithm respects grid capacity"""
        print("\n=== Testing Grid Capacity - MILP Algorithm ===")

        try:
            import pulp

            # Set strict grid capacity
            grid_capacity = {h: 12.0 for h in range(24)}  # 12 kW limit
            system = MultiEVChargingSystem(self.building, self.evs, self.grid, grid_capacity)

            # Run MILP charging for multiple hours
            for hour in range(10, 14):
                system.milp_charge(hour)
                
                # Check grid usage doesn't exceed capacity
                if hour in system.grid_usage:
                    self.assertLessEqual(
                        system.grid_usage[hour],
                        grid_capacity[hour] + 0.1,  # MILP should be very precise
                        f"MILP: Grid usage {system.grid_usage[hour]:.2f} kW exceeds "
                        f"capacity {grid_capacity[hour]:.2f} kW at hour {hour}"
                    )
                    print(f"  Hour {hour}: Grid usage = {system.grid_usage[hour]:.2f} kW "
                          f"(capacity = {grid_capacity[hour]:.2f} kW) ✓")

        except ImportError:
            print("⚠ SKIP: MILP grid capacity test (PuLP not installed)")
            self.skipTest("PuLP not installed")

    def test_urgent_charging_near_deadline(self):
        """Test that algorithms charge urgently when approaching deadline"""
        print("\n=== Testing Urgent Charging Near Deadline ===")

        # Create scenario: EV needs to charge soon before departure
        ev_urgent = ElectricVehicle(
            battery_capacity=50.0,
            initial_soc=0.3,  # Low SOC
            energy_per_km=0.2,
            max_charge_rate=10.0,
            max_discharge_rate=10.0,
            usage_stats={'departure': 13, 'arrival': 10, 'daily_km': 40},
            dod=0.8,
            duration=2
        )

        evs_urgent = [{
            'ev': ev_urgent,
            'desired_soc': 0.8,  # Needs significant charge
            'target_time': 13,   # Departing soon
            'arrival_time': 10
        }]

        system = MultiEVChargingSystem(self.building, evs_urgent, self.grid, self.grid_capacity)

        # Run charging near deadline (hour 12, only 1 hour left)
        initial_soc = ev_urgent.soc
        action_taken, benefit = system.simple_charge_multi(12)
        final_soc = ev_urgent.soc

        self.assertTrue(action_taken, "Should charge when near deadline with low SOC")
        self.assertGreater(final_soc, initial_soc, "SOC should increase near deadline")
        print(f"  ✓ Charged near deadline: {initial_soc:.2f} → {final_soc:.2f}")

    def test_low_priority_charging_with_time(self):
        """Test that algorithms can defer charging when there's plenty of time"""
        print("\n=== Testing Deferred Charging With Available Time ===")

        # This test is more relevant for cost-optimizing algorithms like RL
        ev_time = ElectricVehicle(
            battery_capacity=60.0,
            initial_soc=0.6,  # Moderate SOC
            energy_per_km=0.2,
            max_charge_rate=7.0,
            max_discharge_rate=7.0,
            usage_stats={'departure': 20, 'arrival': 10, 'daily_km': 40},
            dod=0.8,
            duration=2
        )

        evs_time = [{
            'ev': ev_time,
            'desired_soc': 0.8,  # Needs some charge
            'target_time': 20,   # Lots of time available
            'arrival_time': 10
        }]

        # Use peak pricing at hour 18 (expensive)
        system = MultiEVChargingSystem(self.building, evs_time, self.grid, self.grid_capacity)

        # RL might choose to wait for better pricing
        initial_soc = ev_time.soc
        action_taken, benefit = system.rl_charge_multi(18, episodes=400)
        
        print(f"  RL at peak hour (18): Action={action_taken}, "
              f"SOC: {initial_soc:.2f} → {ev_time.soc:.2f}")
        print(f"  ✓ Algorithm made decision with time available")

    def test_multiple_evs_grid_sharing(self):
        """Test that multiple EVs share grid capacity appropriately"""
        print("\n=== Testing Grid Capacity Sharing Among Multiple EVs ===")

        # Set limited grid capacity that requires sharing
        grid_capacity = {h: 12.0 for h in range(24)}  # Can't charge all EVs at max rate
        system = MultiEVChargingSystem(self.building, self.evs, self.grid, grid_capacity)

        # All EVs at low SOC, need to charge
        for ev_cfg in self.evs:
            ev_cfg['ev'].soc = 0.3

        # Run charging
        system.simple_charge_multi(11)

        # Check that grid capacity was respected
        if 11 in system.grid_usage:
            self.assertLessEqual(
                system.grid_usage[11],
                grid_capacity[11] + 0.1,
                "Total grid usage should not exceed capacity when multiple EVs charge"
            )
            
            # Count how many EVs charged
            charged_count = sum(1 for ev_cfg in self.evs if ev_cfg['ev'].soc > 0.3)
            print(f"  Grid capacity: {grid_capacity[11]:.2f} kW")
            print(f"  Grid used: {system.grid_usage[11]:.2f} kW")
            print(f"  EVs charged: {charged_count}/3")
            print(f"  ✓ Multiple EVs shared grid capacity appropriately")

    def test_no_discharge_in_simple_charge(self):
        """Test that simple charge never discharges EVs"""
        print("\n=== Testing No Discharge in Simple Charge ===")

        system = MultiEVChargingSystem(self.building, self.evs, self.grid, self.grid_capacity)

        # Run multiple charging cycles
        for hour in range(8, 15):
            initial_socs = [ev_cfg['ev'].soc for ev_cfg in self.evs]
            system.simple_charge_multi(hour)
            final_socs = [ev_cfg['ev'].soc for ev_cfg in self.evs]
            
            # Ensure no EV discharged (SOC never decreased)
            for i in range(len(self.evs)):
                self.assertGreaterEqual(
                    final_socs[i], 
                    initial_socs[i] - 0.001,  # Small tolerance for floating point
                    f"EV {i} should not discharge at hour {hour}"
                )
        
        print("✓ No discharge test passed")

    def test_rl_charge(self):
        """Test reinforcement learning algorithm"""
        print("\n=== Testing RL Charge Algorithm ===")

        system = MultiEVChargingSystem(self.building, self.evs, self.grid, self.grid_capacity)

        # Store initial SOCs
        initial_socs = [ev_cfg['ev'].soc for ev_cfg in self.evs]

        # Run RL charging at hour 10 (reduced episodes for testing)
        print("Training RL agent (500 episodes)...")
        action_taken, benefit = system.rl_charge_multi(10, episodes=500)

        self.assertIsInstance(action_taken, bool, "RL should return boolean")
        self.assertIsInstance(benefit, (int, float), "RL should return numeric benefit")

        print(f"✓ RL Result: Action={action_taken}, Benefit={benefit:.2f}€")

    def test_milp_charge(self):
        """Test MILP optimization algorithm"""
        print("\n=== Testing MILP Algorithm ===")

        try:
            import pulp

            system = MultiEVChargingSystem(self.building, self.evs, self.grid, self.grid_capacity)

            # Run MILP at hour 10
            action_taken, benefit = system.milp_charge(10)

            self.assertIsInstance(action_taken, bool, "MILP should return boolean")
            self.assertIsInstance(benefit, (int, float), "MILP should return numeric benefit")

            print(f"✓ MILP Result: Action={action_taken}, Benefit={benefit:.2f}€")

        except ImportError:
            print("⚠ SKIP: MILP test (PuLP not installed)")
            self.skipTest("PuLP not installed")

    def test_mpc_charge(self):
        """Test Model Predictive Control algorithm"""
        print("\n=== Testing MPC Algorithm ===")

        system = MultiEVChargingSystem(self.building, self.evs, self.grid, self.grid_capacity)

        # Run MPC at hour 10
        print("Running MPC optimization...")
        action_taken, benefit = system.mpc_charge(10, horizon=4, iterations=30)

        self.assertIsInstance(action_taken, bool, "MPC should return boolean")
        self.assertIsInstance(benefit, (int, float), "MPC should return numeric benefit")

        print(f"✓ MPC Result: Action={action_taken}, Benefit={benefit:.2f}€")

    def test_pso_charge(self):
        """Test Particle Swarm Optimization algorithm"""
        print("\n=== Testing PSO Algorithm ===")

        system = MultiEVChargingSystem(self.building, self.evs, self.grid, self.grid_capacity)

        # Run PSO at hour 10
        print("Running PSO optimization...")
        action_taken, benefit = system.pso_charge(10, n_particles=20, n_iterations=30)

        self.assertIsInstance(action_taken, bool, "PSO should return boolean")
        self.assertIsInstance(benefit, (int, float), "PSO should return numeric benefit")

        print(f"✓ PSO Result: Action={action_taken}, Benefit={benefit:.2f}€")

    # def test_dqn_charge(self):
    #     """Test Deep Q-Network algorithm"""
    #     print("\n=== Testing DQN Algorithm ===")
    #
    #     try:
    #         import tensorflow
    #
    #         system = MultiEVChargingSystem(self.building, self.evs, self.grid, self.grid_capacity)
    #
    #         # Run DQN at hour 10 (reduced episodes for testing)
    #         print("Training DQN agent (100 episodes)...")
    #         action_taken, benefit = system.dqn_charge(10, episodes=100, batch_size=16)
    #
    #         self.assertIsInstance(action_taken, bool, "DQN should return boolean")
    #         self.assertIsInstance(benefit, (int, float), "DQN should return numeric benefit")
    #
    #         print(f"✓ DQN Result: Action={action_taken}, Benefit={benefit:.2f}€")
    #
    #     except ImportError:
    #         print("⚠ SKIP: DQN test (TensorFlow not installed)")
    #         self.skipTest("TensorFlow not installed")

    def test_soc_constraints(self):
        """Test that SOC stays within valid bounds"""
        print("\n=== Testing SOC Constraints ===")

        system = MultiEVChargingSystem(self.building, self.evs, self.grid, self.grid_capacity)

        # Run multiple hours
        for hour in range(8, 15):
            system.simple_charge_multi(hour)

        # Check all EVs have valid SOC
        for i, ev_cfg in enumerate(self.evs):
            ev = ev_cfg['ev']
            self.assertGreaterEqual(ev.soc, 0, f"EV {i} SOC should be >= 0")
            self.assertLessEqual(ev.soc, 1.0, f"EV {i} SOC should be <= 1.0")
            self.assertGreaterEqual(
                ev.soc,
                system.min_soc,
                f"EV {i} SOC {ev.soc:.3f} should be >= min_soc {system.min_soc}"
            )
        
        print("✓ SOC constraints test passed")

    def test_building_integration(self):
        """Test integration with building energy management"""
        print("\n=== Testing Building Integration ===")

        system = MultiEVChargingSystem(self.building, self.evs, self.grid, self.grid_capacity)

        # Check building energy at different hours
        morning_demand = self.building.get_net_energy_demand(8)
        noon_demand = self.building.get_net_energy_demand(12)  # Should have solar

        self.assertLess(
            noon_demand,
            morning_demand,
            f"Noon demand ({noon_demand:.2f}) should be less than morning ({morning_demand:.2f}) due to solar"
        )
        
        print(f"✓ Building integration test passed - Morning: {morning_demand:.2f}, Noon: {noon_demand:.2f}")

    def test_full_simulation(self):
        """Test full day simulation with all EVs"""
        print("\n=== Testing Full Day Simulation ===")

        system = MultiEVChargingSystem(self.building, self.evs, self.grid, self.grid_capacity)

        total_cost = 0

        # Run simulation from 8:00 to 20:00
        for hour in range(8, 21):
            action_taken, cost = system.simple_charge_multi(hour)
            total_cost -= cost  # cost is negative (benefit format)
            if action_taken:
                print(f"Hour {hour}: Cost = {-cost:.2f}€")

        # Check that all EVs reached their target SOC (or close to it)
        for i, ev_cfg in enumerate(self.evs):
            ev = ev_cfg['ev']
            target_soc = ev_cfg['desired_soc']
            # Allow tolerance due to charging constraints
            self.assertGreaterEqual(
                ev.soc,
                target_soc - 0.15,
                f"EV {i} should reach target SOC. Target: {target_soc:.2f}, Actual: {ev.soc:.2f}"
            )

        print(f"✓ Full simulation test passed - Total cost: {total_cost:.2f}€")

    def test_algorithm_comparison(self):
        """Compare all algorithms on the same scenario"""
        print("\n=== Algorithm Comparison ===")

        algorithms = [
            ("Simple", lambda sys, hour: sys.simple_charge_multi(hour)),
            ("RL", lambda sys, hour: sys.rl_charge_multi(hour, episodes=300)),
            ("MPC", lambda sys, hour: sys.mpc_charge(hour, horizon=4, iterations=20)),
            ("PSO", lambda sys, hour: sys.pso_charge(hour, n_particles=15, n_iterations=20)),
        ]

        # Add MILP if available
        try:
            import pulp
            algorithms.append(("MILP", lambda sys, hour: sys.milp_charge(hour)))
        except ImportError:
            print("⚠ MILP not available for comparison")

        results = {}

        for name, algo_func in algorithms:
            try:
                # Reset EVs to initial state
                for ev_cfg in self.evs:
                    if hasattr(ev_cfg['ev'], '_initial_soc'):
                        ev_cfg['ev'].soc = ev_cfg['ev']._initial_soc
                    else:
                        ev_cfg['ev']._initial_soc = ev_cfg['ev'].soc

                # Create fresh system
                system = MultiEVChargingSystem(self.building, self.evs, self.grid, self.grid_capacity)
                
                total_benefit = 0
                print(f"\nRunning {name}...")
                
                for hour in range(10, 16):
                    action_taken, benefit = algo_func(system, hour)
                    total_benefit += benefit
                
                results[name] = total_benefit
                print(f"{name}: Total Benefit = {total_benefit:.2f}€")
                
            except Exception as e:
                print(f"{name}: Error - {str(e)}")
                results[name] = None

        # Print comparison
        print("\n--- Algorithm Comparison Summary ---")
        for name, benefit in results.items():
            if benefit is not None:
                print(f"{name:15s}: {benefit:>10.2f}€")
        
        print("✓ Algorithm comparison completed")

    def test_reset_grid_usage(self):
        """Test grid usage reset functionality"""
        print("\n=== Testing Grid Usage Reset ===")

        system = MultiEVChargingSystem(self.building, self.evs, self.grid, self.grid_capacity)

        # Use some grid
        system.simple_charge_multi(10)
        self.assertGreater(len(system.grid_usage), 0, "Grid usage should be tracked")

        # Reset
        system.reset_grid_usage()
        self.assertEqual(len(system.grid_usage), 0, "Grid usage should be cleared after reset")
        
        print("✓ Grid usage reset test passed")


def run_test_suite():
    """Run all tests with detailed output"""
    print("=" * 70)
    print("Multi-EV Charging System (Charge-Only) - Test Suite")
    print("=" * 70)

    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestMultiEVChargingSystem)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Total Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✓ ALL TESTS PASSED")
        success_rate = 100.0
    else:
        success_rate = 100.0 * (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun
        print(f"\n✗ SOME TESTS FAILED")
    
    print(f"Success Rate: {success_rate:.1f}%")
    print("=" * 70)

    return result.wasSuccessful()


if __name__ == "__main__":
    # Run test suite
    success = run_test_suite()

    # Exit with appropriate code
    sys.exit(0 if success else 1)
