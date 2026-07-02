"""Plot Q-learning convergence for one representative day (charge-only case study)."""

import os
import random
import sys

import matplotlib.pyplot as plt
import numpy as np
import yaml

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.models.building import Building
from src.models.grid import Grid
from src.models.multi_ev_charging_system import MultiEVChargingSystem
from src.simulation.multi_ev_simulator import random_ev_config
from src.utils.data_generator import load_consumption_profile, load_irradiance_pvgis

plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 11,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
})


def build_system(cfg, seed=42):
    random.seed(seed)
    np.random.seed(seed)

    duration = cfg['duration']
    project_root = PROJECT_ROOT

    consumption_file = cfg['consumption_file']
    if not os.path.isabs(consumption_file):
        consumption_file = os.path.join(project_root, consumption_file)

    irradiance_profile = None
    if cfg.get('irradiance_file') and cfg.get('irradiance_date'):
        irradiance_file = cfg['irradiance_file']
        if not os.path.isabs(irradiance_file):
            irradiance_file = os.path.join(project_root, irradiance_file)
        irradiance_profile = load_irradiance_pvgis(
            irradiance_file, cfg['irradiance_date'])

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

    price_profile = {h: p for h, p in enumerate(cfg['price_profile'])}
    grid_capacity = {h: c for h, c in enumerate(cfg['grid_capacity_per_hour'])}
    grid = Grid(price_profile=price_profile)

    evs = [random_ev_config(i, cfg, duration) for i in range(cfg['n_evs'])]

    return MultiEVChargingSystem(
        building=building,
        evs=evs,
        grid=grid,
        grid_capacity_per_hour=grid_capacity,
        min_soc=cfg.get('min_soc', 0.2),
    )


def main():
    config_path = os.path.join(PROJECT_ROOT, 'data', 'multi_ev_config.yml')
    with open(config_path, encoding='utf-8') as f:
        cfg = yaml.safe_load(f)

    system = build_system(cfg, seed=42)

    # Mid-morning hour: most EVs plugged in, prices still variable
    training_hour = 10
    episodes = cfg.get('rl_episodes', 15000)
    history = []

    print(f'Training Q-learning: {episodes} episodes at hour {training_hour}...')
    system.rl_charge_multi(
        training_hour,
        episodes=episodes,
        learning_rate=cfg.get('rl_lr', 0.15),
        discount_factor=cfg.get('rl_gamma', 1.0),
        epsilon=cfg.get('rl_epsilon', 0.10),
        convergence_history=history,
    )
    print(f'Collected {len(history)} episode rewards.')

    episodes_x = np.arange(1, len(history) + 1)
    rewards = np.array(history)

    window = 500
    if len(rewards) >= window:
        kernel = np.ones(window) / window
        smoothed = np.convolve(rewards, kernel, mode='valid')
        smooth_x = episodes_x[window - 1:]
    else:
        smoothed = rewards
        smooth_x = episodes_x

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(episodes_x, rewards, color='#bdbdbd', linewidth=0.6,
            alpha=0.7, label='Per-episode reward')
    ax.plot(smooth_x, smoothed, color='#2166ac', linewidth=2.2,
            label=f'{window}-episode moving average')

    final_avg = np.mean(rewards[-window:])
    init_avg = np.mean(rewards[:window])
    ax.axhline(final_avg, color='#31a354', linestyle='--', linewidth=1.2,
               label=f'Final {window}-ep. avg ({final_avg:.0f})')

    ax.set_xlabel('Training episode')
    ax.set_ylabel('Cumulative episode reward')
    ax.set_title(
        'Q-Learning Convergence — Charge-Only, 15 EVs\n'
        'March 12, 2018 (PVGIS); training at hour 10:00'
    )
    ax.set_xlim(0, len(history))
    ax.legend(loc='lower right', framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle='--')

    note = (
        f'Hyperparameters: {episodes:,} episodes, '
        f'α={cfg.get("rl_lr", 0.15)}, γ={cfg.get("rl_gamma", 1.0)}, '
        f'ε={cfg.get("rl_epsilon", 0.10)}'
    )
    ax.text(0.02, 0.02, note, transform=ax.transAxes, fontsize=9,
            verticalalignment='bottom', color='#444444')

    out_dir = os.path.join(PROJECT_ROOT, 'thesis', 'figures')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'rl_convergence.png')
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    print(f'Saved {out_path}')
    print(f'Reward improvement (first vs last {window} eps): '
          f'{init_avg:.0f} → {final_avg:.0f}')


if __name__ == '__main__':
    main()
