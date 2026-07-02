#!/usr/bin/env python3
"""
Comprehensive thesis data extraction script.
Runs charge-only and V2G simulations and outputs all metrics
needed for Chapter 4 (Results). All comparisons are relative
to the Simple algorithm baseline.
"""
import sys
import os
import time
import json
import random
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.config import load_config
from src.utils.data_generator import load_consumption_profile, load_irradiance_pvgis
from src.models.building import Building
from src.models.grid import Grid
from src.simulation.multi_ev_simulator import run_multi_ev_simulation, random_ev_config as random_ev_config_co
from src.simulation.multi_ev_v2g_simulator import run_multi_ev_v2g_simulation, random_ev_config as random_ev_config_v2g


SEED = 42


def build_environment(cfg):
    """Build building and grid from config."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    consumption_file = cfg['consumption_file']
    if not os.path.isabs(consumption_file):
        if not os.path.exists(consumption_file):
            consumption_file = os.path.join(project_root, consumption_file)

    irradiance_profile = None
    if cfg.get('irradiance_file') and cfg.get('irradiance_date'):
        irradiance_file = cfg['irradiance_file']
        if not os.path.isabs(irradiance_file):
            if not os.path.exists(irradiance_file):
                irradiance_file = os.path.join(project_root, irradiance_file)
        irradiance_profile = load_irradiance_pvgis(irradiance_file, cfg['irradiance_date'])

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

    price_profile = cfg['price_profile']
    if isinstance(price_profile, list):
        price_profile = {h: price_profile[h] for h in range(24)}
        cfg['price_profile'] = price_profile

    grid = Grid(
        price_profile=price_profile,
        sell_price_profile=cfg.get('sell_price_profile')
    )

    return building, grid




def extract_method_metrics(results, method, cfg, building, grid):
    """Extract detailed metrics from simulation results for a given method."""
    hours = results['hours']
    benefit_list = results[method]['benefit']
    grid_usage_list = results[method]['grid_usage']
    ev_soc_list = results[method]['ev_soc']

    total_benefit = sum(benefit_list)
    total_cost = -total_benefit
    total_grid_energy = sum(grid_usage_list)

    total_energy_charged = 0
    total_solar_used = 0
    for i, hour in enumerate(hours):
        consumption = building.energy_consumption_profile[hour % len(building.energy_consumption_profile)]
        production = building.renewable_energy_profile[hour % len(building.renewable_energy_profile)]
        building_net = consumption - production
        building_surplus = max(0, -building_net)

        ev_grid = grid_usage_list[i]
        if i > 0:
            soc_prev = np.array(ev_soc_list[i - 1])
        else:
            soc_prev = np.array([ev_cfg['ev'].soc for ev_cfg in results.get('_evs', [])])
            if len(soc_prev) == 0:
                soc_prev = np.array(ev_soc_list[i])

        soc_curr = np.array(ev_soc_list[i])
        soc_diff = soc_curr - soc_prev
        energy_change = sum(max(0, d) * cfg['ev_battery_capacity'] for d in soc_diff)
        total_energy_charged += energy_change

        solar_used = max(0, energy_change - ev_grid)
        total_solar_used += solar_used

    cost_per_kwh = total_cost / total_grid_energy if total_grid_energy > 0 else 0

    grid_cap = cfg['grid_capacity_per_hour']
    if isinstance(grid_cap, list):
        grid_cap = {h: grid_cap[h] for h in range(24)}
    grid_violations = sum(
        1 for i, h in enumerate(hours)
        if grid_usage_list[i] > grid_cap.get(h, float('inf'))
    )

    min_soc = cfg.get('min_soc', 0.2)
    soc_violations = sum(
        1 for soc_array in ev_soc_list
        for s in soc_array
        if s < min_soc
    )

    final_socs = np.array(ev_soc_list[-1]) if ev_soc_list else np.array([])

    return {
        'total_cost': total_cost,
        'total_benefit': total_benefit,
        'total_grid_energy': total_grid_energy,
        'total_solar_used': total_solar_used,
        'total_energy_charged': total_energy_charged,
        'cost_per_kwh': cost_per_kwh,
        'grid_violations': grid_violations,
        'soc_violations': soc_violations,
        'final_socs': final_socs,
        'mean_final_soc': float(final_socs.mean()) if len(final_socs) > 0 else 0,
        'min_final_soc': float(final_socs.min()) if len(final_socs) > 0 else 0,
        'max_final_soc': float(final_socs.max()) if len(final_socs) > 0 else 0,
        'std_final_soc': float(final_socs.std()) if len(final_socs) > 0 else 0,
    }


def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    co_config = load_config("data/multi_ev_config.yml")
    v2g_config = load_config("data/multi_ev_v2g_config.yml")

    if isinstance(co_config['grid_capacity_per_hour'], list):
        co_config['grid_capacity_per_hour'] = {h: co_config['grid_capacity_per_hour'][h] for h in range(24)}
    if isinstance(v2g_config['grid_capacity_per_hour'], list):
        v2g_config['grid_capacity_per_hour'] = {h: v2g_config['grid_capacity_per_hour'][h] for h in range(24)}

    building_co, grid_co = build_environment(co_config)
    building_v2g, grid_v2g = build_environment(v2g_config)

    all_data = {}


    # ============================
    # 1. Charge-Only (Simple + RL)
    # ============================
    print("=" * 80)
    print("RUNNING CHARGE-ONLY SIMULATION (Simple + RL)")
    print("=" * 80)
    random.seed(SEED)
    np.random.seed(SEED)
    t0 = time.time()
    co_results = run_multi_ev_simulation(co_config)
    co_time = time.time() - t0

    building_co2, _ = build_environment(co_config)

    for method in ['simple', 'rl']:
        if method not in co_results:
            continue
        metrics = extract_method_metrics(co_results, method, co_config, building_co2, grid_co)
        all_data[f'co_{method}'] = metrics
        all_data[f'co_{method}']['execution_time'] = co_time

        print(f"\n{method.upper()} (Charge-Only):")
        print(f"  Total cost: EUR {metrics['total_cost']:.2f}")
        print(f"  Grid energy: {metrics['total_grid_energy']:.1f} kWh")
        print(f"  Solar used: {metrics['total_solar_used']:.1f} kWh")
        print(f"  Cost/kWh: EUR {metrics['cost_per_kwh']:.4f}")
        print(f"  Grid violations: {metrics['grid_violations']}")
        print(f"  Avg final SoC: {metrics['mean_final_soc']:.1%}")

    # ============================
    # 2. V2G (Simple + RL)
    # ============================
    print("\n" + "=" * 80)
    print("RUNNING V2G SIMULATION (Simple + RL)")
    print("=" * 80)
    random.seed(SEED)
    np.random.seed(SEED)
    t0 = time.time()
    v2g_results = run_multi_ev_v2g_simulation(v2g_config)
    v2g_time = time.time() - t0

    building_v2g2, _ = build_environment(v2g_config)

    for method in ['simple', 'rl']:
        if method not in v2g_results:
            continue
        metrics = extract_method_metrics(v2g_results, method, v2g_config, building_v2g2, grid_v2g)

        v2g_benefit_list = v2g_results[method]['benefit']
        v2g_revenue = sum(b for b in v2g_benefit_list if b > 0)
        v2g_energy_discharged = 0
        ev_soc_list = v2g_results[method]['ev_soc']
        for i in range(1, len(ev_soc_list)):
            soc_prev = np.array(ev_soc_list[i - 1])
            soc_curr = np.array(ev_soc_list[i])
            for j in range(len(soc_prev)):
                if soc_curr[j] < soc_prev[j]:
                    v2g_energy_discharged += (soc_prev[j] - soc_curr[j]) * v2g_config['ev_battery_capacity']

        metrics['v2g_revenue'] = v2g_revenue
        metrics['v2g_energy_discharged'] = v2g_energy_discharged
        metrics['execution_time'] = v2g_time

        all_data[f'v2g_{method}'] = metrics

        print(f"\n{method.upper()} (V2G):")
        print(f"  Total benefit: EUR {metrics['total_benefit']:.2f}")
        print(f"  Total cost: EUR {metrics['total_cost']:.2f}")
        print(f"  V2G revenue: EUR {v2g_revenue:.2f}")
        print(f"  V2G energy discharged: {v2g_energy_discharged:.1f} kWh")
        print(f"  Grid energy: {metrics['total_grid_energy']:.1f} kWh")
        print(f"  Avg final SoC: {metrics['mean_final_soc']:.1%}")

    # ============================
    # 3. Building profile data
    # ============================
    total_solar_produced = sum(building_co2.renewable_energy_profile)
    total_building_consumption = sum(building_co2.energy_consumption_profile)
    building_solar_used = 0
    for hour in range(24):
        cons = building_co2.energy_consumption_profile[hour]
        solar = building_co2.renewable_energy_profile[hour]
        building_solar_used += min(cons, solar)

    all_data['building'] = {
        'total_solar_produced': total_solar_produced,
        'total_consumption': total_building_consumption,
        'solar_used_by_building': building_solar_used,
    }

    # ============================
    # 4. Print structured summary
    # ============================
    print("\n\n" + "=" * 80)
    print("STRUCTURED DATA OUTPUT FOR THESIS")
    print("=" * 80)

    baseline_cost = all_data['co_simple']['total_cost']

    print("\n--- TABLE 4.1: Economic comparison (charge-only) ---")
    for m in ['simple', 'rl']:
        k = f'co_{m}'
        if k in all_data:
            d = all_data[k]
            sav_pct = (baseline_cost - d['total_cost']) / baseline_cost * 100 if baseline_cost > 0 else 0
            print(f"{m.upper():8s}: Cost={d['total_cost']:.2f} EUR, "
                  f"vs Simple={sav_pct:+.1f}%, "
                  f"Cost/kWh={d['cost_per_kwh']:.4f}, "
                  f"Grid={d['total_grid_energy']:.1f} kWh")

    print("\n--- TABLE 4.2: Renewable utilization (charge-only) ---")
    simple_solar = all_data.get('co_simple', {}).get('total_solar_used', 0)
    for label, k in [('Simple', 'co_simple'), ('RL', 'co_rl')]:
        if k in all_data:
            d = all_data[k]
            total_energy = d.get('total_solar_used', 0) + d.get('total_grid_energy', 0)
            solar_pct = (d.get('total_solar_used', 0) / total_energy * 100) if total_energy > 0 else 0
            solar_vs_simple = (d.get('total_solar_used', 0) - simple_solar) / simple_solar * 100 if simple_solar > 0 else 0
            print(f"{label:8s}: Solar Used={d.get('total_solar_used', 0):.1f} kWh, "
                  f"Solar%={solar_pct:.0f}%, "
                  f"vs Simple={solar_vs_simple:+.1f}%, "
                  f"Grid={d['total_grid_energy']:.1f} kWh")

    print("\n--- TABLE 4.3: Constraint violations (charge-only) ---")
    for label, k in [('Simple', 'co_simple'), ('RL', 'co_rl')]:
        if k in all_data:
            d = all_data[k]
            targets_met = d.get('targets_met', co_config['n_evs'])
            target_pct = targets_met / co_config['n_evs'] * 100 if 'targets_met' in d else 100
            print(f"{label:8s}: Grid Violations={d['grid_violations']}, "
                  f"SoC Violations={d['soc_violations']}, "
                  f"Target={target_pct:.0f}%")

    print("\n--- TABLE 4.4: V2G benefit ---")
    for m in ['simple', 'rl']:
        vk = f'v2g_{m}'
        ck = f'co_{m}'
        if vk in all_data and ck in all_data:
            v = all_data[vk]
            c = all_data[ck]
            improvement = c['total_cost'] - v['total_cost']
            print(f"{m.upper():8s}: TotalBenefit={v['total_benefit']:.2f} EUR, "
                  f"Improvement={improvement:.2f} EUR, "
                  f"V2G Revenue={v.get('v2g_revenue', 0):.2f} EUR, "
                  f"V2G Energy={v.get('v2g_energy_discharged', 0):.1f} kWh")

    print("\n--- TABLE 4.5: V2G energy flow (RL) ---")
    if 'v2g_rl' in all_data:
        d = all_data['v2g_rl']
        total_charged = d['total_solar_used'] + d['total_grid_energy']
        net_ev = d['total_energy_charged'] - d.get('v2g_energy_discharged', 0)
        print(f"Solar Energy: {d['total_solar_used']:.1f} kWh ({d['total_solar_used']/total_charged*100:.0f}%)" if total_charged > 0 else "Solar: 0")
        print(f"Grid Energy: {d['total_grid_energy']:.1f} kWh ({d['total_grid_energy']/total_charged*100:.0f}%)" if total_charged > 0 else "Grid: 0")
        print(f"Total Charged: {total_charged:.1f} kWh")
        print(f"EV Net: {net_ev:.1f} kWh")
        print(f"V2G Discharge: {d.get('v2g_energy_discharged', 0):.1f} kWh")

    print("\n--- TABLE 4.6: Cost reduction relative to Simple ---")
    levels = [
        ('Simple (Baseline)', all_data.get('co_simple', {}).get('total_cost', 0)),
        ('RL', all_data.get('co_rl', {}).get('total_cost', 0)),
        ('RL+V2G', all_data.get('v2g_rl', {}).get('total_cost', 0)),
    ]
    for label, cost in levels:
        saving = baseline_cost - cost
        saving_pct = saving / baseline_cost * 100 if baseline_cost > 0 else 0
        print(f"{label:20s}: Cost={cost:.2f} EUR, vs Simple={saving:+.2f} EUR ({saving_pct:+.0f}%)")

    print("\n--- TABLE 4.7: Computational performance ---")
    print(f"Simple: Training=0s, Execution={all_data.get('co_simple', {}).get('execution_time', 0):.2f}s")
    print(f"RL:     Training={all_data.get('co_rl', {}).get('execution_time', 0):.1f}s (total incl training)")

    print("\n--- TABLE 4.8: Final SoC statistics ---")
    for label, k in [('Simple', 'co_simple'), ('RL', 'co_rl')]:
        if k in all_data:
            d = all_data[k]
            print(f"{label:8s}: Mean={d['mean_final_soc']:.1%}, "
                  f"Min={d['min_final_soc']:.1%}, "
                  f"Max={d['max_final_soc']:.1%}, "
                  f"StdDev={d['std_final_soc']:.1%}")

    print("\n--- TABLE 4.9: V2G impact on costs ---")
    for m in ['simple', 'rl']:
        ck = f'co_{m}'
        vk = f'v2g_{m}'
        if ck in all_data and vk in all_data:
            c_cost = all_data[ck]['total_cost']
            v_cost = all_data[vk]['total_cost']
            benefit = c_cost - v_cost
            print(f"{m.upper():8s}: Charge-Only={c_cost:.2f} EUR, "
                  f"V2G={v_cost:.2f} EUR, "
                  f"V2G Benefit={benefit:.2f} EUR")

    print("\n--- TABLE 4.10: Battery cycling ---")
    for scenario, k in [('Charge-Only (RL)', 'co_rl'), ('V2G (RL)', 'v2g_rl')]:
        if k in all_data:
            d = all_data[k]
            total_charged = d['total_energy_charged']
            avg_charge_cycles = total_charged / (co_config['n_evs'] * co_config['ev_battery_capacity'])
            v2g_discharged = d.get('v2g_energy_discharged', 0)
            avg_discharge_cycles = v2g_discharged / (co_config['n_evs'] * co_config['ev_battery_capacity'])
            total_throughput = total_charged + v2g_discharged
            print(f"{scenario:20s}: ChargeCycles={avg_charge_cycles:.2f}, "
                  f"DischargeCycles={avg_discharge_cycles:.2f}, "
                  f"Throughput={total_throughput:.1f} kWh")

    print("\n--- TABLE 4.11: Solar utilization ---")
    bld = all_data['building']
    print(f"{'Scenario':12s} {'Solar Prod':>12s} {'Bld Used':>10s} {'EV Used':>10s} {'Self-Cons%':>12s}")
    no_ev_self = bld['solar_used_by_building'] / bld['total_solar_produced'] * 100 if bld['total_solar_produced'] > 0 else 0
    print(f"{'No EVs':12s} {bld['total_solar_produced']:>12.1f} {bld['solar_used_by_building']:>10.1f} {'0':>10s} {no_ev_self:>11.0f}%")
    for label, k in [('Simple', 'co_simple'), ('RL', 'co_rl')]:
        if k in all_data:
            d = all_data[k]
            ev_solar = d.get('total_solar_used', 0)
            total_used = bld['solar_used_by_building'] + ev_solar
            self_cons = total_used / bld['total_solar_produced'] * 100 if bld['total_solar_produced'] > 0 else 0
            print(f"{label:12s} {bld['total_solar_produced']:>12.1f} {bld['solar_used_by_building']:>10.1f} {ev_solar:>10.1f} {self_cons:>11.0f}%")

    print("\n--- TABLE 4.12: Annual projections (250 working days) ---")
    for label, cost in levels:
        annual = cost * 250
        annual_saving = (baseline_cost - cost) * 250
        print(f"{label:20s}: Daily={cost:.2f} EUR, Annual={annual:.0f} EUR, "
              f"vs Simple={annual_saving:+.0f} EUR")

    print("\n--- SUMMARY TEXT (relative to Simple baseline) ---")
    rl_cost = all_data.get('co_rl', {}).get('total_cost', 0)
    rl_vs_simple = (baseline_cost - rl_cost) / baseline_cost * 100 if baseline_cost > 0 else 0

    v2g_simple_cost = all_data.get('v2g_simple', {}).get('total_cost', 0)
    v2g_rl_cost = all_data.get('v2g_rl', {}).get('total_cost', 0)
    v2g_rl_vs_simple = (baseline_cost - v2g_rl_cost) / baseline_cost * 100 if baseline_cost > 0 else 0

    v2g_daily_benefit_simple = baseline_cost - v2g_simple_cost
    v2g_daily_benefit_rl = rl_cost - v2g_rl_cost

    print(f"RL improvement over Simple: {rl_vs_simple:+.1f}%")
    print(f"RL+V2G improvement over Simple: {v2g_rl_vs_simple:+.1f}%")
    print(f"V2G daily benefit (Simple): EUR {v2g_daily_benefit_simple:.2f}")
    print(f"V2G daily benefit (RL): EUR {v2g_daily_benefit_rl:.2f}")
    print(f"V2G annual benefit (250 days): EUR {v2g_daily_benefit_simple*250:.0f}-{v2g_daily_benefit_rl*250:.0f}")

    # Save raw data for reference
    output_data = {}
    for k, v in all_data.items():
        if isinstance(v, dict):
            output_data[k] = {}
            for k2, v2 in v.items():
                if isinstance(v2, np.ndarray):
                    output_data[k][k2] = v2.tolist()
                elif isinstance(v2, (np.floating, np.integer)):
                    output_data[k][k2] = float(v2)
                else:
                    output_data[k][k2] = v2

    with open('scripts/thesis_data.json', 'w') as f:
        json.dump(output_data, f, indent=2, default=str)
    print("\nRaw data saved to scripts/thesis_data.json")


if __name__ == "__main__":
    main()
