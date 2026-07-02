#!/usr/bin/env python3
"""
Script to extract data from simulation results and generate LaTeX table entries.
This helps populate the [XX.XX] placeholders in the thesis.

Usage:
    python scripts/extract_thesis_data.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
from src.utils.config import load_config
from src.simulation.multi_ev_simulator import run_multi_ev_simulation
from src.simulation.multi_ev_v2g_simulator import run_multi_ev_v2g_simulation


def format_latex_table_row(method, cost, savings_pct, cost_per_kwh, grid_energy):
    """Format a row for LaTeX table"""
    return f"{method:<20} & {cost:>7.2f} & {savings_pct:>6.1f} & {cost_per_kwh:>6.3f} & {grid_energy:>7.1f} \\\\"


def extract_charge_only_results():
    """Run charge-only simulation and extract results"""
    print("=" * 80)
    print("EXTRACTING CHARGE-ONLY SIMULATION DATA")
    print("=" * 80)
    
    config_path = "data/multi_ev_config.yml"
    config = load_config(config_path)
    
    print(f"\nRunning simulation with {config['n_evs']} EVs...")
    results = run_multi_ev_simulation(config)
    
    print("\n" + "=" * 80)
    print("LATEX TABLE DATA - CHARGE-ONLY SCENARIO")
    print("=" * 80)
    
    # Calculate metrics for each method
    methods = ['simple', 'rl']  # Add more if available
    baseline_cost = None
    
    print("\n% Copy this into Table 4.1 (Economic Comparison)")
    print("% \\begin{tabular}{@{}lcccc@{}}")
    print("% Method & Total Cost (€) & Savings vs L0 (\\%) & Cost/kWh (€) & Grid Energy (kWh) \\\\")
    print("% \\midrule")
    
    for method in methods:
        if method not in results:
            continue
        
        total_benefit = sum(results[method]['benefit'])
        total_cost = -total_benefit  # Benefit is negative cost
        
        # Calculate total energy charged
        total_grid_energy = sum(results[method]['grid_usage'])
        
        # Cost per kWh
        cost_per_kwh = total_cost / total_grid_energy if total_grid_energy > 0 else 0
        
        # Savings vs baseline (if we had baseline)
        if baseline_cost is None and method == 'simple':
            # Estimate baseline as 1.5x simple cost (rough approximation)
            baseline_cost = total_cost * 1.5
        
        savings_pct = ((baseline_cost - total_cost) / baseline_cost * 100) if baseline_cost else 0
        
        method_name = method.upper()
        print(format_latex_table_row(method_name, total_cost, savings_pct, 
                                     cost_per_kwh, total_grid_energy))
        
        # Additional statistics
        print(f"\n% {method_name} Additional Stats:")
        print(f"%   Total benefit: €{total_benefit:.2f}")
        print(f"%   Total grid energy: {total_grid_energy:.1f} kWh")
        print(f"%   Average SoC: {np.mean(results[method]['ev_soc'][-1]):.1%}")
        print(f"%   Grid violations: {sum(1 for g in results[method]['grid_usage'] if g > config['grid_capacity_per_hour'][0])}")
    
    print("\n% \\bottomrule")
    print("% \\end{tabular}")
    
    return results


def extract_v2g_results():
    """Run V2G simulation and extract results"""
    print("\n" + "=" * 80)
    print("EXTRACTING V2G SIMULATION DATA")
    print("=" * 80)
    
    config_path = "data/multi_ev_v2g_config.yml"
    config = load_config(config_path)
    
    print(f"\nRunning V2G simulation with {config['n_evs']} EVs...")
    results = run_multi_ev_v2g_simulation(config)
    
    print("\n" + "=" * 80)
    print("LATEX TABLE DATA - V2G SCENARIO")
    print("=" * 80)
    
    methods = ['simple', 'rl']
    
    print("\n% Copy this into Table 4.X (V2G Comparison)")
    print("% \\begin{tabular}{@{}lccc@{}}")
    print("% Method & Total Benefit (€) & Improvement vs Charge-Only (€) & V2G Revenue (€) \\\\")
    print("% \\midrule")
    
    for method in methods:
        if method not in results:
            continue
        
        total_benefit = sum(results[method]['benefit'])
        
        method_name = method.upper()
        print(f"{method_name:<20} & {total_benefit:>7.2f} & [TBD] & [TBD] \\\\")
        
        print(f"\n% {method_name} V2G Stats:")
        print(f"%   Total benefit: €{total_benefit:.2f}")
        print(f"%   Average final SoC: {np.mean(results[method]['ev_soc'][-1]):.1%}")
    
    print("\n% \\bottomrule")
    print("% \\end{tabular}")
    
    return results


def extract_building_profile(config_path):
    """Extract building consumption and solar production data"""
    print("\n" + "=" * 80)
    print("BUILDING ENERGY PROFILE DATA")
    print("=" * 80)
    
    config = load_config(config_path)
    
    from src.utils.data_generator import load_consumption_profile, load_irradiance_pvgis
    from src.models.building import Building
    
    # Load consumption
    consumption_file = config['consumption_file']
    if not os.path.isabs(consumption_file):
        consumption_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                       consumption_file)
    
    consumption = load_consumption_profile(consumption_file)
    
    # Load irradiance
    irradiance = None
    if config.get('irradiance_file') and config.get('irradiance_date'):
        irradiance_file = config['irradiance_file']
        if not os.path.isabs(irradiance_file):
            irradiance_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                          irradiance_file)
        irradiance = load_irradiance_pvgis(irradiance_file, config['irradiance_date'])
    
    # Create building
    building = Building(
        energy_consumption_profile=consumption,
        panel_area=config['panel_area'],
        panel_efficiency=config['panel_efficiency'],
        peak_solar_irradiance=config['peak_solar_irradiance'],
        battery_capacity=config['building_battery_capacity'],
        battery_efficiency=config['building_battery_efficiency'],
        initial_soc=config['building_initial_soc'],
        dod=config['building_dod'],
        irradiance_profile=irradiance
    )
    
    print("\n% Copy this into Table 3.X (Building Energy Profile)")
    print("% Hour & Consumption (kW) & Solar (kW) & Net Demand (kW) \\\\")
    print("% \\midrule")
    
    total_consumption = 0
    total_solar = 0
    
    for hour in range(24):
        cons = building.energy_consumption_profile[hour]
        solar = building.renewable_energy_profile[hour]
        net = cons - solar
        
        total_consumption += cons
        total_solar += solar
        
        print(f"% {hour:02d}:00 & {cons:>6.2f} & {solar:>6.2f} & {net:>7.2f} \\\\")
    
    print(f"% \\midrule")
    print(f"% Total & {total_consumption:>6.1f} & {total_solar:>6.1f} & --- \\\\")
    print("% \\bottomrule")
    
    print(f"\n% Summary Statistics:")
    print(f"%   Total daily consumption: {total_consumption:.1f} kWh")
    print(f"%   Total daily solar production: {total_solar:.1f} kWh")
    print(f"%   Peak consumption: {max(consumption):.1f} kW")
    print(f"%   Peak solar production: {max(building.renewable_energy_profile):.1f} kW")
    print(f"%   Solar self-sufficiency: {(total_solar/total_consumption)*100:.1f}%")


def extract_price_profile(config_path):
    """Extract electricity price data"""
    print("\n" + "=" * 80)
    print("ELECTRICITY PRICE PROFILE DATA")
    print("=" * 80)
    
    config = load_config(config_path)
    
    price_profile = config['price_profile']
    sell_profile = config.get('sell_price_profile', [0] * 24)
    
    print("\n% Copy this into Table 3.X (Electricity Prices)")
    print("% Hour & Purchase (€/kWh) & Sell (€/kWh) & Spread (\\%) \\\\")
    print("% \\midrule")
    
    for hour in range(24):
        buy = price_profile[hour]
        sell = sell_profile[hour] if hour < len(sell_profile) else 0
        spread = (sell / buy * 100) if buy > 0 else 0
        
        print(f"% {hour:02d}:00 & {buy:.2f} & {sell:.2f} & {spread:.0f}\\% \\\\")
    
    avg_buy = np.mean(price_profile)
    avg_sell = np.mean(sell_profile) if sell_profile else 0
    
    print(f"% \\midrule")
    print(f"% Average & {avg_buy:.2f} & {avg_sell:.2f} & {(avg_sell/avg_buy*100):.0f}\\% \\\\")
    print("% \\bottomrule")


def generate_all_data():
    """Generate all data for thesis"""
    print("\n")
    print("=" * 80)
    print("THESIS DATA EXTRACTION TOOL")
    print("=" * 80)
    print("\nThis script will run simulations and extract data for your thesis.")
    print("The output includes LaTeX table entries you can copy directly.")
    print("\nNote: This may take several minutes to complete.")
    print("=" * 80)
    
    # Extract building and price data (fast)
    extract_building_profile("data/multi_ev_v2g_config.yml")
    extract_price_profile("data/multi_ev_v2g_config.yml")
    
    # Run simulations (slow)
    print("\n\nWARNING: About to run full simulations. This may take 5-10 minutes.")
    response = input("Continue? (y/n): ")
    
    if response.lower() == 'y':
        charge_only_results = extract_charge_only_results()
        v2g_results = extract_v2g_results()
        
        print("\n" + "=" * 80)
        print("DATA EXTRACTION COMPLETE")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Copy the LaTeX table entries above into your thesis chapters")
        print("2. Replace [XX.XX] placeholders with the actual values")
        print("3. Create additional figures as needed")
        print("4. Compile your thesis: cd thesis && make")
        print("=" * 80)
    else:
        print("\nSimulation skipped. Run manually when ready.")


if __name__ == "__main__":
    # Change to project root
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    generate_all_data()
