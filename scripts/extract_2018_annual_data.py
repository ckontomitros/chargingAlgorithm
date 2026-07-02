#!/usr/bin/env python3
"""
Annual 2018 data extraction script.

Runs charge-only rule-based and RL simulations for every day in 2018,
organized by month. Each month's results are saved to a separate
JSON file: scripts/results_2018/month_<MM>.json

Usage:
    python scripts/extract_2018_annual_data.py [--month 1-12] [--rl-episodes N]

    --month  Only process the given month (1-12). If omitted, all months are run.
    --rl-episodes  Override config rl_episodes for faster exploratory runs.

Multithreading:
    Each month is processed in its own thread (up to 12 threads in parallel).
    Within each month, all days are processed sequentially to keep memory usage
    predictable and avoid racing on the shared config structures.
"""

import sys
import os
import copy
import json
import time
import random
import argparse
import calendar
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from typing import Dict, Any, List, Optional

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.config import load_config
from src.utils.data_generator import load_consumption_profile, load_irradiance_pvgis
from src.models.building import Building
from src.models.grid import Grid
from src.simulation.multi_ev_simulator import run_multi_ev_simulation

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEED = 42
YEAR = 2018
HOME_CHARGING_PRICE_EUR_PER_KWH = 0.19
MAX_WORKERS = 12          # Maximum parallel month-threads
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'results_2018')
_print_lock = threading.Lock()


def tprint(*args, **kwargs):
    """Thread-safe print."""
    with _print_lock:
        print(*args, **kwargs)


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------

def _resolve_path(path: str, project_root: str) -> str:
    """Resolve a config path to an absolute path."""
    if os.path.isabs(path):
        return path
    if os.path.exists(path):
        return path
    return os.path.join(project_root, path)


