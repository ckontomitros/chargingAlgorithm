#!/usr/bin/env python3
"""
Annual 2018 averages aggregator.

Reads the per-month JSON files produced by extract_2018_annual_data.py
(scripts/results_2018/month_<MM>.json) and computes:

  1. Per-month averages  — one row per month
  2. Per-day-of-year averages — ordered across all months
  3. Overall annual averages  — single summary row

Results are printed to stdout and saved to:
    scripts/results_2018/averages_2018.json

Usage:
    python scripts/compute_2018_averages.py [--month 1-12]

    --month  Limit the aggregation to a single month (useful for quick checks).
"""

import sys
import os
import json
import argparse
import calendar
from typing import Dict, Any, List, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
RESULTS_DIR = os.path.join(os.path.dirname(__file__), 'results_2018')
OUTPUT_FILE = os.path.join(RESULTS_DIR, 'averages_2018.json')

# Scenarios we know about
SCENARIOS = ('co_simple', 'co_rl', 'v2g_simple', 'v2g_rl')

# Numeric metric names to average
NUMERIC_METRICS = (
    'total_cost',
    'total_benefit',
    'total_grid_energy',
    'total_solar_used',
    'total_energy_charged',
    'cost_per_kwh',
    'grid_violations',
    'soc_violations',
    'mean_final_soc',
    'min_final_soc',
    'max_final_soc',
    'std_final_soc',
    'execution_time',
    # V2G-specific (only present for v2g_* scenarios)
    'v2g_revenue',
    'v2g_energy_discharged',
)

