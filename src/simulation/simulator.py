# src/simulation/simulator.py
from src.models.building import Building
from src.models.electric_vehicle import ElectricVehicle
from src.models.grid import Grid
from src.models.charging_system import ChargingSystem
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
    grid = Grid(config['price_profile'])
    charging_system = charging_system = ChargingSystem(building, ev, grid, config['desired_soc'], config['target_time'],
                                                       config['arrival_time'])
    results = {
        'simple_charge_results': [],
        'optimized_charge_results': [],
        'rl_charge_results': []
    }
    # Simulate over the available hours

    for hour in range(config['arrival_time'], config['target_time']):
        # Reset EV SoC for each method to ensure fair comparison
        ev.soc = config['ev_initial_soc']
        results['simple_charge_results'].append(charging_system.simple_charge(hour))
        ev.soc = config['ev_initial_soc']
        results['optimized_charge_results'].append(charging_system.cost_optimized_charge(hour))
        ev.soc = config['ev_initial_soc']
        results['rl_charge_results'].append(charging_system.rl_charge(hour))
    return results