def build_environment(cfg: Dict[str, Any], irradiance_date: str):
    """Create a Building and Grid for the given date, deep-copying the config."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    consumption_file = _resolve_path(cfg['consumption_file'], project_root)
    irradiance_profile = None

    if cfg.get('irradiance_file'):
        irradiance_file = _resolve_path(cfg['irradiance_file'], project_root)
        irradiance_profile = load_irradiance_pvgis(irradiance_file, irradiance_date)

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
        irradiance_profile=irradiance_profile,
    )

    price_profile = cfg['price_profile']
    if isinstance(price_profile, list):
        price_profile = {h: price_profile[h] for h in range(24)}

    grid = Grid(price_profile=price_profile)

    return building, grid


# ---------------------------------------------------------------------------
# Metric extraction (same logic as extract_all_thesis_data.py)
# ---------------------------------------------------------------------------

def extract_method_metrics(
    results: Dict,
    method: str,
    cfg: Dict[str, Any],
    building: 'Building',
    grid: 'Grid',
) -> Dict[str, Any]:
    """Extract detailed metrics from simulation results for a given method."""
    hours = results['hours']
    benefit_list = results[method]['benefit']
    grid_usage_list = results[method]['grid_usage']
    ev_soc_list = results[method]['ev_soc']

    total_benefit = sum(benefit_list)
    total_cost = -total_benefit
    total_grid_energy = sum(grid_usage_list)

    total_energy_charged = 0.0
    total_solar_used = 0.0

    for i, hour in enumerate(hours):
        production = building.renewable_energy_profile[hour % len(building.renewable_energy_profile)]
        consumption = building.energy_consumption_profile[hour % len(building.energy_consumption_profile)]
        building_net = consumption - production

        ev_grid = grid_usage_list[i]
        if i > 0:
            soc_prev = np.array(ev_soc_list[i - 1])
        else:
            soc_prev = np.array([ec['ev'].soc for ec in results.get('_evs', [])])
            if len(soc_prev) == 0:
                soc_prev = np.array(ev_soc_list[i])

        soc_curr = np.array(ev_soc_list[i])
        soc_diff = soc_curr - soc_prev
        energy_change = sum(max(0.0, d) * cfg['ev_battery_capacity'] for d in soc_diff)
        total_energy_charged += energy_change

        solar_used = max(0.0, energy_change - ev_grid)
        total_solar_used += solar_used

    cost_per_kwh = total_cost / total_grid_energy if total_grid_energy > 0 else 0.0

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
        'total_cost': float(total_cost),
        'total_benefit': float(total_benefit),
        'total_grid_energy': float(total_grid_energy),
        'total_solar_used': float(total_solar_used),
        'total_energy_charged': float(total_energy_charged),
        'cost_per_kwh': float(cost_per_kwh),
        'grid_violations': int(grid_violations),
        'soc_violations': int(soc_violations),
        'mean_final_soc': float(final_socs.mean()) if len(final_socs) > 0 else 0.0,
        'min_final_soc': float(final_socs.min()) if len(final_socs) > 0 else 0.0,
        'max_final_soc': float(final_socs.max()) if len(final_socs) > 0 else 0.0,
        'std_final_soc': float(final_socs.std()) if len(final_socs) > 0 else 0.0,
    }


# ---------------------------------------------------------------------------
# Single-day simulation
# ---------------------------------------------------------------------------

def simulate_day(
    date_str: str,
    co_base_cfg: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Run charge-only rule-based + RL simulations for one day and return all metrics.

    Returns a dict keyed by scenario name:
        { 'co_simple': {...}, 'co_rl': {...}, 'building': {...}, 'date': 'YYYYMMDD' }
    """
    # Deep-copy config so threads don't share mutable state
    co_cfg = copy.deepcopy(co_base_cfg)

    # Patch the irradiance date for this specific day
    co_cfg['irradiance_date'] = date_str

    # Normalise grid capacity
    if isinstance(co_cfg['grid_capacity_per_hour'], list):
        co_cfg['grid_capacity_per_hour'] = {h: co_cfg['grid_capacity_per_hour'][h] for h in range(24)}

    day_data: Dict[str, Any] = {'date': date_str}

    # ---- Charge-Only -------------------------------------------------------
    random.seed(SEED)
    np.random.seed(SEED)
    t0 = time.time()
    co_results = run_multi_ev_simulation(co_cfg)
    co_time = time.time() - t0

    building_co, grid_co = build_environment(co_cfg, date_str)

    for method in ('simple', 'rl'):
        if method not in co_results:
            continue
        metrics = extract_method_metrics(co_results, method, co_cfg, building_co, grid_co)
        metrics['home_charging_price_eur_per_kwh'] = HOME_CHARGING_PRICE_EUR_PER_KWH
        metrics['home_charging_cost'] = (
            metrics['total_energy_charged'] * HOME_CHARGING_PRICE_EUR_PER_KWH
        )
        metrics['execution_time'] = float(co_time)
        day_data[f'co_{method}'] = metrics

    # ---- Building profile --------------------------------------------------
    total_solar = sum(building_co.renewable_energy_profile)
    total_consumption = sum(building_co.energy_consumption_profile)
    building_solar_used = sum(
        min(building_co.energy_consumption_profile[h], building_co.renewable_energy_profile[h])
        for h in range(24)
    )
    day_data['building'] = {
        'total_solar_produced': float(total_solar),
        'total_consumption': float(total_consumption),
        'solar_used_by_building': float(building_solar_used),
    }

    return day_data


