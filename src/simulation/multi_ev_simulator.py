# src/simulation/multi_ev_simulator.py
import os
import random
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
from src.models.building import Building
from src.models.electric_vehicle import ElectricVehicle
from src.models.grid import Grid
from src.models.multi_ev_charging_system import MultiEVChargingSystem
from src.utils.data_generator import load_consumption_profile, load_irradiance_pvgis


def random_ev_config(idx: int, cfg: dict, duration: int):
    """Generate a random EV configuration from config ranges."""
    arrival = random.randint(cfg['ev_arrival_window'][0],
                             cfg['ev_arrival_window'][1])
    max_target = min(cfg['ev_target_window'][1], duration - 1)
    target = random.randint(cfg['ev_target_window'][0], max_target)

    return {
        'ev': ElectricVehicle(
            battery_capacity=cfg['ev_battery_capacity'],
            initial_soc=random.uniform(*cfg['ev_initial_soc_range']),
            energy_per_km=cfg['energy_per_km'],
            max_charge_rate=cfg['max_charge_rate'],
            max_discharge_rate=cfg['max_discharge_rate'],
            usage_stats=cfg.get('usage_stats'),
            dod=cfg['ev_dod'],
            duration=duration,
        ),
        'desired_soc': random.uniform(*cfg['ev_desired_soc_range']),
        'arrival_time': arrival,
        'target_time': target,
    }


def run_multi_ev_simulation(cfg: dict):
    """Main entry point - runs the whole multi-EV experiment (charge-only)."""
    duration = cfg['duration']

    # ------------------------------------------------------------------ #
    # 1. Convert list -> dict for grid capacity
    # ------------------------------------------------------------------ #
    if isinstance(cfg['grid_capacity_per_hour'], list):
        cfg['grid_capacity_per_hour'] = {
            h: cfg['grid_capacity_per_hour'][h] for h in range(24)
        }

    # ------------------------------------------------------------------ #
    # 2. Build shared environment
    # ------------------------------------------------------------------ #
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    consumption_file = cfg['consumption_file']
    if not os.path.isabs(consumption_file):
        if not os.path.exists(consumption_file):
            consumption_file = os.path.join(project_root, consumption_file)

    # Load irradiance data from PVGIS if specified
    irradiance_profile = None
    if cfg.get('irradiance_file') and cfg.get('irradiance_date'):
        irradiance_file = cfg['irradiance_file']
        if not os.path.isabs(irradiance_file):
            if not os.path.exists(irradiance_file):
                irradiance_file = os.path.join(project_root, irradiance_file)

        irradiance_profile = load_irradiance_pvgis(irradiance_file, cfg['irradiance_date'])
        print(f"Loaded PVGIS irradiance data for date: {cfg['irradiance_date']}")
        print(f"   Peak irradiance: {max(irradiance_profile):.1f} W/m2")

    building = Building(
        energy_consumption_profile=load_consumption_profile(consumption_file),
        panel_area=cfg['panel_area'],
        panel_efficiency=cfg['panel_efficiency'],
        peak_solar_irradiance=cfg['peak_solar_irradiance'],
        battery_capacity=cfg['building_battery_capacity'],
        battery_efficiency=cfg['building_battery_efficiency'],
        initial_soc=cfg['building_initial_soc'],
        dod=cfg['building_dod'],
        max_charge_rate=cfg.get('building_max_charge_rate'),
        max_discharge_rate=cfg.get('building_max_discharge_rate'),
        irradiance_profile=irradiance_profile
    )

    # Price profile: list -> dict
    if isinstance(cfg['price_profile'], list):
        cfg['price_profile'] = {h: cfg['price_profile'][h] for h in range(24)}

    grid = Grid(price_profile=cfg['price_profile'])

    # ------------------------------------------------------------------ #
    # 3. Generate EV fleet
    # ------------------------------------------------------------------ #
    evs = [random_ev_config(i, cfg, duration) for i in range(cfg['n_evs'])]

    # ------------------------------------------------------------------ #
    # 4. Charging system
    # ------------------------------------------------------------------ #
    system = MultiEVChargingSystem(
        building=building,
        evs=evs,
        grid=grid,
        grid_capacity_per_hour=cfg['grid_capacity_per_hour'],
        min_soc=cfg.get('min_soc', 0.2)
    )

    # ------------------------------------------------------------------ #
    # 5. Define algorithms
    # ------------------------------------------------------------------ #
    methods = {
        'simple': system.simple_charge_multi,
        'rl': lambda h: system.rl_charge_multi(
            h,
            episodes=cfg.get('rl_episodes', 8000),
            learning_rate=cfg.get('rl_lr', 0.1),
            discount_factor=cfg.get('rl_gamma', 1),
            epsilon=cfg.get('rl_epsilon', 0.25)
        ),
    }

    # ------------------------------------------------------------------ #
    # 6. Run simulation over time
    # ------------------------------------------------------------------ #
    results = {name: defaultdict(list) for name in methods}
    results['hours'] = []

    start_hour = cfg.get('simulation_start', 0)
    last_ev_departure = max(ev_cfg['target_time'] for ev_cfg in evs)
    end_hour = min(cfg.get('simulation_end', duration - 1), last_ev_departure)

    # Track building consumption for display
    results['building_consumption'] = []
    results['building_solar'] = []

    for hour in range(start_hour, end_hour + 1):
        results['hours'].append(hour)

        building_consumption = building.energy_consumption_profile[hour % len(building.energy_consumption_profile)]
        building_solar = building.renewable_energy_profile[hour % len(building.renewable_energy_profile)]
        results['building_consumption'].append(building_consumption)
        results['building_solar'].append(building_solar)

        for name, func in methods.items():
            # Reset system for each method to avoid interference
            system.reset_grid_usage()

            # Restore EV states from previous hour
            for i, ev_cfg in enumerate(evs):
                if results[name]['ev_soc']:
                    ev_cfg['ev'].soc = results[name]['ev_soc'][-1][i]
                else:
                    ev_cfg['ev'].soc = ev_cfg['ev'].soc

            acted, benefit = func(hour)
            results[name]['acted'].append(acted)
            results[name]['benefit'].append(benefit)
            results[name]['grid_usage'].append(system.grid_usage[hour])
            results[name]['ev_soc'].append([ev_cfg['ev'].soc for ev_cfg in evs])

    # ------------------------------------------------------------------ #
    # 7. Visualize + Summary
    # ------------------------------------------------------------------ #
    visualise_multi_ev(results, cfg, evs, system)
    summarise_multi_ev(results, cfg, system)

    return results


