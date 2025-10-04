import unittest
from src.models.v2g_charging_system import V2GChargingSystem  # Updated import
from src.models.building import Building
from src.models.electric_vehicle import ElectricVehicle
from src.models.grid import Grid


class TestChargingSystem(unittest.TestCase):
    def setUp(self):
        # Common setup based on config.yml
        self.battery_capacity = 60  # kWh
        self.max_charge_rate = 7  # kW
        self.max_discharge_rate = 7  # kW
        self.price_profile = [0.15, 0.12, 0.10, 0.10, 0.12]  # €/kWh for 5 hours
        self.sell_price_profile = [p * 0.8 for p in self.price_profile]  # 80% of buy price
        self.consumption_profile = [10] * 24  # kWh, constant consumption
        self.panel_area = 50  # m²
        self.panel_efficiency = 0.2
        self.peak_solar_irradiance = 800  # W/m²
        self.building_battery_capacity = 50  # kWh
        self.building_battery_efficiency = 0.9
        self.building_initial_soc = 0.5
        self.building_dod = 0.8
        self.duration = 5
        self.ev_initial_soc = 0.5
        self.ev_dod = 0.8
        self.energy_per_km = 0.2
        self.usage_stats = {'departure': 8, 'arrival': 18, 'daily_km': 50}
        self.desired_soc = 0.8
        self.target_time = 12
        self.arrival_time = 8
        self.min_soc = 0.2

    def create_charging_system(self, initial_soc=None, arrival_time=None, target_time=None,
                             price_profile=None, sell_price_profile=None, renewable_profile=None):
        """Helper to create V2GChargingSystem instance with customizable parameters."""
        initial_soc = initial_soc if initial_soc is not None else self.ev_initial_soc
        arrival_time = arrival_time if arrival_time is not None else self.arrival_time
        target_time = target_time if target_time is not None else self.target_time
        price_profile = price_profile if price_profile is not None else self.price_profile
        sell_price_profile = sell_price_profile if sell_price_profile is not None else self.sell_price_profile
        building = Building(
            energy_consumption_profile=self.consumption_profile,
            panel_area=self.panel_area,
            panel_efficiency=self.panel_efficiency,
            peak_solar_irradiance=self.peak_solar_irradiance,
            battery_capacity=self.building_battery_capacity,
            battery_efficiency=self.building_battery_efficiency,
            initial_soc=self.building_initial_soc,
            dod=self.building_dod,
            duration=self.duration
        )
        if renewable_profile is not None:
            building.renewable_energy_profile = renewable_profile
        ev = ElectricVehicle(
            battery_capacity=self.battery_capacity,
            initial_soc=initial_soc,
            energy_per_km=self.energy_per_km,
            max_charge_rate=self.max_charge_rate,
            max_discharge_rate=self.max_discharge_rate,
            usage_stats=self.usage_stats,
            dod=self.ev_dod,
            duration=self.duration
        )
        grid = Grid(price_profile, sell_price_profile)
        return V2GChargingSystem(building, ev, grid, self.desired_soc, target_time, arrival_time, self.min_soc)

    def test_simple_charge_before_arrival(self):
        charger = self.create_charging_system()
        should_charge, cost = charger.simple_charge(hour=7)
        self.assertFalse(should_charge)
        self.assertEqual(cost, 0)
        self.assertEqual(charger.ev.soc, 0.5)  # SoC unchanged

    def test_simple_charge_at_arrival(self):
        charger = self.create_charging_system()
        should_charge, cost = charger.simple_charge(hour=10)
        self.assertTrue(should_charge)
        self.assertAlmostEqual(cost, 7 * 0.15)  # 7 kWh * 0.15 €/kWh
        self.assertAlmostEqual(charger.ev.soc, 0.5 + 7 / 60)  # SoC updated

    def test_simple_charge_soc_reached(self):
        charger = self.create_charging_system(initial_soc=0.8)
        should_charge, cost = charger.simple_charge(hour=8)
        self.assertFalse(should_charge)
        self.assertEqual(cost, 0)
        self.assertEqual(charger.ev.soc, 0.8)  # SoC unchanged

    def test_simple_charge_multiple_hours(self):
        charger = self.create_charging_system(initial_soc=0.3)
        total_cost = 0
        for hour in range(8, 12):
            should_charge, cost = charger.simple_charge(hour)
            self.assertTrue(should_charge)
            total_cost += cost
        self.assertGreaterEqual(charger.ev.soc, 0.766)  # Should approach desired SoC
        expected_energy = (0.8 - 0.3) * 60  # 30 kWh needed
        expected_cost = 7 * 0.1 + 7 * 0.12 + 7 * 0.15 + 7 * 0.12  # First 4 hours
        self.assertAlmostEqual(total_cost, expected_cost, places=5)

    def test_rl_charge_low_price_hour(self):
        charger = self.create_charging_system()
        should_act, cost = charger.rl_charge(hour=8, episodes=1000)  # Hour 8: 0.10 €/kWh
        self.assertTrue(should_act)  # RL should prefer low-price hour
        self.assertAlmostEqual(cost, 7 * 0.10, places=2)
        self.assertAlmostEqual(charger.ev.soc, 0.5 + 7 / 60)

    def test_rl_charge_discharge_high_price(self):
        charger = self.create_charging_system(initial_soc=0.8)
        should_act, cost = charger.rl_charge(hour=9, episodes=100)  # Hour 9: 0.12 €/kWh (sell price 0.096)
        self.assertTrue(should_act)
        self.assertLess(cost, 0)  # Negative cost for discharge
        self.assertAlmostEqual(cost, -7 * 0.096, places=1)  # Approximate due to RL variability
        self.assertAlmostEqual(charger.ev.soc, 0.8 - (7 / 0.9) / 60, places=2)
        self.assertGreater(charger.building.soc, 0.5)  # Building battery should charge

    def test_rl_charge_short_window(self):
        charger = self.create_charging_system(arrival_time=11, target_time=12)
        should_act, cost = charger.rl_charge(hour=11, episodes=100)
        self.assertTrue(should_act)  # Must charge in only available hour
        self.assertAlmostEqual(cost, 7 * 0.12, places=2)
        self.assertAlmostEqual(charger.ev.soc, 0.5 + 7 / 60)

    def test_rl_charge_with_renewables(self):
        renewable_profile = [0, 0, 20, 20, 0]  # High renewable energy at hours 2 and 3
        charger = self.create_charging_system(renewable_profile=renewable_profile)
        should_act, cost = charger.rl_charge(hour=8, episodes=100)  # Hour 8: 0.10 €/kWh, 20 kWh renewable
        self.assertTrue(should_act)
        self.assertAlmostEqual(cost, 0, places=2)  # No grid cost due to renewables
        self.assertAlmostEqual(charger.ev.soc, 0.5 + 7 / 60)


if __name__ == '__main__':
    unittest.main()