def summarise_month(month_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate daily metrics for the month."""
    summary: Dict[str, Any] = {}
    valid_days = [day for day in month_results if 'error' not in day]

    for key in ('co_simple', 'co_rl'):
        rows = [day[key] for day in valid_days if key in day]
        if not rows:
            continue

        total_cost = sum(row['total_cost'] for row in rows)
        total_energy = sum(row['total_energy_charged'] for row in rows)
        home_cost = sum(row['home_charging_cost'] for row in rows)
        summary[key] = {
            'total_cost': float(total_cost),
            'total_grid_energy': float(sum(row['total_grid_energy'] for row in rows)),
            'total_energy_charged': float(total_energy),
            'home_charging_price_eur_per_kwh': HOME_CHARGING_PRICE_EUR_PER_KWH,
            'home_charging_cost': float(home_cost),
            'home_charging_delta_vs_algorithm': float(home_cost - total_cost),
            'mean_final_soc': float(np.mean([row['mean_final_soc'] for row in rows])),
            'days': len(rows),
        }

    return summary


# ---------------------------------------------------------------------------
# Month processing
# ---------------------------------------------------------------------------

def process_month(month: int, co_base_cfg: Dict) -> str:
    """
    Simulate every day in `month` and save results to:
        scripts/results_2018/month_<MM>.json

    Returns the path to the saved file.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f'month_{month:02d}.json')

    tprint(f"\n{'='*70}")
    tprint(f"  Month {month:02d} ({calendar.month_name[month]} {YEAR})  —  thread {threading.current_thread().name}")
    tprint(f"{'='*70}")

    num_days = calendar.monthrange(YEAR, month)[1]
    month_results: List[Dict] = []
    errors: List[str] = []

    for day in range(1, num_days + 1):
        d = date(YEAR, month, day)
        date_str = d.strftime('%Y%m%d')
        try:
            tprint(f"  [{month:02d}] Simulating {date_str} ...")
            day_data = simulate_day(date_str, co_base_cfg)
            month_results.append(day_data)
        except Exception as exc:
            msg = f"  [{month:02d}] ERROR on {date_str}: {exc}"
            tprint(msg)
            errors.append(msg)
            month_results.append({'date': date_str, 'error': str(exc)})

    output_payload = {
        'month': month,
        'month_name': calendar.month_name[month],
        'year': YEAR,
        'num_days_processed': len(month_results),
        'errors': errors,
        'summary': summarise_month(month_results),
        'days': month_results,
    }

    with open(output_path, 'w') as f:
        json.dump(output_payload, f, indent=2, default=str)

    tprint(f"  [{month:02d}] Saved -> {output_path}  ({len(month_results)} days, {len(errors)} errors)")
    for key, label in (('co_simple', 'Rule-based'), ('co_rl', 'RL')):
        if key in output_payload['summary']:
            s = output_payload['summary'][key]
            tprint(
                f"  [{month:02d}] {label}: algorithm cost EUR {s['total_cost']:.2f}, "
                f"home cost EUR {s['home_charging_cost']:.2f} "
                f"at EUR {HOME_CHARGING_PRICE_EUR_PER_KWH:.2f}/kWh"
            )
    return output_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Extract 2018 charge-only rule-based/RL simulation data, one file per month.'
    )
    parser.add_argument(
        '--month', type=int, choices=range(1, 13), metavar='1-12',
        help='Process only this month (1=Jan … 12=Dec). Omit to process all months.'
    )
    parser.add_argument(
        '--rl-episodes', type=int, metavar='N',
        help='Override the config rl_episodes value for this run.'
    )
    args = parser.parse_args()

    # Change to project root so relative paths in configs work
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    # Load base config once (threads will deep-copy it)
    tprint('Loading config ...')
    co_base_cfg = load_config('data/multi_ev_config.yml')
    if args.rl_episodes is not None:
        co_base_cfg['rl_episodes'] = args.rl_episodes

    # Disable plotting and summarizing to avoid terminal spam and file contention in parallel runs
    co_base_cfg['visualise'] = False
    co_base_cfg['summarise'] = False

    months_to_run: List[int] = [args.month] if args.month else list(range(1, 13))

    tprint(f'Processing months: {months_to_run}')
    tprint(f'Output directory : {OUTPUT_DIR}')
    tprint(f'Max parallel threads: {min(MAX_WORKERS, len(months_to_run))}')
    tprint(f"RL episodes      : {co_base_cfg.get('rl_episodes')}")

    t_start = time.time()

    if len(months_to_run) == 1:
        # Single month — run inline (simpler for debugging)
        process_month(months_to_run[0], co_base_cfg)
    else:
        # Multiple months — one thread per month
        with ThreadPoolExecutor(
            max_workers=min(MAX_WORKERS, len(months_to_run)),
            thread_name_prefix='month',
        ) as executor:
            futures = {
                executor.submit(process_month, m, co_base_cfg): m
                for m in months_to_run
            }
            for future in as_completed(futures):
                m = futures[future]
                try:
                    path = future.result()
                    tprint(f'Month {m:02d} complete -> {path}')
                except Exception as exc:
                    tprint(f'Month {m:02d} FAILED: {exc}')

    elapsed = time.time() - t_start
    tprint(f'\nAll done in {elapsed:.1f}s  -  results in {OUTPUT_DIR}')


if __name__ == '__main__':
    main()
