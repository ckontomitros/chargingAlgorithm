from src.models.building import Building
from src.models.electric_vehicle import ElectricVehicle
from src.models.grid import Grid
from src.models.v2g_charging_system import V2GChargingSystem  # Updated import
from src.utils.data_generator import load_consumption_profile


def run_simulation(config):
    building = Building(
        energy_consumption_profile=load_consumption_profile(config['consumption_file']),
        panel_area=config['panel_area'],
        panel_efficiency=config['panel_efficiency'],
        peak_solar_irradiance=config['peak_solar_irradiance'],
        battery_capacity=config['building_battery_capacity'],
        battery_efficiency=config['building_battery_efficiency'],
        initial_soc=config['building_initial_soc'],
        dod=config['building_dod'],
        duration=config['duration']
    )
    ev = ElectricVehicle(
        battery_capacity=config['ev_battery_capacity'],
        initial_soc=config['ev_initial_soc'],
        energy_per_km=config['energy_per_km'],
        max_charge_rate=config['max_charge_rate'],
        max_discharge_rate=config['max_discharge_rate'],
        usage_stats=config['usage_stats'],
        dod=config['ev_dod'],
        duration=config['duration']
    )
    grid = Grid(config['price_profile'], config.get('sell_price_profile'))  # Pass sell_price_profile
    charging_system = V2GChargingSystem(
        building, ev, grid, config['desired_soc'], config['target_time'],
        config['arrival_time'], min_soc=config.get('min_soc', 0.2)
    )
    results = {
        'simple_charge_results': [],
        'optimized_charge_results': [],
        'rl_charge_results': [],
        'ev_soc': [],  # Track EV SoC
        'building_soc': [],  # Track building battery SoC
        'net_cost': {'simple': 0, 'optimized': 0, 'rl': 0}  # Track net cost/benefit
    }

    for hour in range(config['arrival_time'], config['target_time']):
        # Reset EV and building SoC for each method to ensure fair comparison
        ev.soc = config['ev_initial_soc']
        building.soc = config['building_initial_soc']

        # Simple charge (no V2G)
        action, cost = charging_system.simple_charge(hour)
        results['simple_charge_results'].append((action, cost))
        results['net_cost']['simple'] += cost
        results['ev_soc'].append(ev.soc)
        results['building_soc'].append(building.soc)

        # Reset for optimized charge
        ev.soc = config['ev_initial_soc']
        building.soc = config['building_initial_soc']
        action, cost = charging_system.cost_optimized_charge(hour)
        results['optimized_charge_results'].append((action, cost))
        results['net_cost']['optimized'] += cost  # Cost is positive for charging, negative for discharging
        results['ev_soc'].append(ev.soc)
        results['building_soc'].append(building.soc)

        # Reset for RL charge
        ev.soc = config['ev_initial_soc']
        building.soc = config['building_initial_soc']
        action, cost = charging_system.rl_charge(hour)
        results['rl_charge_results'].append((action, cost))
        results['net_cost']['rl'] += cost
        results['ev_soc'].append(ev.soc)
        results['building_soc'].append(building.soc)

    return results