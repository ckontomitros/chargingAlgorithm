# src/simulation/multi_ev_simulator.py
import random
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
from src.models.building import Building
from src.models.electric_vehicle import ElectricVehicle
from src.models.grid import Grid
from src.models.multi_ev_charging_system import MultiEVChargingSystem
from src.utils.data_generator import load_consumption_profile


def random_ev_config(idx: int, cfg: dict, duration: int):
    """Generate a random EV configuration."""
    arrival = random.randint(cfg['ev_arrival_window'][0],
                             cfg['ev_arrival_window'][1])
    # stay at least 2 h, at most the full window
    stay = random.randint(2, cfg['ev_target_window'][1] - arrival)
    target = arrival + stay

    return {
        'ev': ElectricVehicle(
            battery_capacity=cfg['ev_battery_capacity'],
            initial_soc=random.uniform(cfg['ev_initial_soc'][0],
                                       cfg['ev_initial_soc'][1]),
            energy_per_km=cfg['energy_per_km'],
            max_charge_rate=cfg['max_charge_rate'],
            max_discharge_rate=cfg['max_discharge_rate'],
            usage_stats=cfg['usage_stats'],
            dod=cfg['ev_dod'],
            duration=duration,
        ),
        'desired_soc': random.uniform(cfg['desired_soc'][0],
                                      cfg['desired_soc'][1]),
        'arrival_time': arrival,
        'target_time': target,
    }


def run_multi_ev_simulation(cfg: dict):
    """Main entry point – runs the whole multi-EV experiment."""
    # ------------------------------------------------------------------ #
    # 1. Build the shared environment (building, solar, grid)
    # ------------------------------------------------------------------ #
    building = Building(
        energy_consumption_profile=load_consumption_profile(cfg['consumption_file']),
        panel_area=cfg['panel_area'],
        panel_efficiency=cfg['panel_efficiency'],
        peak_solar_irradiance=cfg['peak_solar_irradiance'],
        battery_capacity=cfg['building_battery_capacity'],
        battery_efficiency=cfg['building_battery_efficiency'],
        initial_soc=cfg['building_initial_soc'],
        dod=cfg['building_dod'],
        duration=cfg['duration']
    )

    grid = Grid(price_profile=cfg['price_profile'])

    # ------------------------------------------------------------------ #
    # 2. Create the fleet of EVs
    # ------------------------------------------------------------------ #
    evs = [random_ev_config(i, cfg, cfg['duration']) for i in range(cfg['n_evs'])]

    # ------------------------------------------------------------------ #
    # 3. Prepare the charging system (charge-only, no V2G)
    # ------------------------------------------------------------------ #
    system = MultiEVChargingSystem(
        building=building,
        evs=evs,
        grid=grid,
        grid_capacity_per_hour=cfg['grid_capacity_per_hour'],
        min_soc=cfg.get('min_soc', 0.2)
    )

    # ------------------------------------------------------------------ #
    # 4. Run each algorithm over the whole day
    # ------------------------------------------------------------------ #
    methods = {
        'simple': system.simple_charge_multi,
        'rl'    : lambda h: system.rl_charge_multi(h,
                     episodes=cfg['rl_episodes'],
                     learning_rate=cfg['rl_lr'],
                     discount_factor=cfg['rl_gamma'],
                     epsilon=cfg['rl_epsilon']),
        'milp'  : system.milp_charge,
        'pso'   : lambda h: system.pso_charge(h,
                     n_particles=cfg['pso_particles'],
                     n_iterations=cfg['pso_iters'],
                     w=cfg['pso_w'],
                     c1=cfg['pso_c1'],
                     c2=cfg['pso_c2'])
    }

    results = {name: defaultdict(list) for name in methods}
    results['hours'] = []

    # Reset grid usage at the start of the day
    system.reset_grid_usage()

    for hour in range(cfg['simulation_start'], cfg['simulation_end'] + 1):
        results['hours'].append(hour)

        for name, func in methods.items():
            acted, benefit = func(hour)
            results[name]['acted'].append(acted)
            results[name]['benefit'].append(benefit)   # negative cost = benefit
            # store per-EV SoC for visualisation
            results[name]['ev_soc'].append([ev_cfg['ev'].soc for ev_cfg in evs])

    # ------------------------------------------------------------------ #
    # 5. Visualise & summarise
    # ------------------------------------------------------------------ #
    visualise_multi_ev(results, cfg, evs)
    summarise_multi_ev(results, cfg)

    return results


