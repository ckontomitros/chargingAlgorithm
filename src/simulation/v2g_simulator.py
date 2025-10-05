from src.models.building import Building
from src.models.electric_vehicle import ElectricVehicle
from src.models.grid import Grid
from src.models.v2g_charging_system import V2GChargingSystem
from src.utils.data_generator import load_consumption_profile
import matplotlib.pyplot as plt
import numpy as np


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
    grid = Grid(config['price_profile'], config.get('sell_price_profile'))

    results = {
        'simple_charge_results': [],
        'optimized_charge_results': [],
        'rl_charge_results': [],
        'simple_ev_soc': [],
        'rl_ev_soc': [],
        'simple_building_soc': [],
        'rl_building_soc': [],
        'simple_costs': [],
        'rl_costs': [],
        'hours': [],
        'net_cost': {'simple': 0, 'optimized': 0, 'rl': 0}
    }

    hours_range = range(config['arrival_time'], config['target_time'])

    # Run simple charge simulation
    ev.soc = config['ev_initial_soc']
    building.soc = config['building_initial_soc']
    charging_system = V2GChargingSystem(
        building, ev, grid, config['desired_soc'], config['target_time'],
        config['arrival_time'], min_soc=config.get('min_soc', 0.2)
    )

    for hour in hours_range:
        action, cost = charging_system.simple_charge(hour)
        results['simple_charge_results'].append((action, cost))
        results['simple_ev_soc'].append(ev.soc)
        results['simple_building_soc'].append(building.soc)
        results['simple_costs'].append(cost)
        results['net_cost']['simple'] += cost

    # Run RL charge simulation
    ev.soc = config['ev_initial_soc']
    building.soc = config['building_initial_soc']
    charging_system = V2GChargingSystem(
        building, ev, grid, config['desired_soc'], config['target_time'],
        config['arrival_time'], min_soc=config.get('min_soc', 0.2)
    )

    for hour in hours_range:
        action, cost = charging_system.rl_charge(hour)
        results['rl_charge_results'].append((action, cost))
        results['rl_ev_soc'].append(ev.soc)
        results['rl_building_soc'].append(building.soc)
        results['rl_costs'].append(cost)
        results['net_cost']['rl'] += cost
        results['hours'].append(hour)

    # Generate visualizations
    visualize_results(results, config)

    return results


def visualize_results(results, config):
    """Generate visualization charts for simulation results."""
    hours = results['hours']
    target_soc = config['desired_soc']

    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    fig.suptitle('V2G Charging Simulation Results', fontsize=16, fontweight='bold')

    # Plot 1: EV State of Charge
    ax1.plot(hours, results['simple_ev_soc'], marker='o', linewidth=2,
             label='Simple Charge', color='#2E86AB')
    ax1.plot(hours, results['rl_ev_soc'], marker='s', linewidth=2,
             label='RL Charge', color='#A23B72')
    ax1.axhline(y=target_soc, color='#F18F01', linestyle='--', linewidth=2,
                label=f'Target SoC ({target_soc * 100:.0f}%)')

    ax1.set_xlabel('Hour of Day', fontsize=12)
    ax1.set_ylabel('State of Charge (SoC)', fontsize=12)
    ax1.set_title('EV Battery State of Charge Over Time', fontsize=14, fontweight='bold')
    ax1.legend(loc='best', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim([0, 1])

    # Format y-axis as percentage
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y * 100:.0f}%'))

    # Plot 2: Cost Comparison
    x_pos = np.arange(len(hours))
    width = 0.35

    bars1 = ax2.bar(x_pos - width / 2, results['simple_costs'], width,
                    label='Simple Charge', color='#2E86AB', alpha=0.8)
    bars2 = ax2.bar(x_pos + width / 2, results['rl_costs'], width,
                    label='RL Charge', color='#A23B72', alpha=0.8)

    ax2.set_xlabel('Hour of Day', fontsize=12)
    ax2.set_ylabel('Cost (€)', fontsize=12)
    ax2.set_title('Hourly Charging Cost Comparison', fontsize=14, fontweight='bold')
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(hours)
    ax2.legend(loc='best', fontsize=10)
    ax2.grid(True, alpha=0.3, axis='y')

    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height != 0:  # Only show label if non-zero
                ax2.text(bar.get_x() + bar.get_width() / 2., height,
                         f'€{height:.2f}',
                         ha='center', va='bottom', fontsize=8)

    # Add total cost summary
    total_simple = results['net_cost']['simple']
    total_rl = results['net_cost']['rl']
    savings = total_simple - total_rl
    savings_pct = (savings / total_simple * 100) if total_simple != 0 else 0

    summary_text = (f"Total Cost - Simple: €{total_simple:.2f} | "
                    f"RL: €{total_rl:.2f} | "
                    f"Savings: €{savings:.2f} ({savings_pct:.1f}%)")
    fig.text(0.5, 0.02, summary_text, ha='center', fontsize=11,
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    plt.savefig('simulation_results.png', dpi=300, bbox_inches='tight')
    print(f"\nVisualization saved as 'simulation_results.png'")
    plt.show()

    # Print summary statistics
    print("\n" + "=" * 60)
    print("SIMULATION SUMMARY")
    print("=" * 60)
    print(f"Simple Charge Method:")
    print(f"  - Final EV SoC: {results['simple_ev_soc'][-1] * 100:.1f}%")
    print(f"  - Total Cost: €{total_simple:.2f}")
    print(f"\nRL Charge Method:")
    print(f"  - Final EV SoC: {results['rl_ev_soc'][-1] * 100:.1f}%")
    print(f"  - Total Cost: €{total_rl:.2f}")
    print(f"\nTarget SoC: {target_soc * 100:.0f}%")
    print(f"Cost Savings with RL: €{savings:.2f} ({savings_pct:.1f}%)")
    print("=" * 60)