# ---------------------------------------------------------------------- #
# Visualisation
# ---------------------------------------------------------------------- #
def visualise_multi_ev(results: dict, cfg: dict, evs: list, system):
    """Visualize multi-EV simulation results."""
    hours = results['hours']

    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(4, 1, height_ratios=[2, 1.2, 1, 1], hspace=0.4)

    colors = {
        'simple': '#1f77b4',
        'rl': '#ff7f0e',
    }

    # 1. EV SoC with range bands
    ax1 = fig.add_subplot(gs[0])
    for name, color in colors.items():
        if name not in results:
            continue
        socs = np.array(results[name]['ev_soc'])
        avg = socs.mean(axis=1)
        low, high = socs.min(axis=1), socs.max(axis=1)
        ax1.plot(hours, avg, label=f'{name.upper()} (avg)', color=color, lw=2.5)
        ax1.fill_between(hours, low, high, color=color, alpha=0.15)

    avg_target = np.mean([ev['desired_soc'] for ev in evs])
    ax1.axhline(y=avg_target, color='green', linestyle='--', lw=2,
                label=f'Avg Target SoC ({avg_target:.0%})', alpha=0.7)
    ax1.axhline(y=cfg.get('min_soc', 0.2), color='red', linestyle=':', lw=2,
                label=f'Min SoC ({cfg.get("min_soc", 0.2):.0%})', alpha=0.7)

    ax1.set_ylabel('EV SoC', fontsize=12)
    ax1.set_title('EV Fleet State-of-Charge (Charge-Only)', fontsize=14, fontweight='bold')
    ax1.legend(loc='best', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, 1)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))

    # 2. Grid usage vs capacity (Total = Building net + EV charging)
    ax2 = fig.add_subplot(gs[1])
    capacity = [cfg['grid_capacity_per_hour'].get(h, float('inf')) for h in hours]

    building_net = [max(0, results['building_consumption'][i] - results['building_solar'][i])
                    for i in range(len(hours))]

    ax2.fill_between(hours, 0, building_net, alpha=0.3, color='gray', label='Building Net')

    for name, color in colors.items():
        if name not in results or 'grid_usage' not in results[name]:
            continue
        ev_usage = results[name]['grid_usage']
        total_usage = [building_net[i] + ev_usage[i] for i in range(len(hours))]
        ax2.plot(hours, total_usage, label=f'{name.upper()} (Total)', color=color,
                 marker='o', markersize=4, lw=2)
        ax2.plot(hours, ev_usage, label=f'{name.upper()} (EV only)', color=color,
                 linestyle=':', lw=1.5, alpha=0.7)

    ax2.plot(hours, capacity, 'k--', lw=2.5, label='Grid Capacity', alpha=0.8)
    ax2.set_ylabel('Grid Power (kW)', fontsize=12)
    ax2.set_title('Hourly Grid Consumption (Building + EV Charging)', fontsize=14, fontweight='bold')
    ax2.legend(loc='upper right', fontsize=8, ncol=2)
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(bottom=0)

    # 3. Hourly benefit comparison
    ax3 = fig.add_subplot(gs[2])
    x = np.arange(len(hours))
    width = 0.2

    for i, (name, color) in enumerate(colors.items()):
        if name not in results:
            continue
        offset = width * (i - 0.5)
        ax3.bar(x + offset, results[name]['benefit'], width,
                label=name.upper(), color=color, alpha=0.8)

    ax3.set_xlabel('Hour of Day', fontsize=12)
    ax3.set_ylabel('Hourly Benefit (EUR)', fontsize=12)
    ax3.set_title('Hourly Financial Benefit (Negative = Cost)',
                  fontsize=14, fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(hours)
    ax3.legend(loc='best', fontsize=10)
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.8)

    # 4. Cumulative benefit
    ax4 = fig.add_subplot(gs[3])
    for name, color in colors.items():
        if name not in results:
            continue
        cum = np.cumsum(results[name]['benefit'])
        ax4.plot(hours, cum, label=f'{name.upper()}', color=color, lw=2.5,
                 marker='o', markersize=5)

    ax4.set_xlabel('Hour of Day', fontsize=12)
    ax4.set_ylabel('Cumulative Benefit (EUR)', fontsize=12)
    ax4.set_title('Cumulative Financial Benefit Over Time', fontsize=14, fontweight='bold')
    ax4.legend(loc='best', fontsize=10)
    ax4.grid(True, alpha=0.3)
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.8)

    plt.suptitle('Multi-EV Charging Simulation - Grid Capacity Aware (Charge-Only)',
                 fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout(rect=[0, 0, 1, 0.99])
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               '..', '..', 'scripts', 'simulation_results_multi.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nVisualization saved as '{output_path}'")
    plt.close()


# ---------------------------------------------------------------------- #
# Summary table
# ---------------------------------------------------------------------- #
def summarise_multi_ev(results: dict, cfg: dict, system):
    """Print summary statistics for multi-EV simulation."""
    print("\n" + "=" * 90)
    print("MULTI-EV SIMULATION SUMMARY (CHARGE-ONLY)")
    print("=" * 90)
    print(f"{'Method':<8} {'Total Benefit (EUR)':>18} {'Final Avg SoC':>16} "
          f"{'Grid Violations':>18} {'SoC Violations':>16}")
    print("-" * 90)

    for name in ['simple', 'rl']:
        if name not in results:
            continue

        benefit = sum(results[name]['benefit'])
        socs = np.array(results[name]['ev_soc'])
        avg_final = socs[-1].mean()

        grid_violations = sum(
            1 for i, h in enumerate(results['hours'])
            if results[name]['grid_usage'][i] > cfg['grid_capacity_per_hour'].get(h, float('inf'))
        )

        min_soc = cfg.get('min_soc', 0.2)
        soc_violations = sum(
            1 for soc_array in socs
            for soc in soc_array
            if soc < min_soc
        )

        print(f"{name.upper():<8} {benefit:>18.2f} {avg_final:>16.1%} "
              f"{grid_violations:>18} {soc_violations:>16}")

    print("=" * 90)

    print(f"\nSimulation Parameters:")
    print(f"  - Number of EVs: {cfg['n_evs']}")
    print(f"  - Simulation window: Hour {cfg.get('simulation_start', 0)} to {cfg.get('simulation_end', 23)}")
    print(f"  - EV arrival window: {cfg['ev_arrival_window']}")
    print(f"  - EV target window: {cfg['ev_target_window']}")
    print(f"  - Grid capacity range: "
          f"{min(cfg['grid_capacity_per_hour'].values())}-{max(cfg['grid_capacity_per_hour'].values())} kW")
    print("=" * 90)