# ---------------------------------------------------------------------- #
# 6. Visualisation
# ---------------------------------------------------------------------- #
def visualise_multi_ev(results: dict, cfg: dict, evs: list):
    hours = results['hours']
    n_evs = cfg['n_evs']

    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(3, 1, height_ratios=[2, 1.2, 1], hspace=0.35)

    # ---------- 1. EV SoC (average + min/max envelope) ----------
    ax1 = fig.add_subplot(gs[0])
    for name, color in zip(['simple', 'rl', 'milp', 'pso'],
                           ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']):
        socs = np.array(results[name]['ev_soc'])               # (T, N)
        avg = socs.mean(axis=1)
        low = socs.min(axis=1)
        high = socs.max(axis=1)

        ax1.plot(hours, avg, label=f'{name.upper()} (avg)', color=color, lw=2)
        ax1.fill_between(hours, low, high, color=color, alpha=0.15)

    ax1.set_ylabel('EV SoC')
    ax1.set_title('EV Fleet State-of-Charge')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, 1)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))

    # ---------- 2. Grid usage ----------
    ax2 = fig.add_subplot(gs[1])
    capacity = [cfg['grid_capacity_per_hour'].get(h, float('inf')) for h in hours]

    for name, color in zip(['simple', 'rl', 'milp', 'pso'],
                           ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']):
        usage = [system.grid_usage.get(h, 0) for h in hours]
        ax2.plot(hours, usage, label=name.upper(), color=color, marker='o', markersize=4)

    ax2.plot(hours, capacity, 'k--', lw=2, label='Capacity')
    ax2.set_ylabel('Grid Power (kW)')
    ax2.set_title('Hourly Grid Consumption')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # ---------- 3. Cumulative benefit (negative cost) ----------
    ax3 = fig.add_subplot(gs[2])
    for name, color in zip(['simple', 'rl', 'milp', 'pso'],
                           ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']):
        cum = np.cumsum(results[name]['benefit'])
        ax3.plot(hours, cum, label=f'{name.upper()}', color=color, lw=2)

    ax3.set_xlabel('Hour of Day')
    ax3.set_ylabel('Cumulative Benefit (€)')
    ax3.set_title('Cumulative Financial Benefit')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    plt.suptitle('Multi-EV Charging Simulation – Grid-Capacity-Aware', fontsize=16, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig('scripts/simulation_results_multi.png', dpi=300, bbox_inches='tight')
    plt.show()


# ---------------------------------------------------------------------- #
# 7. Summary table
# ---------------------------------------------------------------------- #
def summarise_multi_ev(results: dict, cfg: dict):
    print("\n" + "="*80)
    print("MULTI-EV SIMULATION SUMMARY")
    print("="*80)
    print(f"{'Method':<8} {'Total Benefit (€)':>18} {'Final Avg SoC':>16} {'Grid Violations':>18}")
    print("-"*80)

    for name in ['simple', 'rl', 'milp', 'pso']:
        benefit = sum(results[name]['benefit'])
        socs = np.array(results[name]['ev_soc'])
        avg_final = socs[-1].mean()
        # count hours where usage > capacity
        violations = sum(
            1 for h in results['hours']
            if system.grid_usage.get(h, 0) > cfg['grid_capacity_per_hour'].get(h, float('inf'))
        )
        print(f"{name.upper():<8} {benefit:>18.2f} {avg_final:>16.1%} {violations:>18}")

    print("="*80)


# ---------------------------------------------------------------------- #
# 8. Example configuration (put this in data/config.yml or pass a dict)
# ---------------------------------------------------------------------- #
EXAMPLE_CONFIG = {
    # ----- Environment -----
    'consumption_file': '../data/consumption_profiles.csv',
    'panel_area': 150.0,
    'panel_efficiency': 0.20,
    'peak_solar_irradiance': 1000.0,
    'building_battery_capacity': 50.0,
    'building_battery_efficiency': 0.95,
    'building_initial_soc': 0.5,
    'building_dod': 0.8,
    'duration': 24,

    # ----- Grid -----
    'price_profile': {h: 0.12 if 7 <= h <= 22 else 0.08 for h in range(24)},
    'grid_capacity_per_hour': {h: 30.0 for h in range(24)},   # 30 kW max per hour

    # ----- EVs -----
    'n_evs': 12,
    'ev_battery_capacity': 60.0,
    'ev_initial_soc': [0.2, 0.5],
    'energy_per_km': 0.18,
    'max_charge_rate': 11.0,
    'max_discharge_rate': 11.0,
    'usage_stats': None,
    'ev_dod': 0.9,
    'desired_soc': [0.8, 0.95],
    'ev_arrival_window': [6, 10],
    'ev_target_window': [14, 22],

    # ----- Simulation window -----
    'simulation_start': 0,
    'simulation_end': 23,

    # ----- Algorithm hyper-parameters -----
    'min_soc': 0.2,
    'rl_episodes': 1500,
    'rl_lr': 0.08,
    'rl_gamma': 0.96,
    'rl_epsilon': 0.12,
    'pso_particles': 40,
    'pso_iters': 60,
    'pso_w': 0.72,
    'pso_c1': 1.49,
    'pso_c2': 1.49,
}

if __name__ == '__main__':
    # You can replace EXAMPLE_CONFIG with yaml-loaded dict in production
    run_multi_ev_simulation(EXAMPLE_CONFIG)