BUILDING_METRICS = (
    'total_solar_produced',
    'total_consumption',
    'solar_used_by_building',
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_mean(values: List[float]) -> Optional[float]:
    """Return the mean of a list, or None if the list is empty."""
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def average_day_records(day_records: List[Dict]) -> Dict[str, Any]:
    """
    Given a list of per-day dicts (each produced by simulate_day()),
    compute the mean of every numeric metric across all valid days.
    """
    valid = [d for d in day_records if 'error' not in d]
    n = len(valid)
    if n == 0:
        return {'n_days': 0}

    averages: Dict[str, Any] = {'n_days': n}

    # Scenario metrics
    for scenario in SCENARIOS:
        scenario_values: Dict[str, List[float]] = {m: [] for m in NUMERIC_METRICS}
        for day in valid:
            if scenario not in day:
                continue
            for metric in NUMERIC_METRICS:
                v = day[scenario].get(metric)
                if v is not None:
                    scenario_values[metric].append(v)

        averages[scenario] = {
            m: safe_mean(scenario_values[m]) for m in NUMERIC_METRICS
        }

    # Building metrics
    bld_values: Dict[str, List[float]] = {m: [] for m in BUILDING_METRICS}
    for day in valid:
        if 'building' not in day:
            continue
        for metric in BUILDING_METRICS:
            v = day['building'].get(metric)
            if v is not None:
                bld_values[metric].append(v)
    averages['building'] = {m: safe_mean(bld_values[m]) for m in BUILDING_METRICS}

    return averages


def load_month_file(month: int) -> Optional[Dict]:
    """Load a month JSON file. Returns None if missing."""
    path = os.path.join(RESULTS_DIR, f'month_{month:02d}.json')
    if not os.path.exists(path):
        print(f'  [WARNING] Missing month file: {path}')
        return None
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Printing helpers
# ---------------------------------------------------------------------------

def _fmt(v: Optional[float], fmt: str = '.4f') -> str:
    return f'{v:{fmt}}' if v is not None else 'N/A'


def print_scenario_table(label: str, averages: Dict[str, Any]):
    """Print a concise table for one set of averages (month or annual)."""
    print(f'\n  {label}')
    n = averages.get('n_days', 0)
    print(f'  Days averaged: {n}')

    hdr = f"  {'Scenario':<14} {'Cost(€)':<10} {'Grid(kWh)':<12} {'Solar(kWh)':<12} {'Cost/kWh':<10} {'GridViol':<9} {'AvgSoC':<8}"
    print(hdr)
    print('  ' + '-' * (len(hdr) - 2))

    for sc in SCENARIOS:
        if sc not in averages:
            continue
        d = averages[sc]
        print(
            f"  {sc:<14} "
            f"{_fmt(d.get('total_cost'), '.2f'):<10} "
            f"{_fmt(d.get('total_grid_energy'), '.1f'):<12} "
            f"{_fmt(d.get('total_solar_used'), '.1f'):<12} "
            f"{_fmt(d.get('cost_per_kwh'), '.4f'):<10} "
            f"{str(round(d['grid_violations']) if d.get('grid_violations') is not None else 'N/A'):<9} "
            f"{_fmt(d.get('mean_final_soc'), '.1%')}"
        )

    bld = averages.get('building', {})
    if bld:
        print(
            f"\n  Building solar produced (avg): {_fmt(bld.get('total_solar_produced'), '.1f')} kWh | "
            f"used by building: {_fmt(bld.get('solar_used_by_building'), '.1f')} kWh"
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Compute averages from 2018 monthly simulation files.'
    )
    parser.add_argument(
        '--month', type=int, choices=range(1, 13), metavar='1-12',
        help='Aggregate only this month. Omit for full year.'
    )
    args = parser.parse_args()

    months_to_process = [args.month] if args.month else list(range(1, 13))

    print('=' * 70)
    print(f'  2018 Annual Simulation Averages')
    print('=' * 70)
    print(f'  Results directory : {RESULTS_DIR}')
    print(f'  Months requested  : {months_to_process}')

    # -----------------------------------------------------------------------
    # Load all month files
    # -----------------------------------------------------------------------
    all_days: List[Dict] = []
    monthly_averages: Dict[int, Dict] = {}

    for month in months_to_process:
        data = load_month_file(month)
        if data is None:
            continue

        days = data.get('days', [])
        all_days.extend(days)

        month_avg = average_day_records(days)
        monthly_averages[month] = month_avg

    # -----------------------------------------------------------------------
    # Print monthly summaries
    # -----------------------------------------------------------------------
    print('\n' + '=' * 70)
    print('  MONTHLY AVERAGES')
    print('=' * 70)

    for month, avg in sorted(monthly_averages.items()):
        print_scenario_table(
            f'{calendar.month_name[month]} {2018}',
            avg
        )

    # -----------------------------------------------------------------------
    # Annual averages
    # -----------------------------------------------------------------------
    annual_avg = average_day_records(all_days)
    total_days = annual_avg.get('n_days', 0)

    print('\n' + '=' * 70)
    print('  ANNUAL AVERAGES (across all processed days)')
    print('=' * 70)
    print_scenario_table('Full Year 2018', annual_avg)

    # -----------------------------------------------------------------------
    # Per-day time-series list (ordered)
    # -----------------------------------------------------------------------
    valid_days_sorted = sorted(
        [d for d in all_days if 'error' not in d],
        key=lambda d: d.get('date', '')
    )

    # -----------------------------------------------------------------------
    # Relative savings summary (RL vs Simple baseline)
    # -----------------------------------------------------------------------
    print('\n' + '=' * 70)
    print('  COST SAVINGS RELATIVE TO Simple BASELINE')
    print('=' * 70)

    baseline_cost = (annual_avg.get('co_simple') or {}).get('total_cost')
    if baseline_cost and baseline_cost > 0:
        comparisons = [
            ('RL (charge-only)', 'co_rl'),
            ('Simple+V2G',       'v2g_simple'),
            ('RL+V2G',           'v2g_rl'),
        ]
        for label, sc in comparisons:
            cost = (annual_avg.get(sc) or {}).get('total_cost')
            if cost is None:
                continue
            saving = baseline_cost - cost
            pct = saving / baseline_cost * 100
            print(f"  {label:<20}: avg daily saving = €{saving:+.2f}  ({pct:+.1f}%)")
            print(f"  {'':20}  extrapolated 250 days = €{saving * 250:+.0f}")
    else:
        print('  (baseline cost not available)')

    # -----------------------------------------------------------------------
    # Save to JSON
    # -----------------------------------------------------------------------
    output = {
        'year': 2018,
        'months_processed': sorted(monthly_averages.keys()),
        'total_days_processed': total_days,
        'annual_averages': annual_avg,
        'monthly_averages': {str(m): v for m, v in sorted(monthly_averages.items())},
        'per_day_timeseries': [
            {
                'date': d['date'],
                **{sc: {k: d[sc].get(k) for k in NUMERIC_METRICS if d[sc].get(k) is not None}
                   for sc in SCENARIOS if sc in d},
                'building': d.get('building', {}),
            }
            for d in valid_days_sorted
        ],
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f'\n✓ Averages saved → {OUTPUT_FILE}')
    print(f'  Total valid days: {total_days}')


if __name__ == '__main__':
    main()
