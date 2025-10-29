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
    """Generate a random EV configuration from config ranges."""
    arrival = random.randint(cfg['ev_arrival_window'][0],
                             cfg['ev_arrival_window'][1])
    # ensure target_time > arrival + 1
    max_target = min(cfg['ev_target_window'][1], duration - 1)
    target = random.randint(arrival + 2, max_target)

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
    """Main entry point – runs the whole multi-EV experiment."""
    duration = cfg['duration']

    # ------------------------------------------------------------------ #
    # 1. Convert list → dict for grid capacity
    # ------------------------------------------------------------------ #
    if isinstance(cfg['grid_capacity_per_hour'], list):
        cfg['grid_capacity_per_hour'] = {
            h: cfg['grid_capacity_per_hour'][h] for h in range(24)
        }

    # ------------------------------------------------------------------ #
    # 2. Build shared environment
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
        duration=duration
    )

    # Price profile: list → dict
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
            episodes=cfg.get('rl_episodes', 1500),
            learning_rate=cfg.get('rl_lr', 0.1),
            discount_factor=cfg.get('rl_gamma', 0.95),
            epsilon=cfg.get('rl_epsilon', 0.15)
        ),

        'pso': lambda h: system.pso_charge(
            h,
            n_particles=cfg.get('pso_particles', 40),
            n_iterations=cfg.get('pso_iters', 60),
            w=cfg.get('pso_w', 0.7),
            c1=cfg.get('pso_c1', 1.5),
            c2=cfg.get('pso_c2', 1.5)
        )
    }

    # ------------------------------------------------------------------ #
    # 6. Run simulation over time
    # ------------------------------------------------------------------ #
    results = {name: defaultdict(list) for name in methods}
    results['hours'] = []

    start_hour = cfg.get('simulation_start', 0)
    end_hour = cfg.get('simulation_end', duration - 1)

    system.reset_grid_usage()

    # In run_multi_ev_simulation, modify the simulation loop:
    for hour in range(start_hour, end_hour + 1):
        results['hours'].append(hour)

        for name, func in methods.items():
            # Create a copy of system for this method (to avoid state interference)

            # Copy EV states from previous hour
            for i, ev_cfg in enumerate(evs):
                ev_cfg['ev'].soc = results[name]['ev_soc'][-1][i] if results[name]['ev_soc'] else ev_cfg[
                    'ev'].soc

            acted, benefit = func(hour)
            results[name]['acted'].append(acted)
            results[name]['benefit'].append(benefit)

            # Track grid usage for THIS method
            results[name]['grid_usage'].append(system.grid_usage[hour])

            # Store SoC
            results[name]['ev_soc'].append([ev_cfg['ev'].soc for ev_cfg in evs])
            results[name]['ev_soc'][-1] = [ev_cfg['ev'].soc for ev_cfg in evs]
            system.reset_grid_usage()

    # ------------------------------------------------------------------ #
    # 7. Visualize + Summ  # (unchanged)
    # ------------------------------------------------------------------ #
    visualise_multi_ev(results, cfg, evs, system)
    summarise_multi_ev(results, cfg, system)

    return results


# ---------------------------------------------------------------------- #
# 6. Visualisation (updated to use system.grid_usage)
# ---------------------------------------------------------------------- #
def visualise_multi_ev(results: dict, cfg: dict, evs: list, system):
    hours = results['hours']

    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(3, 1, height_ratios=[2, 1.2, 1], hspace=0.35)

    # 1. EV SoC
    ax1 = fig.add_subplot(gs[0])
    for name, color in zip(['simple', 'rl',  'pso'],
                           ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']):
        socs = np.array(results[name]['ev_soc'])
        avg = socs.mean(axis=1)
        low, high = socs.min(axis=1), socs.max(axis=1)
        ax1.plot(hours, avg, label=f'{name.upper()} (avg)', color=color, lw=2)
        ax1.fill_between(hours, low, high, color=color, alpha=0.15)
    ax1.set_ylabel('EV SoC')
    ax1.set_title('EV Fleet State-of-Charge')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, 1)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))

    # ---------- 2. Grid usage (FIXED) ----------
    ax2 = fig.add_subplot(gs[1])
    capacity = [cfg['grid_capacity_per_hour'].get(h, float('inf')) for h in hours]

    # Track grid usage PER METHOD during simulation
    for name, color in zip(['simple', 'rl', 'pso'],
                           ['#1f77b4', '#ff7f0e', '#2ca02c']):
        # Store usage in results during simulation
        if 'grid_usage' in results[name]:
            usage = results[name]['grid_usage']
        else:
            usage = [0] * len(hours)  # fallback if not tracked

        ax2.plot(hours, usage, label=name.upper(), color=color, marker='o', markersize=4)

    ax2.plot(hours, capacity, 'k--', lw=2, label='Capacity')
    ax2.set_ylabel('Grid Power (kW)')
    ax2.set_title('Hourly Grid Consumption')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. Cumulative benefit
    ax3 = fig.add_subplot(gs[2])
    for name, color in zip(['simple', 'rl', 'pso'],
                           ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']):
        cum = np.cumsum(results[name]['benefit'])
        ax3.plot(hours, cum, label=f'{name.upper()}', color=color, lw=2)
    ax3.set_xlabel('Hour of Day')
    ax3.set_ylabel('Cumulative Benefit (€)')
    ax3.set_title('Cumulative Financial Benefit')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    plt.suptitle('Multi-EV Charging – Grid Capacity Aware', fontsize=16, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig('simulation_results_multi.png', dpi=300, bbox_inches='tight')
    plt.show()


# ---------------------------------------------------------------------- #
# 7. Summary table
# ---------------------------------------------------------------------- #
def summarise_multi_ev(results: dict, cfg: dict, system):
    print("\n" + "="*80)
    print("MULTI-EV SIMULATION SUMMARY")
    print("="*80)
    print(f"{'Method':<8} {'Total Benefit (€)':>18} {'Final Avg SoC':>16} {'Grid Violations':>18}")
    print("-"*80)

    for name in ['simple', 'rl', 'pso']:
        benefit = sum(results[name]['benefit'])
        socs = np.array(results[name]['ev_soc'])
        avg_final = socs[-1].mean()
        violations = sum(
            1 for h in results['hours']
            if system.grid_usage.get(h, 0) > cfg['grid_capacity_per_hour'].get(h, float('inf'))
        )
        print(f"{name.upper():<8} {benefit:>18.2f} {avg_final:>16.1%} {violations:>18}")

    print("="*80)

